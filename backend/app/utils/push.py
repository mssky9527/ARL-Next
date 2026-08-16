import time
import base64
import hmac
import urllib.parse
import hashlib
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.utils import http_req, get_logger
from app.config import Config

logger = get_logger()


class Push(object):
    """docstring for ClassName"""

    def __init__(self, asset_map, asset_counter, update_map=None, update_counter=None):
        super(Push, self).__init__()
        self.asset_map = asset_map
        self.asset_counter = asset_counter
        self.update_map = update_map or {}
        self.update_counter = update_counter or {}
        self.task_name = self.asset_map.get("task_name", "")
        self.has_any_data = any(v > 0 for v in self.asset_counter.values()) or any(v > 0 for v in self.update_counter.values())

    def _build_generic_info_list(self, data_list, category):
        if not data_list: return []
        mapping = {
            "site": {"站点": "site", "标题": "title", "状态码": "status"},
            "domain": {"域名": "domain", "解析类型": "type", "记录": lambda x: x["record"][0] if x.get("record") else ""},
            "ip": {"IP": "ip", "端口数目": lambda x: len(x.get("port_info", [])), "组织": lambda x: x.get("geo_asn", {}).get("organization", "")},
            "vuln": {"目标": "target", "漏洞名称": "vul_name"},
            "nuclei_result": {"目标": "target", "模板": "template_id"},
            "service": {"服务": "service_name", "端口": "port_id"},
            "fileleak": {"URL": "url", "状态": "status_code"},
            "wih": {"站点": "site", "类型": lambda x: x.get("record_type") or x.get("recordType") or x.get("type", "")},
            "url": {"URL": "url", "状态": "status"},
            "cert": {"IP": "ip", "证书颁发": lambda x: x.get("cert", {}).get("subject", {}).get("common_name", "")},
            "npoc_service": {"主机": "host", "端口": "port", "服务": "service"},
            "cip": {"C段": "cidr_ip"},
            "stat_finger": {"指纹": "name"}
        }
        info_list = []
        for item in data_list:
            d = {}
            cmap = mapping.get(category, {"标识": "_id"})
            for k, v in cmap.items():
                try:
                    d[k] = v(item) if callable(v) else item.get(v, "")
                except:
                    d[k] = ""
            info_list.append(d)
        return info_list

    def _build_markdown_block(self, map_data, counter_data, formatter):
        block = ""
        for cat, cnt in counter_data.items():
            if cnt > 0 and cat in map_data:
                items = self._build_generic_info_list(map_data[cat], cat)
                if not items: continue
                block += f"\n**{cat}** (共 {cnt} 条)\n"
                block += formatter(items) + "\n"
        return block

    def _generate_markdown_payload(self):
        if not self.has_any_data:
            return f"[{self.task_name}] 任务已完成，本次无新增或变动资产。\n"
        
        tpl = f"[{self.task_name}] 任务推送\n"
        new_block = self._build_markdown_block(self.asset_map, self.asset_counter, dict2dingding_mark)
        if new_block:
            tpl += "\n### 🌟 新增资产\n" + new_block
            
        update_block = self._build_markdown_block(self.update_map, self.update_counter, dict2dingding_mark)
        if update_block:
            tpl += "\n### 🔄 更新资产\n" + update_block
            
        if len(tpl) > 3500:
            tpl = tpl[:3500] + "\n\n...(数据过多已截断，详情请登录 ARL 系统查看)"
        return tpl

    def _generate_html_payload(self):
        if not self.has_any_data:
            return f"<div>[{self.task_name}] 任务已完成，本次无新增或变动资产。</div>"
        
        html = f"<h2>[{self.task_name}] 任务推送</h2>"
        new_block = self._build_markdown_block(self.asset_map, self.asset_counter, dict2table)
        if new_block:
            html += "<h3>🌟 新增资产</h3>" + new_block.replace("\n", "<br/>")
            
        update_block = self._build_markdown_block(self.update_map, self.update_counter, dict2table)
        if update_block:
            html += "<h3>🔄 更新资产</h3>" + update_block.replace("\n", "<br/>")
            
        return html

    def _push_dingding(self):
        tpl = self._generate_markdown_payload()
        ding_out = dingding_send(msg=tpl, access_token=Config.DINGDING_ACCESS_TOKEN,
                                 secret=Config.DINGDING_SECRET, msgtype="markdown")
        if ding_out.get("errcode", 0) != 0:
            logger.warning("发送失败 \\n{}\\n {}".format(tpl[:50], ding_out))
            return False
        return True

    def _push_wx_work(self):
        tpl = self._generate_markdown_payload()
        ding_out = wx_work_send(msg=tpl, webhook_url=Config.WX_WORK_WEBHOOK)
        if ding_out.get("errcode", 0) != 0:
            logger.warning("发送失败 \\n{}\\n {}".format(tpl[:50], ding_out))
            return False
        return True

    def _push_feishu(self):
        tpl = self._generate_markdown_payload()
        feishu_out = feishu_send(msg=tpl, webhook_url=Config.FEISHU_WEBHOOK,
                                 secret=Config.FEISHU_SECRET)
        if feishu_out.get("code", 0) != 0:
            logger.warning("发送失败 \\n{}\\n {}".format(tpl[:50], feishu_out))
            return False
        return True

    def _push_telegram(self):
        tpl = self._generate_markdown_payload()
        try:
            tg_out = telegram_send(f"*{self.task_name}*\\n\\n{tpl}", bot_token=Config.TG_BOT_TOKEN, chat_id=Config.TG_CHAT_ID)
            if not tg_out.get("ok"):
                logger.warning("Telegram发送失败 \\n{}\\n {}".format(tpl[:50], tg_out))
                return False
            return True
        except Exception as e:
            logger.warning("Telegram发送异常 \\n{}\\n {}".format(tpl[:50], str(e)))
            return False

    def _push_email(self):
        html = self._generate_html_payload()
        title = "[{}] 灯塔消息推送".format(self.task_name[:50])
        send_email(host=Config.EMAIL_HOST, port=Config.EMAIL_PORT, mail=Config.EMAIL_USERNAME,
                   password=Config.EMAIL_PASSWORD, to=Config.EMAIL_TO, title=title, html=html)
        return True

    def push_dingding(self):
        try:
            if Config.DINGDING_ACCESS_TOKEN and Config.DINGDING_SECRET:
                if self._push_dingding():
                    logger.info("push dingding succ")
                    return True

        except Exception as e:
            logger.warning(f"[{self.task_name}] push dingding error: {e}")

    def push_email(self):
        try:
            if Config.EMAIL_HOST and Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD:
                self._push_email()
                logger.info("send email succ")
                return True
        except Exception as e:
            logger.warning(f"[{self.task_name}] push email error: {e}")

    def push_feishu(self):
        try:
            if Config.FEISHU_WEBHOOK and Config.FEISHU_SECRET:
                self._push_feishu()
                logger.info("send feishu succ")
                return True
        except Exception as e:
            logger.warning(f"[{self.task_name}] push feishu error: {e}")

    def push_wx_work(self):
        try:
            if Config.WX_WORK_WEBHOOK:
                self._push_wx_work()
                logger.info("send wx work succ")
                return True
        except Exception as e:
            logger.warning(f"[{self.task_name}] push wx work error: {e}")

    def push_telegram(self):
        try:
            if getattr(Config, 'TG_BOT_TOKEN', None) and getattr(Config, 'TG_CHAT_ID', None):
                self._push_telegram()
                logger.info("send telegram succ")
                return True
        except Exception as e:
            logger.warning(f"[{self.task_name}] push telegram error: {e}")


def message_push(asset_map, asset_counter, update_map=None, update_counter=None):
    if "task_complete" not in Config.PUSH_OPTIONS:
        return
    logger.info("ARL push run")
    p = Push(asset_map=asset_map, asset_counter=asset_counter, update_map=update_map, update_counter=update_counter)
    p.push_dingding()
    p.push_email()
    p.push_feishu()
    p.push_wx_work()
    p.push_telegram()

def unified_push(push_type: str, title: str, content: str):
    """
    统一消息推送入口，适配所有配置的有效渠道
    """
    if push_type not in Config.PUSH_OPTIONS:
        return
        
    # 钉钉
    if Config.DINGDING_ACCESS_TOKEN and Config.DINGDING_SECRET:
        try:
            res = dingding_send(content, Config.DINGDING_ACCESS_TOKEN, Config.DINGDING_SECRET, msgtype="markdown", title=title)
            if res.get("errcode", 0) != 0:
                logger.warning(f"unified_push dingding api error: {res}")
        except Exception as e:
            logger.warning(f"unified_push dingding error: {e}")
            
    # 飞书
    if Config.FEISHU_WEBHOOK and Config.FEISHU_SECRET:
        try:
            res = feishu_send(content, Config.FEISHU_WEBHOOK, Config.FEISHU_SECRET, title=title)
            if res.get("code", 0) != 0:
                logger.warning(f"unified_push feishu api error: {res}")
        except Exception as e:
            logger.warning(f"unified_push feishu error: {e}")
            
    # 企业微信
    if Config.WX_WORK_WEBHOOK:
        try:
            wx_content = f"**{title}**\n\n{content}"
            res = wx_work_send(wx_content, Config.WX_WORK_WEBHOOK)
            if res.get("errcode", 0) != 0:
                logger.warning(f"unified_push wx_work api error: {res}")
        except Exception as e:
            logger.warning(f"unified_push wx_work error: {e}")
            
    # 邮件
    if Config.EMAIL_HOST and Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD and Config.EMAIL_TO:
        try:
            html = content.replace('\n', '<br>')
            html = f"<div><h3>{title}</h3><div>{html}</div></div>"
            send_email(Config.EMAIL_HOST, Config.EMAIL_PORT, Config.EMAIL_USERNAME, Config.EMAIL_PASSWORD, Config.EMAIL_TO, title, html)
        except Exception as e:
            logger.warning(f"unified_push email error: {e}")

    # Telegram
    tg_token = getattr(Config, 'TG_BOT_TOKEN', None)
    tg_chat = getattr(Config, 'TG_CHAT_ID', None)
    if tg_token and tg_chat:
        try:
            res = telegram_send(f"*{title}*\n\n{content}", tg_token, tg_chat)
            if not res.get("ok"):
                logger.warning(f"unified_push telegram api error: {res}")
        except Exception as e:
            logger.warning(f"unified_push telegram error: {e}")


def dict2dingding_mark(info_list):
    if not info_list:
        return ""

    title_tpl = '  \t\t  '.join(map(str, info_list[0].keys()))
    items_tpl = ""
    cnt = 0
    for row in info_list:
        cnt += 1
        row = ' \t '.join(map(str, row.values()))
        items_tpl += "{}. {}\n".format(cnt, row)

    return "{}\n{}".format(title_tpl, items_tpl)


def dingding_send(msg, access_token, secret, msgtype="text", title="灯塔消息推送"):
    ding_url = "https://oapi.dingtalk.com/robot/send?access_token={}".format(access_token)
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    param = "&timestamp={}&sign={}".format(timestamp, sign)
    ding_url = ding_url + param
    send_json = {
        "msgtype": msgtype,
        "text": {
            "content": msg
        },
        "markdown": {
            "title": title,
            "text": msg
        }
    }
    conn = http_req(ding_url, method='post', json=send_json)
    return conn.json()


def send_email(host, port, mail, password, to, title, html, smtp_timeout=10):
    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, context=context, timeout=smtp_timeout)
    else:
        server = smtplib.SMTP(host, port, timeout=smtp_timeout)

    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = mail
    msg['To'] = to
    part1 = MIMEText(html, "html", "utf-8")
    msg.attach(part1)
    server.login(mail, password)
    server.send_message(msg)
    server.close()


def dict2table(info_list):
    if not info_list:
        return ""
    html = ""
    table_style = 'style="border-collapse: collapse;"'
    table_start = '<table {}>\n'.format(table_style)
    table_end = '</table>\n'
    style = 'style="border: 0.5pt solid windowtext;"'
    thead_start = '<thead><tr><th {}>序号</th><th {}>\n'.format(style, style)
    thead_end = '\n</th></tr></thead>'
    th_join_tpl = '</th>\n<th {}>'.format(style)
    thead_tpl = th_join_tpl.join(map(str, info_list[0].keys()))
    html += table_start
    html += thead_start
    html += thead_tpl
    html += thead_end

    tbody = "<tbody>\n"
    cnt = 0
    for row in info_list:
        cnt += 1
        td_join_tpl = '</td>\n<td {}>'.format(style)
        row_start = '<tr><td {}>{}</td>\n<td {}>'.format(style, cnt, style)
        items = [str(x).replace('>', "&#x3e;").replace('<', "&#x3c;") for x in row.values()]
        row = td_join_tpl.join(items)
        row_end = '</td>\n</tr>'
        row_tpl = row_start + row + row_end
        tbody = tbody + row_tpl + "\n"

    html = html + tbody + "</tbody>" + table_end

    return html


def feishu_send(msg, webhook_url, secret, title="灯塔消息推送"):
    timestamp = str(int(time.time()))
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    # 对结果进行base64处理
    sign = base64.b64encode(hmac_code).decode('utf-8')

    send_data = {
        "timestamp": timestamp,
        "sign": sign,
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": [
                        [{
                            "tag": "text",
                            "text": msg
                        }]
                    ]
                }
            }
        }
    }
    conn = http_req(webhook_url, method='post', json=send_data)
    return conn.json()


def wx_work_send(msg, webhook_url):
    send_data = {
        "msgtype": "markdown",
        "markdown":{
            "content": msg
        }
    }
    conn = http_req(webhook_url, method='post', json=send_data)
    return conn.json()

def telegram_send(msg, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        conn = http_req(url, method='post', json=payload, timeout=10)
        return conn.json()
    except Exception as e:
        logger.warning(f"telegram_send error: {e}")
        return {}

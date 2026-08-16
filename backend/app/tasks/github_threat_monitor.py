import datetime
import re
from lxml import etree
from app import utils
from app.config import Config

logger = utils.get_logger()

def get_github_headers():
    return {
        'Authorization': f"token {Config.GITHUB_TOKEN}" if Config.GITHUB_TOKEN else "",
        'Accept': 'application/vnd.github.v3+json'
    }

from app.utils.push import unified_push

class ThreatIntelligencePush:
    @staticmethod
    def push_msg(title, body):
        # Determine push_type from title
        if 'CVE' in title:
            push_type = 'github_cve'
        elif '工具' in title or '监控' in title:
            push_type = 'github_tools'
        elif '大佬' in title or '动态' in title:
            push_type = 'github_hackers'
        else:
            push_type = 'github_leak' # Fallback
            
        unified_push(push_type, title, body)

class GithubCveMonitorTask:
    def __init__(self):
        self.collection = "github_cve_history"
        
    def fetch_mitre_cve_desc(self, cve_id):
        try:
            url = f"https://cve.mitre.org/cgi-bin/cvename.cgi?name={cve_id}"
            res = utils.http_req(url, timeout=(10, 10))
            if res and res.text:
                html = etree.HTML(res.text)
                if html is not None:
                    elements = html.xpath('//*[@id="GeneratedTable"]/table//tr[4]/td/text()')
                    if elements:
                        des = elements[0].strip()
                        if des:
                            return des
        except Exception as e:
            logger.warning(f"Fetch MITRE desc failed for {cve_id}: {e}")
        return "No description available on MITRE yet."

    def run(self):
        logger.info("Starting Github CVE Monitor Task...")
        year = datetime.datetime.now().year
        utc_now = datetime.datetime.utcnow()
        api = f"https://api.github.com/search/repositories?q=CVE-{year}&sort=updated&per_page=100"
        
        try:
            res = utils.http_req(api, headers=get_github_headers(), timeout=(10, 10))
            if not res or res.status_code != 200:
                logger.error("Failed to fetch Github repos for CVE.")
                return

            items = res.json().get('items', [])[:100]
            db = utils.conn_db(self.collection)

            for item in items:
                cve_name_raw = item['name'].upper()
                cve_match = re.findall(r'(CVE-\d+-\d+)', cve_name_raw)
                if not cve_match:
                    continue
                    
                cve_id = cve_match[0]
                pushed_at_str = item.get('pushed_at', '')
                try:
                    pushed_at_dt = datetime.datetime.strptime(pushed_at_str, "%Y-%m-%dT%H:%M:%SZ")
                    # 转换为北京时间 (UTC+8) 存入数据库
                    pushed_at_local_dt = pushed_at_dt + datetime.timedelta(hours=8)
                    pushed_at_date = pushed_at_local_dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
                repo_url = item['html_url']

                # 仅处理最近24小时内更新的仓库（彻底解决跨时区问题）
                if (utc_now - pushed_at_dt).total_seconds() > 24 * 3600:
                    continue

                # Use upsert to prevent race conditions
                result = db.update_one(
                    {"cve_name": cve_id},
                    {"$setOnInsert": {
                        "cve_name": cve_id,
                        "cve_url": repo_url,
                        "pushed_at": pushed_at_date,
                        "insert_time": utils.curr_date()
                    }},
                    upsert=True
                )
                
                if result.upserted_id is not None:
                    logger.info(f"New CVE found: {cve_id}")
                    cve_desc = self.fetch_mitre_cve_desc(cve_id)
                    db.update_one({"_id": result.upserted_id}, {"$set": {"desc": cve_desc}})
                    
                    title = f"🚨 发现新公开的 {cve_id} Github 利用代码！"
                    body = (
                        f"**CVE 编号**: {cve_id}\n"
                        f"**项目地址**: {repo_url}\n"
                        f"**官方描述**: \n{cve_desc}\n"
                    )
                    ThreatIntelligencePush.push_msg(title, body)
                
        except Exception as e:
            logger.exception(f"GithubCveMonitorTask Error: {e}")


class GithubToolsMonitorTask:
    def __init__(self):
        self.collection = "github_tools_target"

    def run(self):
        logger.info("Starting Github Tools Monitor Task...")
        db = utils.conn_db(self.collection)
        targets = list(db.find({})) 
        
        for target in targets:
            repo_url = target.get('repo_url')
            if not repo_url: continue
                
            try:
                api_releases = f"{repo_url}/releases"
                res = utils.http_req(api_releases, headers=get_github_headers(), timeout=(10, 10))
                
                if res and res.status_code == 200 and len(res.json()) > 0:
                    latest = res.json()[0]
                    new_tag = latest.get('tag_name', '')
                    try:
                        published_at_str = latest.get('published_at', '')
                        published_at_dt = datetime.datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
                        published_at_local_dt = published_at_dt + datetime.timedelta(hours=8)
                        new_pushed_at = published_at_local_dt.strftime("%Y-%m-%d")
                    except Exception:
                        new_pushed_at = ""
                    
                    old_tag = target.get('last_tag', '')
                    if new_tag != old_tag:
                        # Atomically update to ensure only one thread pushes the notification
                        result = db.update_one(
                            {"_id": target["_id"], "last_tag": old_tag},
                            {"$set": {"last_tag": new_tag, "last_commit_time": new_pushed_at}}
                        )
                        
                        if result.modified_count > 0 and old_tag != '':
                            update_log = latest.get('body', 'No update log provided.')
                            download_url = latest.get('html_url')
                            tool_name = repo_url.split('/')[-1]
                            
                            title = f"🛠️ 工具 [{tool_name}] 发布了新版本: {new_tag}"
                            body = f"**地址**: {download_url}\n**更新日志**:\n{update_log}"
                            
                            ThreatIntelligencePush.push_msg(title, body)
            except Exception as e:
                logger.error(f"Failed to check tool {repo_url}: {e}")

class GithubHackersMonitorTask:
    def __init__(self):
        self.collection = "github_hackers_target"
        self.history_collection = "github_hackers_history" # 记录推送过的仓库，避免重复
        
    def run(self):
        logger.info("Starting Github Hackers Monitor Task...")
        db = utils.conn_db(self.collection)
        history_db = utils.conn_db(self.history_collection)
        
        targets = list(db.find({}))
        utc_now = datetime.datetime.utcnow()
        
        for target in targets:
            github_id = target.get('github_id')
            if not github_id: continue
                
            try:
                api = f"https://api.github.com/users/{github_id}/repos?sort=created&direction=desc"
                res = utils.http_req(api, headers=get_github_headers(), timeout=(10, 10))
                
                if not res or res.status_code != 200:
                    continue
                    
                repos = res.json()
                for repo in repos:
                    # 避免遍历太多，只看最近几条
                    if isinstance(repo, dict):
                        fork = repo.get('fork', False)
                        created_at_raw = repo.get('created_at', '')
                        if not created_at_raw: continue
                        
                        try:
                            created_at_dt = datetime.datetime.strptime(created_at_raw, "%Y-%m-%dT%H:%M:%SZ")
                        except ValueError:
                            continue
                            
                        # 仅处理最近24小时内创建的仓库（解决时区导致的部分时段遗漏）
                        is_recent = (utc_now - created_at_dt).total_seconds() <= 24 * 3600
                        
                        if is_recent and not fork:
                            full_name = repo.get('full_name')
                            # 检查是否已推送并原子插入
                            result = history_db.update_one(
                                {"full_name": full_name},
                                {"$setOnInsert": {
                                    "full_name": full_name,
                                    "insert_time": utils.curr_date()
                                }},
                                upsert=True
                            )
                            
                            if result.upserted_id is not None:
                                name = repo.get('name')
                                description = repo.get('description') or "作者未写描述"
                                download_url = repo.get('html_url')
                                
                                title = f"👨‍💻 大佬 [{github_id}] 分享了一款新工具!"
                                body = (
                                    f"**工具名称**: {name}\n"
                                    f"**项目地址**: {download_url}\n"
                                    f"**工具描述**: {description}\n"
                                )
                                ThreatIntelligencePush.push_msg(title, body)
            except Exception as e:
                logger.error(f"Failed to check hacker {github_id}: {e}")

import time

def threat_intelligence_scheduler():
    now = time.time()
    db = utils.conn_db("system_config")
    
    # CVE 抓取频率通过 DB 动态配置
    conf = db.find_one({"_id": "cve_radar_config"}) or {"enabled": False, "interval": 6}
    if conf.get("enabled", False):
        cve_interval_hours = conf.get("interval", 6)
        last_run = conf.get("last_run_time", 0)
        if now - last_run > 3600 * cve_interval_hours:
            try:
                GithubCveMonitorTask().run()
                db.update_one({"_id": "cve_radar_config"}, {"$set": {"last_run_time": now}}, upsert=True)
            except Exception as e:
                logger.error(f"CVE schedule error: {e}")
        
    # Tools 抓取频率通过 DB 动态配置
    tools_conf = db.find_one({"_id": "tools_radar_config"}) or {"enabled": False, "interval": 6}
    if tools_conf.get("enabled", False):
        tools_interval_hours = tools_conf.get("interval", 6)
        last_run = tools_conf.get("last_run_time", 0)
        if now - last_run > 3600 * tools_interval_hours:
            try:
                GithubToolsMonitorTask().run()
                db.update_one({"_id": "tools_radar_config"}, {"$set": {"last_run_time": now}}, upsert=True)
            except Exception as e:
                logger.error(f"Tools schedule error: {e}")

    # Hackers 抓取频率通过 DB 动态配置
    hackers_conf = db.find_one({"_id": "hackers_radar_config"}) or {"enabled": False, "interval": 6}
    if hackers_conf.get("enabled", False):
        hackers_interval_hours = hackers_conf.get("interval", 6)
        last_run = hackers_conf.get("last_run_time", 0)
        if now - last_run > 3600 * hackers_interval_hours:
            try:
                GithubHackersMonitorTask().run()
                db.update_one({"_id": "hackers_radar_config"}, {"$set": {"last_run_time": now}}, upsert=True)
            except Exception as e:
                logger.error(f"Hackers schedule error: {e}")


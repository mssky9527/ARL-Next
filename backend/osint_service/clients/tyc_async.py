import aiohttp
import asyncio
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class AsyncTycException(Exception):
    pass

class AsyncTycClient:
    def __init__(self, gid, token):
        self.gid = gid
        self.token = token
        self.base_url = "https://capi.tianyancha.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:152.0) Gecko/20100101 Firefox/152.0",
            "Version": "TYC-Web",
            "X-Tycid": self.gid,
            "X-Auth-Token": self.token,
            "Content-Type": "application/json"
        }
        self.page_size = 100

    async def _request(self, method, path, json_data=None, params=None, max_retries=3):
        import random
        await asyncio.sleep(random.uniform(5, 10))
        if not self.gid or not self.token:
            raise AsyncTycException("未配置天眼查 ID 或 Token。")

        url = urljoin(self.base_url, path)
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    if method.upper() == 'POST':
                        async with session.post(url, headers=self.headers, json=json_data, timeout=15) as res:
                            status = res.status
                            text = await res.text()
                            data = await res.json() if "application/json" in res.headers.get("Content-Type", "") else None
                    else:
                        async with session.get(url, headers=self.headers, params=params, timeout=15) as res:
                            status = res.status
                            text = await res.text()
                            data = await res.json() if "application/json" in res.headers.get("Content-Type", "") else None
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    raise AsyncTycException("天眼查 API 请求超时")
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    raise AsyncTycException(f"网络异常: {e}")

                if status == 401:
                    raise AsyncTycException("TYC Token 已失效。")
                elif status in [403, 429]:
                    if attempt < max_retries - 1:
                        logger.warning(f"触发限流(HTTP {status})，挂起 {15 * (attempt + 1)} 秒后重试 (Attempt {attempt+1}/{max_retries})...")
                        await asyncio.sleep(15 * (attempt + 1))
                        continue
                    raise AsyncTycException("触发天眼查风控拦截或限流。")
                elif status != 200:
                    raise AsyncTycException(f"天眼查 API 请求失败, HTTP {status}, {text[:100]}")

                if not data:
                    return None

                state = str(data.get("state", "")).lower()
                message = str(data.get("message", ""))
                
                # 1. 过滤正常的无数据场景
                if "无数据" in message or "未找到" in message or "为空" in message:
                    return None
                    
                # 2. 精准识别风控拦截与业务异常
                if state != "ok":
                    if any(kw in message for kw in ["频繁", "验证码", "登录", "异常", "机器人", "操作过快", "校验"]):
                        if attempt < max_retries - 1:
                            logger.warning(f"触发风控 ({message})，挂起 {15 * (attempt + 1)} 秒后重试 (Attempt {attempt+1}/{max_retries})...")
                            await asyncio.sleep(15 * (attempt + 1))
                            continue
                        raise AsyncTycException(f"触发天眼查风控拦截: {message}")
                    else:
                        raise AsyncTycException(f"天眼查业务异常: state={state}, message={message}")

                if 'data' not in data:
                    return None

                return data.get('data')

    async def fetch_all_pages(self, method, path, total_key, list_key, gid_field="gid", gid_val=None, extra_payload=None, delay=1.5):
        results = []
        page_num = 1
        while True:
            params = None
            json_data = None
            payload = {"pageSize": self.page_size, "pageNum": page_num}
            if "trademarkList" in path:
                payload = {"ps": self.page_size, "pn": page_num}
            payload[gid_field] = gid_val
            if extra_payload:
                payload.update(extra_payload)
            if method.upper() == 'POST':
                json_data = payload
            else:
                params = payload
            try:
                data = await self._request(method, path, json_data=json_data, params=params)
            except Exception as e:
                logger.error(f"分页获取失败 (页码: {page_num}): {e}")
                break
            if not data:
                break
            items = data.get(list_key, [])
            if not items:
                break
            results.extend(items)
            total = data.get(total_key, 0)
            if len(results) >= total:
                break
            page_num += 1
            await asyncio.sleep(delay)
        return results

    async def get_invest_list(self, gid):
        extra = {"benefitSharesType": 1, "percentLevel": "-100", "registation": "-100", "province": "-100", "category": "-100", "fullSearchText": ""}
        return await self.fetch_all_pages("POST", "/cloud-company-background/company/investListV2", "total", "result", "gid", gid, extra)

    async def get_trademark_list(self, gid):
        extra = {"category": "-100", "fullSearchText": "", "sortField": "", "sortType": ""}
        return await self.fetch_all_pages("POST", "/cloud-intellectual-property/intellectualProperty/trademarkList", "viewtotal", "items", "id", gid, extra)

    async def get_icp_record_list(self, gid):
        return await self.fetch_all_pages("GET", "/cloud-intellectual-property/intellectualProperty/icpRecordList", "itemTotal", "item", "id", gid)

    async def get_mini_program_list(self, gid):
        return await self.fetch_all_pages("GET", "/cloud-intellectual-property/intellectualProperty/miniProgramIcpRecordList", "itemTotal", "miniProgramIcpRecordList", "gid", gid)

    async def get_app_list(self, gid):
        return await self.fetch_all_pages("GET", "/cloud-business-state/v3/ar/appbkinfo", "count", "items", "id", gid)

    async def get_app_icp_record_list(self, gid):
        return await self.fetch_all_pages("GET", "/cloud-intellectual-property/intellectualProperty/appIcpRecordList", "itemTotal", "appIcpRecordList", "gid", gid)

    async def get_wechat_list(self, gid):
        return await self.fetch_all_pages("GET", "/cloud-business-state/wechat/list", "count", "resultList", "graphId", gid)

    async def get_weibo_list(self, gid):
        return await self.fetch_all_pages("GET", "/cloud-business-state/weibo/list", "total", "result", "graphId", gid)

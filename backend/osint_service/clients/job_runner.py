import logging
import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from .tyc_async import AsyncTycClient
import re

logger = logging.getLogger(__name__)
MONGO_URI = "mongodb://admin:admin@mongodb:27017/?authSource=admin"
client = AsyncIOMotorClient(MONGO_URI)
db = client['arl']

def curr_date():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

async def run_recon_job(options):
    logger.info(f"Entering run_recon_job with options: {options}")
    task_id = options.get("task_id")
    recon_type = options.get("type", "tyc")
    if recon_type == "tyc":
        await run_tyc_job(options)
    elif recon_type == "icp":
        await run_icp_job(options)


async def run_icp_job(options):
    task_id = options.get("task_id")
    target = options.get("target")
    query_types = options.get("query_type", [])
    if not task_id or not target:
        logger.error(f"Missing required ICP params for task {task_id}")
        return
        
    await db['icp_task'].update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "running", "start_time": curr_date()}})
    
    total_assets = 0
    error_msg = []
    
    # We must import ymicp dynamically since we are in clients/
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ymicp import beian
    
    myicp = beian()
    
    handlers = {
        "web": myicp.ymWeb,
        "app": myicp.ymApp,
        "mapp": myicp.ymMiniApp,
        "kapp": myicp.ymKuaiApp,
    }
    
    counts = {"web": 0, "app": 0, "mapp": 0, "kapp": 0}
    
    async def insert_syslog(level, title, message):
        log_doc = {
            "task_id": task_id,
            "level": level,
            "title": title,
            "message": message,
            "create_time": curr_date()
        }
        try:
            await db['syslog'].insert_one(log_doc)
        except Exception:
            pass

    async def update_stats():
        await db['icp_task'].update_one({"_id": ObjectId(task_id)}, {"$set": {"statistic": {
            "asset_cnt": total_assets,
            "web_cnt": counts.get("web", 0),
            "app_cnt": counts.get("app", 0),
            "mapp_cnt": counts.get("mapp", 0),
            "kapp_cnt": counts.get("kapp", 0)
        }}})

    await insert_syslog("info", "ICP查询", f"任务开始运行，目标: {target}，类型: {query_types}")

    for qt in query_types:
        if qt in handlers:
            try:
                await insert_syslog("info", f"{qt}查询", f"开始获取 {qt} 资产数据...")
                res = await handlers[qt](target, "", "", proxy=None)
                if res.get("code") == 200 and res.get("params"):
                    assets = res["params"].get("list", [])
                    for asset in assets:
                        asset['task_id'] = task_id
                        asset['query_type'] = qt
                        await db['icp_asset'].insert_one(asset)
                    total_assets += len(assets)
                    counts[qt] += len(assets)
                    await update_stats()
                    await insert_syslog("info", f"{qt}查询", f"获取完成，共计 {len(assets)} 条资产")
                elif res.get("code") != 200:
                    error_msg.append(f"{qt}: {res.get('msg', 'error')}")
                    await insert_syslog("warning", f"{qt}查询", f"接口返回异常: {res.get('msg', 'error')}")
            except Exception as e:
                logger.error(f"ICP Query exception for {qt}: {e}")
                error_msg.append(f"{qt} error: {str(e)}")
                await insert_syslog("error", f"{qt}查询", f"执行过程发生异常: {str(e)}")
        
    update_data = {
        "$set": {
            "status": "done" if not error_msg else "error", 
            "end_time": curr_date(),
            "statistic": {
                "asset_cnt": total_assets,
                "web_cnt": counts["web"],
                "app_cnt": counts["app"],
                "mapp_cnt": counts["mapp"],
                "kapp_cnt": counts["kapp"]
            }
        }
    }
    if error_msg:
        update_data["$set"]["error_msg"] = "; ".join(error_msg)
    await db['icp_task'].update_one({"_id": ObjectId(task_id)}, update_data)
    await insert_syslog("info", "任务完成", f"ICP查询任务执行结束，共获取 {total_assets} 条资产")
    logger.info(f"ICP query task {task_id} completed.")


async def run_tyc_job(options):
    task_id = options.get("task_id")
    gid = options.get("gid")
    depth = options.get("depth", 1)
    query_types = options.get("query_type", [])
    tyc_id = options.get("tyc_id")
    tyc_token = options.get("tyc_token")
    if not task_id or not tyc_id or not tyc_token:
        logger.error(f"Missing required TYC params for task {task_id}")
        return
    await db['icp_task'].update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "running", "start_time": curr_date()}})
    total_assets = 0
    error_msg = []
    counts = {"web": 0, "app": 0, "mapp": 0, "wechat": 0, "weibo": 0, "invest": 0}
    
    async def insert_syslog(level, title, message):
        log_doc = {
            "task_id": task_id,
            "level": level,
            "title": title,
            "message": message,
            "create_time": curr_date()
        }
        try:
            await db['syslog'].insert_one(log_doc)
        except Exception:
            pass

    async def update_stats():
        await db['icp_task'].update_one({"_id": ObjectId(task_id)}, {"$set": {"statistic": {
            "asset_cnt": total_assets,
            "invest_cnt": counts.get("invest", 0),
            "web_cnt": counts.get("web", 0),
            "app_cnt": counts.get("app", 0),
            "mapp_cnt": counts.get("mapp", 0),
            "wechat_cnt": counts.get("wechat", 0),
            "weibo_cnt": counts.get("weibo", 0),
            "kapp_cnt": 0,
            "trademark_cnt": 0
        }}})

    await insert_syslog("info", "TYC查询", f"任务开始运行，目标: {tyc_id}，深度: {depth}")

    client = AsyncTycClient(gid=tyc_id, token=tyc_token)
    gids_to_query = [gid]
    for level in range(depth):
        await insert_syslog("info", "TYC查询", f"开始执行第 {level + 1} 层穿透查询，共 {len(gids_to_query)} 个目标...")
        next_gids = []
        for current_gid in gids_to_query:
            # 股权穿透 (投资)
            if "invest" in query_types:
                try:
                    await insert_syslog("info", "投资查询", f"正在查询目标 {current_gid} 的对外投资...")
                    invest_list = await client.get_invest_list(current_gid)
                    if invest_list:
                        for item in invest_list:
                            item['task_id'] = task_id
                            item['query_type'] = 'invest'
                            
                            pct = item.get("percent")
                            if pct and isinstance(pct, str):
                                try:
                                    item['percent_num'] = float(pct.replace("%", "").strip())
                                except ValueError:
                                    pass
                            
                            rc = item.get("regCapital")
                            if rc and isinstance(rc, str):
                                m = re.search(r"(\d+(\.\d+)?)", rc.replace(",", ""))
                                if m:
                                    try:
                                        item['regCapital_num'] = float(m.group(1))
                                    except ValueError:
                                        pass
                                        
                            await db['icp_asset'].insert_one(item)
                            next_gids.append(item.get("id"))
                        counts["invest"] += len(invest_list)
                        total_assets += len(invest_list)
                        await update_stats()
                        await insert_syslog("info", "投资查询", f"目标 {current_gid} 投资查询完成，新增 {len(invest_list)} 条记录")
                except Exception as e:
                    logger.error(f"TYC Query exception for invest: {e}")
                    error_msg.append(f"invest error: {str(e)}")
                    await insert_syslog("error", "投资查询", f"目标 {current_gid} 投资查询异常: {str(e)}")
            
            # 网站备案
            if "web" in query_types:
                try:
                    await insert_syslog("info", "网站查询", f"正在查询目标 {current_gid} 的网站备案...")
                    web_list = await client.get_icp_record_list(current_gid)
                    if web_list:
                        for item in web_list:
                            item['task_id'] = task_id
                            item['query_type'] = 'web'
                            await db['icp_asset'].insert_one(item)
                        counts["web"] += len(web_list)
                        total_assets += len(web_list)
                        await update_stats()
                        await insert_syslog("info", "网站查询", f"目标 {current_gid} 网站备案查询完成，新增 {len(web_list)} 条记录")
                except Exception as e:
                    logger.error(f"TYC Query exception for web: {e}")
                    error_msg.append(f"web error: {str(e)}")
                    await insert_syslog("error", "网站查询", f"目标 {current_gid} 网站查询异常: {str(e)}")
                    
            # App查询
            if "app" in query_types:
                try:
                    await insert_syslog("info", "APP查询", f"正在查询目标 {current_gid} 的APP...")
                    app_list = await client.get_app_list(current_gid)
                    if app_list:
                        for item in app_list:
                            item['task_id'] = task_id
                            item['query_type'] = 'app'
                            await db['icp_asset'].insert_one(item)
                        counts["app"] += len(app_list)
                        total_assets += len(app_list)
                        await update_stats()
                        await insert_syslog("info", "APP查询", f"目标 {current_gid} APP查询完成，新增 {len(app_list)} 条记录")
                except Exception as e:
                    logger.error(f"TYC Query exception for app: {e}")
                    error_msg.append(f"app error: {str(e)}")
                    await insert_syslog("error", "APP查询", f"目标 {current_gid} APP查询异常: {str(e)}")
                    
            # 微信公众号
            if "wechat" in query_types:
                try:
                    await insert_syslog("info", "微信查询", f"正在查询目标 {current_gid} 的微信公众号...")
                    wechat_list = await client.get_wechat_list(current_gid)
                    if wechat_list:
                        for item in wechat_list:
                            item['task_id'] = task_id
                            item['query_type'] = 'wechat'
                            await db['icp_asset'].insert_one(item)
                        counts["wechat"] += len(wechat_list)
                        total_assets += len(wechat_list)
                        await update_stats()
                        await insert_syslog("info", "微信查询", f"目标 {current_gid} 微信查询完成，新增 {len(wechat_list)} 条记录")
                except Exception as e:
                    logger.error(f"TYC Query exception for wechat: {e}")
                    error_msg.append(f"wechat error: {str(e)}")
                    await insert_syslog("error", "微信查询", f"目标 {current_gid} 微信查询异常: {str(e)}")
                    
            # 微博
            if "weibo" in query_types:
                try:
                    await insert_syslog("info", "微博查询", f"正在查询目标 {current_gid} 的微博...")
                    weibo_list = await client.get_weibo_list(current_gid)
                    if weibo_list:
                        for item in weibo_list:
                            item['task_id'] = task_id
                            item['query_type'] = 'weibo'
                            await db['icp_asset'].insert_one(item)
                        counts["weibo"] += len(weibo_list)
                        total_assets += len(weibo_list)
                        await update_stats()
                        await insert_syslog("info", "微博查询", f"目标 {current_gid} 微博查询完成，新增 {len(weibo_list)} 条记录")
                except Exception as e:
                    logger.error(f"TYC Query exception for weibo: {e}")
                    error_msg.append(f"weibo error: {str(e)}")
                    await insert_syslog("error", "微博查询", f"目标 {current_gid} 微博查询异常: {str(e)}")
                    
            # 微信小程序
            if "mapp" in query_types:
                try:
                    await insert_syslog("info", "小程序查询", f"正在查询目标 {current_gid} 的小程序...")
                    mapp_list = await client.get_mini_program_list(current_gid)
                    if mapp_list:
                        for item in mapp_list:
                            item['task_id'] = task_id
                            item['query_type'] = 'mapp'
                            await db['icp_asset'].insert_one(item)
                        counts["mapp"] += len(mapp_list)
                        total_assets += len(mapp_list)
                        await update_stats()
                        await insert_syslog("info", "小程序查询", f"目标 {current_gid} 小程序查询完成，新增 {len(mapp_list)} 条记录")
                except Exception as e:
                    logger.error(f"TYC Query exception for mapp: {e}")
                    error_msg.append(f"mapp error: {str(e)}")
                    await insert_syslog("error", "小程序查询", f"目标 {current_gid} 小程序查询异常: {str(e)}")

        gids_to_query = next_gids
        if not gids_to_query:
            break
    update_data = {
        "$set": {
            "status": "done" if not error_msg else "error", 
            "end_time": curr_date(),
            "statistic": {
                "asset_cnt": total_assets, 
                "invest_cnt": counts["invest"],
                "web_cnt": counts["web"],
                "app_cnt": counts["app"],
                "mapp_cnt": counts["mapp"],
                "wechat_cnt": counts["wechat"],
                "weibo_cnt": counts["weibo"],
            }
        }
    }
    if error_msg:
        update_data["$set"]["error_msg"] = "; ".join(error_msg)
    await db['icp_task'].update_one({"_id": ObjectId(task_id)}, update_data)
    await insert_syslog("info", "任务完成", f"TYC查询任务执行结束，共获取 {total_assets} 条资产")
    logger.info(f"TYC query task {task_id} completed.")

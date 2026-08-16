from aiohttp import web
import asyncio
import logging

logger = logging.getLogger(__name__)

background_tasks = set()

async def watchdog_task(app):
    """异步看门狗：定时轮询 MongoDB 获取最新并发配置并热更新"""
    task_manager = app.get('task_manager')
    # 第一次获取动态信号量，设置兜底默认值 1
    semaphore = task_manager.get_semaphore("recon_task", 1, dynamic=True)
    try:
        from clients.job_runner import db
        while True:
            try:
                db_config = await db.system_config.find_one({"_id": "performance"})
                limit = db_config.get("osint_concurrency", 1) if db_config else 1
                if hasattr(semaphore, "set_limit"):
                    await semaphore.set_limit(limit)
            except Exception as e:
                logger.error(f"Watchdog failed to fetch config: {e}")
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass

async def start_recon(request):
    try:
        data = await request.json()
        task_id = data.get("task_id")
        if not task_id:
            return web.json_response({"code": 400, "msg": "Missing task_id"})
        
        task_manager = request.app.get('task_manager')
        # 这里仅获取，不硬编码 limit
        semaphore = task_manager.get_semaphore("recon_task", 1, dynamic=True)
        
        from clients.job_runner import run_recon_job
        
        async def bounded_recon_job():
            async with semaphore:
                await run_recon_job(data)
                
        task = asyncio.create_task(bounded_recon_job())
        background_tasks.add(task)
        task_manager.add_task(task_id, task)
        
        def handle_task_result(t):
            background_tasks.discard(t)
            try:
                t.result()
            except Exception as e:
                logger.error(f"Background task crashed: {e}", exc_info=True)
                
        task.add_done_callback(handle_task_result)
        return web.json_response({"code": 200, "msg": "Task accepted", "task_id": task_id})
    except Exception as e:
        return web.json_response({"code": 500, "msg": str(e)})

async def stop_recon(request):
    try:
        data = await request.json()
        task_id = data.get("task_id")
        if not task_id:
            return web.json_response({"code": 400, "msg": "Missing task_id"})
        
        task_manager = request.app.get('task_manager')
        task_manager.remove_task(task_id)
        logger.info(f"Task {task_id} cancel requested via API.")
        return web.json_response({"code": 200, "msg": "Task stopped", "task_id": task_id})
    except Exception as e:
        return web.json_response({"code": 500, "msg": str(e)})

def setup_recon_routes(app):
    app.router.add_post("/api/v1/recon/start", start_recon)
    app.router.add_post("/api/v1/recon/stop", stop_recon)
    
    async def start_watchdog(app):
        app["watchdog_task"] = asyncio.create_task(watchdog_task(app))
        
    async def cleanup_watchdog(app):
        if "watchdog_task" in app:
            app["watchdog_task"].cancel()
            try:
                await app["watchdog_task"]
            except asyncio.CancelledError:
                pass
                
    app.on_startup.append(start_watchdog)
    app.on_cleanup.append(cleanup_watchdog)

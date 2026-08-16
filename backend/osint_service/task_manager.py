# -*- coding: utf-8 -*-
"""
任务管理器模块
用于管理异步任务和信号量
"""
import asyncio
import weakref
import signal
import sys
from mlog import logger


class DynamicSemaphore:
    def __init__(self, limit: int):
        self._limit = limit
        self._current = 0
        self._cond = asyncio.Condition()

    async def acquire(self):
        async with self._cond:
            while self._current >= self._limit:
                await self._cond.wait()
            self._current += 1

    async def release(self):
        async with self._cond:
            self._current -= 1
            self._cond.notify(1)

    async def set_limit(self, new_limit: int):
        async with self._cond:
            if new_limit != self._limit:
                self._limit = new_limit
                self._cond.notify_all()
                
    async def __aenter__(self):
        await self.acquire()
        return None

    async def __aexit__(self, exc_type, exc, tb):
        await self.release()

class TaskManager:
    """全局任务管理器"""
    def __init__(self):
        self._tasks = weakref.WeakValueDictionary()
        self._semaphores = {}
        
    def add_task(self, task_name, task):
        """添加任务"""
        self._tasks[task_name] = task
        
    def get_task(self, task_name):
        """获取任务"""
        return self._tasks.get(task_name)
        
    def remove_task(self, task_name):
        """移除任务"""
        if task_name in self._tasks:
            task = self._tasks[task_name]
            if not task.done():
                task.cancel()
            del self._tasks[task_name]
            
    def get_semaphore(self, name, limit, dynamic=False):
        """获取信号量"""
        if name not in self._semaphores:
            if dynamic:
                self._semaphores[name] = DynamicSemaphore(limit)
            else:
                self._semaphores[name] = asyncio.Semaphore(limit)
        return self._semaphores[name]


def setup_signal_handlers(task_manager):
    """设置信号处理器"""
    def signal_handler(sig, frame):
        if sig == signal.SIGINT:
            logger.warning('收到关闭信号，程序停止')
            # 清理所有任务
            for task_name in list(task_manager._tasks.keys()):
                task_manager.remove_task(task_name)
            sys.exit()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


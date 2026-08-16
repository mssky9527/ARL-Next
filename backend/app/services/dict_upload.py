import os
import time
import threading
import uuid
from app.utils import get_logger
from app.utils import conn_db as conn

logger = get_logger()

def background_process_dict(task_id, temp_file_path, target_dict_path):
    """
    后台处理字典：逐行读取临时文件，进行去重，并追加到目标字典中
    """
    try:
        # 初始化任务状态
        conn('dict_upload_task').insert_one({
            "task_id": task_id,
            "status": "processing",
            "progress": 0,
            "total_lines": 0,
            "inserted_lines": 0,
            "ignored_lines": 0,
            "message": "正在加载现有字典...",
            "create_time": int(time.time()),
            "update_time": int(time.time())
        })

        existing_set = set()
        
        # 1. 预加载现有字典用于去重
        if os.path.exists(target_dict_path):
            with open(target_dict_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_set.add(line)
        
        conn('dict_upload_task').update_one(
            {"task_id": task_id},
            {"$set": {"message": "正在解析上传文件...", "update_time": int(time.time())}}
        )

        # 2. 获取上传文件的总行数（用于进度计算）
        total_lines = 0
        with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in f:
                total_lines += 1
                
        conn('dict_upload_task').update_one(
            {"task_id": task_id},
            {"$set": {"total_lines": total_lines, "update_time": int(time.time())}}
        )

        inserted_lines = 0
        ignored_lines = 0
        processed_lines = 0
        
        # 3. 逐行读取，去重并追加
        with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as fin:
            with open(target_dict_path, 'a', encoding='utf-8') as fout:
                for line in fin:
                    line = line.strip()
                    processed_lines += 1
                    
                    if line and line not in existing_set:
                        fout.write(line + "\n")
                        existing_set.add(line)
                        inserted_lines += 1
                    elif line:
                        ignored_lines += 1
                        
                    # 每处理 10000 行更新一次进度，避免频繁写库
                    if processed_lines % 10000 == 0:
                        progress = int((processed_lines / total_lines) * 100) if total_lines > 0 else 100
                        conn('dict_upload_task').update_one(
                            {"task_id": task_id},
                            {"$set": {
                                "progress": progress,
                                "inserted_lines": inserted_lines,
                                "ignored_lines": ignored_lines,
                                "message": f"正在处理... ({processed_lines}/{total_lines})",
                                "update_time": int(time.time())
                            }}
                        )

        # 4. 处理完成
        conn('dict_upload_task').update_one(
            {"task_id": task_id},
            {"$set": {
                "status": "completed",
                "progress": 100,
                "inserted_lines": inserted_lines,
                "ignored_lines": ignored_lines,
                "message": "导入完成",
                "update_time": int(time.time())
            }}
        )
        logger.info(f"Dict upload task {task_id} completed. Inserted: {inserted_lines}, Ignored: {ignored_lines}")

    except Exception as e:
        logger.error(f"Error in dict upload task {task_id}: {e}")
        conn('dict_upload_task').update_one(
            {"task_id": task_id},
            {"$set": {
                "status": "error",
                "message": f"处理出错: {str(e)}",
                "update_time": int(time.time())
            }}
        )
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.error(f"Failed to remove temp file {temp_file_path}: {e}")

def trigger_dict_upload_task(temp_file_path, target_dict_path):
    """
    生成任务 ID 并启动后台线程
    """
    task_id = str(uuid.uuid4())
    t = threading.Thread(target=background_process_dict, args=(task_id, temp_file_path, target_dict_path))
    t.daemon = True
    t.start()
    return task_id

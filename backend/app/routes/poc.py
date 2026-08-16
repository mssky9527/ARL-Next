import os
from flask import request
from xing.conf import Conf as npoc_conf
from flask_restx import fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.services.npoc import NPoC
from app import utils
from app.modules import ErrorMsg

ns = Namespace('poc', description="PoC信息")

logger = get_logger()

base_search_fields = {
    'plugin_name': fields.String(description="PoC 名称 ID"),
    'app_name': fields.String(description="应用名称"),
    'scheme': fields.String(description="支持的协议"),
    'vul_name': fields.String(description="漏洞名称"),
    'plugin_type': fields.String(description="插件类别", enum=['poc', 'brute']),
    'update_date': fields.String(description="更新时间"),
    'category': fields.String(description="PoC 分类")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLPoC(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        PoC 信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args,  collection='poc')

        return data


@ns.route('/sync/')
class ARLPoCSync(ARLResource):

    @auth
    def get(self):
        """
        更新 PoC 信息
        """
        n = NPoC()
        plugin_cnt = len(n.plugin_name_list)
        n.sync_to_db()
        n.delete_db()

        return utils.build_ret(ErrorMsg.Success, {"plugin_cnt": plugin_cnt})


@ns.route('/delete/')
class ARLPoCDelete(ARLResource):

    @auth
    def get(self):
        """
        清空 PoC 信息
        """
        result = utils.conn_db('poc').delete_many({})
        delete_cnt = result.deleted_count

        # 级联清空 policy 表中的所有相关引用
        utils.conn_db('policy').update_many(
            {},
            {
                "$set": {
                    "policy.poc_config": [],
                    "policy.brute_config": []
                }
            }
        )

        return utils.build_ret(ErrorMsg.Success, {"delete_cnt": delete_cnt})

    @auth
    def post(self):
        """
        批量删除 PoC 信息
        """
        args = request.json or {}
        plugin_names = args.get('plugin_names', [])
        
        if not plugin_names:
            return utils.build_ret(ErrorMsg.Error, {'error': '未提供要删除的 PoC plugin_names'})

        # 1. 从 DB 删除
        result = utils.conn_db('poc').delete_many({'plugin_name': {'$in': plugin_names}})
        delete_cnt = result.deleted_count
        
        # 2. 级联清空 policy 表中的相关引用
        utils.conn_db('policy').update_many(
            {},
            {
                "$pull": {
                    "policy.poc_config": {"plugin_name": {"$in": plugin_names}},
                    "policy.brute_config": {"plugin_name": {"$in": plugin_names}}
                }
            }
        )

        # 3. 从磁盘删除实际脚本文件
        plugins_dir = npoc_conf.SYSTEM_PLUGINS_DIR
        for name in plugin_names:
            for ext in ['.py', '.yml', '.yaml']:
                file_path = os.path.join(plugins_dir, f"{name}{ext}")
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Failed to remove poc file: {file_path}, err: {e}")
                        
        return utils.build_ret(ErrorMsg.Success, {"delete_cnt": delete_cnt})



@ns.route('/import/')
class ARLPoCImport(ARLResource):

    @auth
    def post(self):
        """
        导入 PoC 文件 (支持单文件和多文件)
        """
        if 'file' not in request.files:
            return utils.build_ret(ErrorMsg.Error, {'error': 'No file part'})

        files = request.files.getlist('file')
        if not files or len(files) == 0:
            return utils.build_ret(ErrorMsg.Error, {'error': 'No selected file'})

        plugins_dir = npoc_conf.SYSTEM_PLUGINS_DIR
        
        success_count = 0
        fail_count = 0
        fail_details = []
        
        for file in files:
            if file.filename == '':
                continue
                
            # 只支持 .py, .yml, .yaml
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ['.py', '.yml', '.yaml']:
                fail_count += 1
                fail_details.append({"filename": file.filename, "reason": "不支持的文件格式，仅支持 .py, .yml, .yaml"})
                continue
                
            try:
                # 简单防止路径穿越
                safe_filename = os.path.basename(file.filename)
                save_path = os.path.join(plugins_dir, safe_filename)
                file.save(save_path)
                success_count += 1
            except Exception as e:
                fail_count += 1
                fail_details.append({"filename": file.filename, "reason": str(e)})

        # 文件保存后，触发一次同步操作
        n = NPoC()
        len(n.plugin_name_list)
        
        try:
            n.sync_to_db()
            n.delete_db()
        except Exception as e:
            logger.error(f"PoC 同步失败: {e}")
            return utils.build_ret(ErrorMsg.Error, {'error': f'PoC 保存成功，但同步到数据库时失败: {e}'})

        return utils.build_ret(ErrorMsg.Success, {
            "success_count": success_count,
            "fail_count": fail_count,
            "fail_details": fail_details
        })

@ns.route('/source/')
class ARLPoCSource(ARLResource):

    @auth
    def get(self):
        """
        获取 PoC 源码
        """
        plugin_name = request.args.get('plugin_name')
        if not plugin_name:
            return utils.build_ret(ErrorMsg.Error, {'error': '未提供 plugin_name'})
        
        plugins_dir = npoc_conf.SYSTEM_PLUGINS_DIR
        file_path = ""
        for root, dirs, files in os.walk(plugins_dir):
            for ext in ['.py', '.yml', '.yaml']:
                if f"{plugin_name}{ext}" in files:
                    file_path = os.path.join(root, f"{plugin_name}{ext}")
                    break
            if file_path:
                break
        
        if not file_path:
            return utils.build_ret(ErrorMsg.Error, {'error': 'PoC 文件未找到'})
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return utils.build_ret(ErrorMsg.Error, {'error': f'读取文件失败: {e}'})
            
        return utils.build_ret(ErrorMsg.Success, {'content': content})

    @auth
    def post(self):
        """
        更新 PoC 源码
        """
        args = request.json or {}
        plugin_name = args.get('plugin_name')
        content = args.get('content')
        
        if not plugin_name or content is None:
            return utils.build_ret(ErrorMsg.Error, {'error': '未提供 plugin_name 或 content'})
            
        plugins_dir = npoc_conf.SYSTEM_PLUGINS_DIR
        file_path = ""
        for root, dirs, files in os.walk(plugins_dir):
            for ext in ['.py', '.yml', '.yaml']:
                if f"{plugin_name}{ext}" in files:
                    file_path = os.path.join(root, f"{plugin_name}{ext}")
                    break
            if file_path:
                break
                
        if not file_path:
            return utils.build_ret(ErrorMsg.Error, {'error': 'PoC 文件未找到'})
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            return utils.build_ret(ErrorMsg.Error, {'error': f'保存文件失败: {e}'})
            
        # 保存后同步更新到数据库
        n = NPoC()
        try:
            n.sync_to_db()
            n.delete_db()
        except Exception as e:
            logger.error(f"PoC 同步失败: {e}")
            return utils.build_ret(ErrorMsg.Error, {'error': f'PoC 保存成功，但同步到数据库时失败: {e}'})

        return utils.build_ret(ErrorMsg.Success, {'message': '保存成功'})


@ns.route('/create/')
class ARLPoCCreate(ARLResource):

    @auth
    def post(self):
        """
        新建 PoC 源码
        """
        args = request.json or {}
        plugin_name = args.get('plugin_name')
        content = args.get('content')
        ext = args.get('ext', '.py')
        
        if not plugin_name or content is None:
            return utils.build_ret(ErrorMsg.Error, {'error': '未提供 plugin_name 或 content'})
            
        plugins_dir = npoc_conf.SYSTEM_PLUGINS_DIR
        
        # 简单校验文件名合法性，防止路径穿越
        if not plugin_name.replace('_', '').isalnum():
            return utils.build_ret(ErrorMsg.Error, {'error': '插件名称只允许字母、数字和下划线'})
            
        # 根据后缀放入对应的基础目录，如果想完全贴合原有分类，这里统一放入 poc 目录
        poc_dir = os.path.join(plugins_dir, 'poc')
        if not os.path.exists(poc_dir):
            poc_dir = plugins_dir
            
        file_path = os.path.join(poc_dir, f"{plugin_name}{ext}")
        if os.path.exists(file_path):
            return utils.build_ret(ErrorMsg.Error, {'error': '该插件名称已存在，请更换！'})
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            return utils.build_ret(ErrorMsg.Error, {'error': f'保存文件失败: {e}'})
            
        # 保存后同步更新到数据库
        n = NPoC()
        try:
            n.sync_to_db()
            n.delete_db()
        except Exception as e:
            logger.error(f"PoC 同步失败: {e}")
            return utils.build_ret(ErrorMsg.Error, {'error': f'PoC 保存成功，但同步到数据库时失败: {e}'})

        return utils.build_ret(ErrorMsg.Success, {'message': '新建成功'})



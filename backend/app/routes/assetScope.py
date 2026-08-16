import re
from bson import ObjectId
from flask_restx import fields, Namespace
from app.utils import get_logger, auth
from app import utils
from . import base_query_fields, ARLResource, get_arl_parser
from app.utils import conn_db as conn
from app.modules import ErrorMsg, AssetScopeType

# 成立“资产组范围”部门，专门管理“地契”
ns = Namespace('asset_scope', description="资产组范围")

logger = get_logger()

# ==========================================
# 表单：新建和查询时用到的基础字段
# ==========================================
base_fields = {
    'name': fields.String(description="资产组名称"),
    'scope': fields.String(description="资产范围"),
    "black_scope": fields.String(description="资产黑名单"),
    "scope_type": fields.String(description="资产范围类别")
}


add_asset_scope_fields = ns.model('addAssetScope', base_fields)

# 查询时多加一个 _id 和 分页字段
base_fields.update({
    "_id": fields.String(description="资产范围 ID")
})

base_fields.update(base_query_fields)


@ns.route('/')
class ARLAssetScope(ARLResource):
    parser = get_arl_parser(base_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产组查看
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='asset_scope')

        # 历史数据兼容：如果发现没有 domain_array 字段，说明是旧版结构，动态赋予它
        for item in data.get("items", []):
            if "domain_array" not in item:
                st = item.get("scope_type")
                sa = item.get("scope_array", [])
                if st == AssetScopeType.DOMAIN:
                    item["domain_array"] = sa
                    item["ip_array"] = []
                elif st == AssetScopeType.IP:
                    item["domain_array"] = []
                    item["ip_array"] = sa
                else:
                    item["domain_array"] = []
                    item["ip_array"] = []

        return data

    @auth
    @ns.expect(add_asset_scope_fields)
    def post(self):
        """
        资产组添加：创建一个新的地契
        """
        args = self.parse_args(add_asset_scope_fields)
        name = args.pop('name')
        scope = args.pop('scope')
        black_scope = args.pop('black_scope')
        # scope_type 前端已不再强传，即使传了也仅作为冗余兜底
        scope_type = args.pop('scope_type', "mixed")

        black_scope_array = []
        if black_scope:
            black_scope_array = re.split(r",|\s", black_scope)

        scope_array = re.split(r",|\s", scope)
        scope_array = list(filter(None, scope_array))

        new_scope_array = []
        domain_array = []
        ip_array = []

        # 4. 【核心验证】：智能探测并分流
        for x in scope_array:
            if utils.is_valid_domain(x):
                new_scope_array.append(x)
                domain_array.append(x)
            else:
                transfer = utils.ip.transfer_ip_scope(x)
                if transfer is not None:
                    new_scope_array.append(transfer)
                    ip_array.append(transfer)
                else:
                    return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": x, "error": "非法的域名或IP格式"})

        if not new_scope_array:
            return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": ""})

        # 5. 组装数据，实行“双轨制”存储
        scope_data = {
            "name": name,
            "scope_type": scope_type,
            "scope": ",".join(new_scope_array),
            "scope_array": new_scope_array,
            "domain_array": domain_array,
            "ip_array": ip_array,
            "black_scope": black_scope,
            "black_scope_array": black_scope_array,
        }
        conn('asset_scope').insert(scope_data)

        # 补全返回数据
        scope_id = str(scope_data.pop("_id"))
        scope_data["scope_id"] = scope_id

        return utils.build_ret(ErrorMsg.Success, scope_data)

# ==========================================
# 接口模块：删除相关 (包含部分删除 和 整体销毁)
# ==========================================
delete_task_get_fields = ns.model('DeleteScopeByID',  {
    'scope': fields.String(description="删除资产范围", required=True),
    'scope_id': fields.String(description="资产范围id", required=True)
})


delete_task_post_fields = ns.model('DeleteScope',  {
    'scope_id': fields.List(fields.String(description="删除资产范围", required=True), required=True)
})


@ns.route('/delete/')
class DeleteARLAssetScope(ARLResource):
    parser = get_arl_parser(delete_task_get_fields, location='args')

    _table = 'asset_scope'

    # 接口 A：局部删除 (GET) - 从某个资产组里，剔除一个具体的域名
    @auth
    @ns.expect(parser)
    def get(self):
        """
        针对资产组删除范围
        """
        args = self.parser.parse_args()
        scope = str(args.pop('scope', "")).lower()  # 比如要删 "baidu.com"
        scope_id = str(args.pop('scope_id', "")).lower()# 在 "资产组A" 里面

        scope_data = self.get_scope_data(scope_id)
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        query = {'_id': ObjectId(scope_id)}

        # 防御：要删的东西根本不在这里面
        if scope not in scope_data.get("scope_array", []):
            return utils.build_ret(ErrorMsg.NotFoundScope, {"scope_id": scope_id, "scope":scope})

        # 核心：操作 Python 列表剔除元素，并同步剔除子轨道
        scope_data["scope_array"].remove(scope)
        if "domain_array" in scope_data and scope in scope_data["domain_array"]:
            scope_data["domain_array"].remove(scope)
        if "ip_array" in scope_data and scope in scope_data["ip_array"]:
            scope_data["ip_array"].remove(scope)

        scope_data["scope"] = ",".join(scope_data["scope_array"])
        utils.conn_db(self._table).find_one_and_replace(query, scope_data)
        
        # --- 新增：深度级联清理孤儿记录 (级联删除属于该资产的所有子资产) ---
        # 清理由于将该主干目标踢出 Scope 而产生的废弃监控状态和指纹历史
        utils.conn_db("asset_domain").delete_many({"scope_id": scope_id, "domain": scope})
        utils.conn_db("asset_ip").delete_many({"scope_id": scope_id, "ip": scope})
        
        # 站点与WIH不仅通过 scope_id 关联，还需要过滤出归属于刚被删除的 scope (即基准 domain/ip) 的记录
        # 我们这里采用以 domain/ip 作为精确匹配 (通常子系统收集资产时会保存关联的 base_domain/ip 到 domain 字段)
        utils.conn_db("asset_site").delete_many({"scope_id": scope_id, "domain": scope})
        utils.conn_db("asset_wih").delete_many({"scope_id": scope_id, "domain": scope})

        return utils.build_ret(ErrorMsg.Success, {"scope_id": scope_id, "scope":scope})

    def get_scope_data(self, scope_id):
        query = {'_id': ObjectId(scope_id)}
        scope_data = utils.conn_db(self._table).find_one(query)
        return scope_data

    # 接口 B：整体销毁 (POST) - 连锅端！
    @auth
    @ns.expect(delete_task_post_fields)
    def post(self):
        """
        删除资产组和资产组中的资产 (极其危险的操作)
        """
        args = self.parse_args(delete_task_post_fields)
        scope_id_list = args.pop('scope_id')

        # 1. 第一轮循环：纯校验
        for scope_id in scope_id_list:
            if not self.get_scope_data(scope_id):
                return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        # 2. 定义受牵连的表（因为你把地契烧了，那这块地上的所有财产全得清空）
        table_list = ["asset_domain", "asset_site", "asset_ip", "scheduler", "asset_wih"]

        # 3. 第二轮循环：大清洗 (级联删除)
        for scope_id in scope_id_list:
            # 删地契本身
            utils.conn_db(self._table).delete_many({'_id': ObjectId(scope_id)})

            # 删牵连的战利品
            for name in table_list:
                utils.conn_db(name).delete_many({'scope_id': scope_id})

        return utils.build_ret(ErrorMsg.Success, {"scope_id": scope_id_list})


# ==========================================
# 接口：向现有资产组追加新域名 (POST /add/)
# ==========================================
add_scope_fields = ns.model('AddScope',  {
    'scope': fields.String(description="添加资产范围"),
    "scope_id": fields.String(description="添加资产范围")
})


@ns.route('/add/')
class AddARLAssetScope(ARLResource):
    @auth
    @ns.expect(add_scope_fields)
    def post(self):
        """
        添加资产范围(局部追加)
        """
        args = self.parse_args(add_scope_fields)
        scope = str(args.pop('scope', "")).lower()

        scope_id = args.pop('scope_id', "")

        table = 'asset_scope'
        query = {'_id': ObjectId(scope_id)}
        scope_data = utils.conn_db(table).find_one(query)
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id, "scope": scope})

        # 兜底旧数据
        if "domain_array" not in scope_data:
            st = scope_data.get("scope_type")
            sa = scope_data.get("scope_array", [])
            scope_data["domain_array"] = list(sa) if st == AssetScopeType.DOMAIN else []
            scope_data["ip_array"] = list(sa) if st == AssetScopeType.IP else []

        scope_array = re.split(r",|\s", scope)
        scope_array = list(filter(None, scope_array))
        if not scope_array:
            return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": ""})

        for x in scope_array:
            new_scope = x
            if utils.is_valid_domain(x):
                if new_scope in scope_data.get("scope_array", []):
                    return utils.build_ret(ErrorMsg.ExistScope, {"scope_id": scope_id, "scope": x})
                scope_data["scope_array"].append(new_scope)
                scope_data["domain_array"].append(new_scope)
            else:
                transfer = utils.ip.transfer_ip_scope(x)
                if transfer is not None:
                    new_scope = transfer
                    if new_scope in scope_data.get("scope_array", []):
                        return utils.build_ret(ErrorMsg.ExistScope, {"scope_id": scope_id, "scope": x})
                    scope_data["scope_array"].append(new_scope)
                    scope_data["ip_array"].append(new_scope)
                else:
                    return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": x, "error": "非法的域名或IP格式"})

        scope_data["scope"] = ",".join(scope_data["scope_array"])
        utils.conn_db(table).find_one_and_replace(query, scope_data)

        return utils.build_ret(ErrorMsg.Success, {"scope_id": scope_id, "scope": scope})
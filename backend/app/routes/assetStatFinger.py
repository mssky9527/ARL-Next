from bson import ObjectId
from flask_restx import fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import ErrorMsg
from app import utils

ns = Namespace('asset_stat_finger', description="资产组指纹统计信息")

logger = get_logger()

base_search_fields = {
    'name': fields.String(required=False, description="指纹名称"),
    'name__eq': fields.String(required=False, description="指纹名称精确匹配"),
    "cnt": fields.Integer(description="数目"),
    "update_date__dgt": fields.String(description="更新时间大于"),
    "update_date__dlt": fields.String(description="更新时间小于"),
    "insert_time__dgt": fields.String(description="插入时间大于"),
    "insert_time__dlt": fields.String(description="插入时间小于"),
    "scope_id": fields.String(description="资产范围ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLAssetStatFinger(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产组指纹统计信息查询
        """
        args = self.parser.parse_args()
        query = self.build_db_query(args)

        pipeline = [
            {"$match": query},
            {"$group": {"_id": "$name", "cnt": {"$sum": "$cnt"}}},
            {"$project": {"_id": 0, "name": "$_id", "cnt": 1}},
            {"$sort": {"cnt": -1}},
            {"$skip": (args.page - 1) * args.size},
            {"$limit": args.size}
        ]
        items = list(utils.conn_db('asset_stat_finger').aggregate(pipeline))

        count_pipeline = [
            {"$match": query},
            {"$group": {"_id": "$name"}}
        ]
        total = len(list(utils.conn_db('asset_stat_finger').aggregate(count_pipeline)))

        return {
            "total": total,
            "items": items,
            "code": 200
        }


@ns.route('/export/')
class ARLAssetStatFingerExport(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产组指纹统计信息导出
        """
        args = self.parser.parse_args()
        response = self.send_export_file(args=args, _type="asset_stat_finger")
        return response


delete_statfinger_fields = ns.model('deleteAssetStatFinger',  {
    '_id': fields.List(fields.String(required=True, description="数据_id"))
})


@ns.route('/delete/')
class DeleteARLAssetStatFinger(ARLResource):
    @auth
    @ns.expect(delete_statfinger_fields)
    def post(self):
        """
        删除资产组指纹统计信息
        """
        args = self.parse_args(delete_statfinger_fields)
        id_list = args.pop('_id', "")

        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('asset_stat_finger').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})

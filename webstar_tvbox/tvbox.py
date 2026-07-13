# -*- coding: utf-8 -*-
"""
TVBox / 影视仓 / OK影视 / 猫影视 数据接口适配
接口规范：
- ac=list          返回分类列表
- ac=detail&ids=   返回影片详情
- ac=videolist&t=  返回某分类影片列表（pg 分页）
- wd=关键词&pg=    搜索
返回字段保持标准 TVBox JSON 格式。
"""
import json
import logging
from typing import Dict, Optional

from aiohttp import web

import config
from database import VodDatabase

logger = logging.getLogger(__name__)


def _row_to_vod(row: Dict) -> Dict:
    return {
        "vod_id": row.get("vod_id", ""),
        "vod_name": row.get("vod_name", ""),
        "vod_pic": row.get("vod_pic", ""),
        "vod_remarks": row.get("vod_remarks", ""),
        "vod_year": row.get("vod_year", ""),
        "vod_area": row.get("vod_area", ""),
        "vod_lang": row.get("vod_lang", ""),
        "vod_actor": row.get("vod_actor", ""),
        "vod_director": row.get("vod_director", ""),
        "vod_content": row.get("vod_content", ""),
        "vod_play_from": row.get("vod_play_from", ""),
        "vod_play_url": row.get("vod_play_url", ""),
        "type_name": row.get("type_name", ""),
        "last_update": row.get("last_update", ""),
    }


class TvBoxAPI:
    def __init__(self, db: Optional[VodDatabase] = None):
        self.db = db or VodDatabase()

    def category(self) -> Dict:
        """分类接口 ac=list"""
        return {
            "code": 1,
            "msg": "success",
            "class": config.TYPE_LIST,
        }

    def videolist(self, type_id: str, page: int = 1, page_size: int = 20) -> Dict:
        """列表接口 ac=videolist&t=type_id&pg=page"""
        type_name = config.CATEGORIES.get(int(type_id), "") if type_id.isdigit() else ""
        offset = (page - 1) * page_size
        rows = self.db.query(type_name=type_name, limit=page_size, offset=offset)
        total = self.db.count(type_name=type_name)
        return {
            "code": 1,
            "msg": "success",
            "page": page,
            "pagecount": (total + page_size - 1) // page_size,
            "limit": page_size,
            "total": total,
            "list": [_row_to_vod(row) for row in rows],
        }

    def detail(self, ids: str) -> Dict:
        """详情接口 ac=detail&ids=vod_id"""
        row = self.db.get(ids)
        return {
            "code": 1,
            "msg": "success",
            "list": [_row_to_vod(row)] if row else [],
        }

    def search(self, keyword: str, page: int = 1, page_size: int = 20) -> Dict:
        """搜索接口 wd=keyword&pg=page"""
        offset = (page - 1) * page_size
        rows = self.db.query(keyword=keyword, limit=page_size, offset=offset)
        total = self.db.count(keyword=keyword)
        return {
            "code": 1,
            "msg": "success",
            "page": page,
            "pagecount": (total + page_size - 1) // page_size,
            "limit": page_size,
            "total": total,
            "list": [_row_to_vod(row) for row in rows],
        }


# aiohttp Web 服务路由
async def handle_api(request: web.Request) -> web.Response:
    db = request.app["db"]
    api = TvBoxAPI(db)

    ac = request.query.get("ac", "list")
    keyword = request.query.get("wd", "")

    if keyword:
        # 搜索：兼容 ?ac=list&wd=xxx&pg=1 与 /search?wd=xxx
        page = int(request.query.get("pg", 1))
        data = api.search(keyword, page=page)
    elif ac == "list":
        # 部分壳子用 ac=list&t=1&pg=1 请求列表；无 t 时返回分类
        type_id = request.query.get("t", "")
        if type_id:
            page = int(request.query.get("pg", 1))
            data = api.videolist(type_id, page=page)
        else:
            data = api.category()
    elif ac == "videolist":
        type_id = request.query.get("t", "1")
        page = int(request.query.get("pg", 1))
        data = api.videolist(type_id, page=page)
    elif ac == "detail":
        ids = request.query.get("ids", "")
        data = api.detail(ids)
    else:
        data = {"code": 0, "msg": "unknown ac"}

    return web.json_response(data, dumps=lambda o: json.dumps(o, ensure_ascii=False))


async def handle_search(request: web.Request) -> web.Response:
    db = request.app["db"]
    api = TvBoxAPI(db)
    keyword = request.query.get("wd", "")
    page = int(request.query.get("pg", 1))
    if not keyword:
        return web.json_response({"code": 0, "msg": "missing wd"})
    data = api.search(keyword, page=page)
    return web.json_response(data, dumps=lambda o: json.dumps(o, ensure_ascii=False))


def build_app(db: Optional[VodDatabase] = None) -> web.Application:
    app = web.Application()
    app["db"] = db or VodDatabase()
    app.router.add_get("/api.php", handle_api)
    app.router.add_get("/api.php/vod", handle_api)  # 部分壳子路径
    app.router.add_get("/vod", handle_api)
    app.router.add_get("/search", handle_search)
    return app


def run_server(host: str = "0.0.0.0", port: int = 8080, db_path: str = "webstar.db"):
    db = VodDatabase(db_path)
    app = build_app(db)
    logger.info("TVBox API server starting at http://%s:%s", host, port)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--db", default="webstar.db")
    args = parser.parse_args()
    run_server(args.host, args.port, args.db)

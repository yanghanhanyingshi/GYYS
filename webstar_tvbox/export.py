# -*- coding: utf-8 -*-
"""
JSON 导出工具
支持导出完整影片数据，或按 TVBox 列表/详情格式导出。
"""
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from database import VodDatabase

logger = logging.getLogger(__name__)


def _row_to_vod(row: Dict) -> Dict:
    """把数据库行转换为标准 vod 字典"""
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


def export_all(
    db: VodDatabase,
    output: str = "webstar_all.json",
    type_name: Optional[str] = None,
) -> int:
    """导出所有或某分类的影片数据"""
    rows = db.query(type_name=type_name, limit=1000000)
    data = {
        "site": "https://www.webstar.cn",
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(rows),
        "list": [_row_to_vod(row) for row in rows],
    }
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("exported %d rows to %s", len(rows), output)
    return len(rows)


def export_tvbox_list(
    db: VodDatabase,
    output: str = "webstar_list.json",
    type_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict:
    """导出 TVBox 列表格式 JSON"""
    offset = (page - 1) * page_size
    rows = db.query(type_name=type_name, limit=page_size, offset=offset)
    total = db.count(type_name=type_name)
    data = {
        "code": 1,
        "msg": "success",
        "page": page,
        "pagecount": (total + page_size - 1) // page_size,
        "limit": page_size,
        "total": total,
        "list": [_row_to_vod(row) for row in rows],
    }
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def export_tvbox_detail(db: VodDatabase, vod_id: str, output: str = "webstar_detail.json") -> Dict:
    """导出 TVBox 详情格式 JSON"""
    row = db.get(vod_id)
    data = {
        "code": 1,
        "msg": "success",
        "list": [_row_to_vod(row)] if row else [],
    }
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data

# -*- coding: utf-8 -*-
"""
SQLite 数据存储与去重
支持增量更新：以 vod_id 为主键，仅当内容有变化或首次入库时更新。
"""
import sqlite3
import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS vods (
    vod_id          TEXT PRIMARY KEY,
    vod_name        TEXT NOT NULL,
    vod_pic         TEXT,
    vod_remarks     TEXT,
    vod_year        TEXT,
    vod_area        TEXT,
    vod_lang        TEXT,
    vod_actor       TEXT,
    vod_director    TEXT,
    vod_content     TEXT,
    vod_play_from   TEXT,
    vod_play_url    TEXT,
    type_name       TEXT,
    last_update     TEXT,
    source_json     TEXT,
    created_at      TEXT,
    updated_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_vods_type ON vods(type_name);
CREATE INDEX IF NOT EXISTS idx_vods_year ON vods(vod_year);
CREATE INDEX IF NOT EXISTS idx_vods_update ON vods(updated_at);
"""


class VodDatabase:
    def __init__(self, db_path: str = "webstar.db"):
        self.db_path = db_path
        # sqlite3 连接不能跨线程，使用线程锁 + 每次新建连接
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.executescript(SCHEMA)
            conn.commit()
            conn.close()

    @contextmanager
    def _transaction(self):
        with self._lock:
            conn = self._conn()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def exists(self, vod_id: str) -> bool:
        with self._transaction() as conn:
            cur = conn.execute("SELECT 1 FROM vods WHERE vod_id=?", (vod_id,))
            return cur.fetchone() is not None

    def upsert(self, vod: Dict) -> bool:
        """
        插入或更新一条影片数据。
        返回 True 表示发生写入（新增或内容变化），用于统计增量。
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        vod_id = str(vod.get("vod_id", ""))
        if not vod_id:
            logger.warning("upsert skipped: vod_id empty")
            return False

        # 计算指纹，用于判断内容是否变化
        fingerprint = self._fingerprint(vod)

        with self._transaction() as conn:
            row = conn.execute(
                "SELECT source_json, created_at FROM vods WHERE vod_id=?", (vod_id,)
            ).fetchone()
            if row:
                old_fp = self._fingerprint(json.loads(row["source_json"] or "{}"))
                if old_fp == fingerprint:
                    logger.debug("vod_id=%s unchanged", vod_id)
                    return False
                conn.execute(
                    """
                    UPDATE vods SET
                        vod_name=?, vod_pic=?, vod_remarks=?, vod_year=?,
                        vod_area=?, vod_lang=?, vod_actor=?, vod_director=?,
                        vod_content=?, vod_play_from=?, vod_play_url=?, type_name=?,
                        last_update=?, source_json=?, updated_at=?
                    WHERE vod_id=?
                    """,
                    (
                        vod.get("vod_name", ""),
                        vod.get("vod_pic", ""),
                        vod.get("vod_remarks", ""),
                        vod.get("vod_year", ""),
                        vod.get("vod_area", ""),
                        vod.get("vod_lang", ""),
                        vod.get("vod_actor", ""),
                        vod.get("vod_director", ""),
                        vod.get("vod_content", ""),
                        vod.get("vod_play_from", ""),
                        vod.get("vod_play_url", ""),
                        vod.get("type_name", ""),
                        vod.get("last_update", ""),
                        json.dumps(vod, ensure_ascii=False),
                        now,
                        vod_id,
                    ),
                )
                logger.info("vod_id=%s updated", vod_id)
                return True
            else:
                conn.execute(
                    """
                    INSERT INTO vods (
                        vod_id, vod_name, vod_pic, vod_remarks, vod_year,
                        vod_area, vod_lang, vod_actor, vod_director, vod_content,
                        vod_play_from, vod_play_url, type_name, last_update,
                        source_json, created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        vod_id,
                        vod.get("vod_name", ""),
                        vod.get("vod_pic", ""),
                        vod.get("vod_remarks", ""),
                        vod.get("vod_year", ""),
                        vod.get("vod_area", ""),
                        vod.get("vod_lang", ""),
                        vod.get("vod_actor", ""),
                        vod.get("vod_director", ""),
                        vod.get("vod_content", ""),
                        vod.get("vod_play_from", ""),
                        vod.get("vod_play_url", ""),
                        vod.get("type_name", ""),
                        vod.get("last_update", ""),
                        json.dumps(vod, ensure_ascii=False),
                        now,
                        now,
                    ),
                )
                logger.info("vod_id=%s inserted", vod_id)
                return True

    @staticmethod
    def _fingerprint(vod: Dict) -> str:
        keys = [
            "vod_name", "vod_pic", "vod_remarks", "vod_year", "vod_area",
            "vod_lang", "vod_actor", "vod_director", "vod_content",
            "vod_play_from", "vod_play_url", "type_name", "last_update",
        ]
        return "|".join(str(vod.get(k, "")) for k in keys)

    def query(
        self,
        type_name: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict]:
        sql = "SELECT * FROM vods WHERE 1=1"
        params = []
        if type_name:
            sql += " AND type_name=?"
            params.append(type_name)
        if keyword:
            sql += " AND (vod_name LIKE ? OR vod_actor LIKE ? OR vod_director LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._transaction() as conn:
            cur = conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def count(self, type_name: Optional[str] = None, keyword: Optional[str] = None) -> int:
        sql = "SELECT COUNT(*) AS c FROM vods WHERE 1=1"
        params = []
        if type_name:
            sql += " AND type_name=?"
            params.append(type_name)
        if keyword:
            sql += " AND (vod_name LIKE ? OR vod_actor LIKE ? OR vod_director LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        with self._transaction() as conn:
            cur = conn.execute(sql, params)
            return cur.fetchone()["c"]

    def get(self, vod_id: str) -> Optional[Dict]:
        with self._transaction() as conn:
            cur = conn.execute("SELECT * FROM vods WHERE vod_id=?", (vod_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_total(self) -> int:
        with self._transaction() as conn:
            cur = conn.execute("SELECT COUNT(*) AS c FROM vods")
            return cur.fetchone()["c"]

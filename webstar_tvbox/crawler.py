# -*- coding: utf-8 -*-
"""
异步影视数据采集器
支持：分类采集、自动翻页、详情补全、播放线路采集、自动去重、自动重试、异步并发。
"""
import re
import asyncio
import logging
from typing import List, Dict, Optional, Callable
from urllib.parse import urljoin

import aiohttp
import requests
from lxml import etree

import config
import detail
from database import VodDatabase

logger = logging.getLogger(__name__)


class WebstarCrawler:
    def __init__(
        self,
        db: Optional[VodDatabase] = None,
        concurrency: int = config.CONCURRENCY,
        retry: int = config.RETRY_TIMES,
        timeout: int = config.REQUEST_TIMEOUT,
    ):
        self.db = db or VodDatabase()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.retry = retry
        self.timeout = timeout
        self.headers = config.HEADERS
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(ssl=False, limit=50),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch(self, url: str, **kwargs) -> str:
        """带重试的异步 GET，返回 HTML 文本"""
        last_err = None
        for attempt in range(1, self.retry + 1):
            try:
                async with self.semaphore:
                    async with self.session.get(url, **kwargs) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=text[:200],
                                headers=resp.headers,
                            )
                        # 站点编码为 utf-8
                        return await resp.text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                last_err = exc
                logger.warning("fetch %s attempt %d/%d failed: %s", url, attempt, self.retry, exc)
                if attempt < self.retry:
                    await asyncio.sleep(config.RETRY_DELAY * attempt)
        raise last_err or Exception(f"fetch {url} failed")

    def fetch_sync(self, url: str) -> str:
        """同步 GET，用于非异步场景或快速测试"""
        for attempt in range(1, self.retry + 1):
            try:
                resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                resp.encoding = "utf-8"
                if resp.status_code == 200:
                    return resp.text
                raise requests.HTTPError(f"status {resp.status_code}")
            except Exception as exc:
                logger.warning("fetch_sync %s attempt %d/%d failed: %s", url, attempt, self.retry, exc)
                if attempt < self.retry:
                    import time
                    time.sleep(config.RETRY_DELAY * attempt)
        raise Exception(f"fetch_sync {url} failed")

    def parse_list_page(self, html_text: str, is_search: bool = False) -> List[Dict]:
        """解析一页列表，返回 vod_id, vod_name, vod_pic, vod_remarks"""
        tree = etree.HTML(html_text)
        results = []
        if is_search:
            items = tree.xpath(config.SELECTORS["search_item"])
        else:
            items = tree.xpath(config.SELECTORS["cat_item"])
        for item in items:
            parsed = detail.parse_list_item(item, is_search=is_search)
            if parsed:
                results.append(parsed)
        return results

    def parse_page_total(self, html_text: str) -> int:
        """从分页区提取总页数，如 '1/545' 返回 545"""
        # 优先匹配 "x/y" 文本
        m = re.search(r"(\d+)\s*/\s*(\d+)", html_text)
        if m:
            return int(m.group(2))
        # 兜底：从尾页链接取最大页码
        tree = etree.HTML(html_text)
        max_page = 1
        for href in tree.xpath("//ul[contains(@class,'myui-page')]//a/@href"):
            pm = re.search(r"--------(\d+)---\.html", href)
            if pm:
                max_page = max(max_page, int(pm.group(1)))
        return max_page

    async def crawl_list(
        self,
        type_id: int,
        max_pages: int = 0,
        fetch_play: bool = False,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> Dict:
        """
        采集某个分类下的列表与详情。
        :param type_id: 分类 ID
        :param max_pages: 最大翻页数，0 表示不限制
        :param fetch_play: 是否继续采集播放页
        :param progress_callback: 回调(current_page, total_pages, saved_count)
        :return: 统计信息
        """
        type_name = config.CATEGORIES.get(type_id, "")
        first_url = config.list_url(type_id, 1)
        first_html = await self.fetch(first_url)
        total_pages = self.parse_page_total(first_html)
        if max_pages > 0:
            total_pages = min(total_pages, max_pages)

        saved = 0
        page_saved = 0
        # 处理第一页
        page_saved = await self._process_list_page(first_html, type_name, fetch_play)
        saved += page_saved
        if progress_callback:
            progress_callback(1, total_pages, saved)

        # 翻页
        tasks = []
        for page in range(2, total_pages + 1):
            tasks.append(
                self._crawl_one_list_page(type_id, page, type_name, fetch_play)
            )
        for idx, coro in enumerate(asyncio.as_completed(tasks), start=2):
            try:
                page_saved = await coro
                saved += page_saved
            except Exception as exc:
                logger.error("list page error: %s", exc)
            if progress_callback:
                progress_callback(min(idx, total_pages), total_pages, saved)

        return {
            "type_id": type_id,
            "type_name": type_name,
            "total_pages": total_pages,
            "saved": saved,
        }

    async def _crawl_one_list_page(
        self, type_id: int, page: int, type_name: str, fetch_play: bool
    ) -> int:
        url = config.list_url(type_id, page)
        try:
            html = await self.fetch(url)
            return await self._process_list_page(html, type_name, fetch_play)
        except Exception as exc:
            logger.error("page %s error: %s", url, exc)
            return 0

    async def _process_list_page(
        self, html_text: str, type_name: str, fetch_play: bool
    ) -> int:
        items = self.parse_list_page(html_text, is_search=False)
        saved = 0
        if fetch_play:
            tasks = [self._crawl_detail(item, type_name) for item in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for vod in results:
                if isinstance(vod, Exception):
                    continue
                if self.db.upsert(vod):
                    saved += 1
        else:
            # 仅保存列表基础字段
            for item in items:
                item["type_name"] = type_name
                item["vod_play_from"] = ""
                item["vod_play_url"] = ""
                item["vod_year"] = ""
                item["vod_area"] = ""
                item["vod_actor"] = ""
                item["vod_director"] = ""
                item["vod_content"] = ""
                item["last_update"] = ""
                if self.db.upsert(item):
                    saved += 1
        return saved

    async def _crawl_detail(self, item: Dict, type_name: str) -> Dict:
        """根据列表项采集详情页与播放页"""
        vod_id = item["vod_id"]
        detail_url = config.detail_url(vod_id)
        detail_html = await self.fetch(detail_url)
        vod = detail.parse_detail(detail_html, type_name=type_name or item.get("type_name", ""))
        # 用列表页的图片/备注兜底
        vod.setdefault("vod_pic", item.get("vod_pic", ""))
        vod.setdefault("vod_remarks", item.get("vod_remarks", ""))

        # 播放页：默认取第一集
        play_html = await self.fetch(config.play_url(vod_id, 1, 1))
        source_names, episodes_list = detail.parse_play(play_html)
        vod = detail.merge_detail_play(vod, source_names, episodes_list)
        return vod

    async def fetch_detail_full(self, vod_id: str, type_name: str = "") -> Optional[Dict]:
        """采集单个影片的详情+播放"""
        try:
            detail_html = await self.fetch(config.detail_url(vod_id))
            vod = detail.parse_detail(detail_html, type_name=type_name)
            play_html = await self.fetch(config.play_url(vod_id, 1, 1))
            source_names, episodes_list = detail.parse_play(play_html)
            vod = detail.merge_detail_play(vod, source_names, episodes_list)
            self.db.upsert(vod)
            return vod
        except Exception as exc:
            logger.error("fetch_detail_full %s error: %s", vod_id, exc)
            return None

    async def fill_missing_details(
        self, limit: int = 100, concurrency: int = 4
    ) -> int:
        """
        增量补齐：数据库中缺少详情字段的记录，重新抓取详情页。
        """
        rows = self.db.query(limit=limit)
        tasks = []
        sem = asyncio.Semaphore(concurrency)

        async def _fill(row):
            async with sem:
                vod_id = row["vod_id"]
                if row.get("vod_content") and row.get("vod_play_url"):
                    return 0
                vod = await self.fetch_detail_full(vod_id, row.get("type_name", ""))
                return 1 if vod else 0

        for row in rows:
            tasks.append(_fill(row))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if isinstance(r, int) and r == 1)

# -*- coding: utf-8 -*-
"""
搜索采集模块
说明：
- 搜索接口为公开 GET：/vodsearch/{keyword}----------{page}---.html
- 搜索结果结构与分类列表不同，使用 detail.parse_list_item(is_search=True) 解析。
"""
import asyncio
import logging
from typing import Dict, List, Optional, Callable

from lxml import etree

import config
import detail
from crawler import WebstarCrawler

logger = logging.getLogger(__name__)


class WebstarSearch:
    def __init__(self, crawler: Optional[WebstarCrawler] = None):
        self.crawler = crawler or WebstarCrawler()

    async def search(
        self,
        keyword: str,
        max_pages: int = 1,
        fetch_play: bool = False,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> Dict:
        """
        按关键词搜索并入库。
        :param keyword: 关键词
        :param max_pages: 最大翻页数
        :param fetch_play: 是否继续抓详情+播放
        :return: 统计信息
        """
        first_url = config.search_url(keyword, 1)
        async with self.crawler:
            first_html = await self.crawler.fetch(first_url)
            total_pages = self.crawler.parse_page_total(first_html)
            if max_pages > 0:
                total_pages = min(total_pages, max_pages)

            saved = await self._process_search_page(first_html, fetch_play)
            if progress_callback:
                progress_callback(1, total_pages, saved)

            tasks = []
            for page in range(2, total_pages + 1):
                tasks.append(self._crawl_one_search_page(keyword, page, fetch_play))
            for idx, coro in enumerate(asyncio.as_completed(tasks), start=2):
                try:
                    page_saved = await coro
                    saved += page_saved
                except Exception as exc:
                    logger.error("search page error: %s", exc)
                if progress_callback:
                    progress_callback(min(idx, total_pages), total_pages, saved)

        return {
            "keyword": keyword,
            "total_pages": total_pages,
            "saved": saved,
        }

    async def _crawl_one_search_page(
        self, keyword: str, page: int, fetch_play: bool
    ) -> int:
        url = config.search_url(keyword, page)
        try:
            html = await self.crawler.fetch(url)
            return await self._process_search_page(html, fetch_play)
        except Exception as exc:
            logger.error("search %s page %d error: %s", keyword, page, exc)
            return 0

    async def _process_search_page(self, html_text: str, fetch_play: bool) -> int:
        items = self.crawler.parse_list_page(html_text, is_search=True)
        saved = 0
        if fetch_play:
            tasks = [self.crawler._crawl_detail(item, "") for item in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for vod in results:
                if isinstance(vod, Exception):
                    continue
                if self.crawler.db.upsert(vod):
                    saved += 1
        else:
            for item in items:
                item["vod_play_from"] = ""
                item["vod_play_url"] = ""
                item["vod_year"] = ""
                item["vod_area"] = ""
                item["vod_lang"] = ""
                item["vod_actor"] = ""
                item["vod_director"] = ""
                item["vod_content"] = ""
                item["last_update"] = ""
                if self.crawler.db.upsert(item):
                    saved += 1
        return saved

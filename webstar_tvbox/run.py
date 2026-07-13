# -*- coding: utf-8 -*-
"""
采集入口脚本
用法示例：
    python run.py --type 1 --pages 3 --detail
    python run.py --search 变形金刚 --pages 2 --detail
    python run.py --fill-detail --limit 50
    python run.py --export webstar_all.json
"""
import argparse
import asyncio
import logging

from crawler import WebstarCrawler
from search import WebstarSearch
from database import VodDatabase
from export import export_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    parser = argparse.ArgumentParser(description="webstar.cn 影视数据采集器")
    parser.add_argument("--type", type=int, default=0, help="分类ID，如 1=电影")
    parser.add_argument("--pages", type=int, default=1, help="最大翻页数，0=不限")
    parser.add_argument("--detail", action="store_true", help="同时采集详情+播放地址")
    parser.add_argument("--search", default="", help="搜索关键词")
    parser.add_argument("--fill-detail", action="store_true", help="补齐已有数据的详情")
    parser.add_argument("--limit", type=int, default=100, help="fill-detail 每次处理条数")
    parser.add_argument("--export", default="", help="导出所有数据到 JSON 文件")
    parser.add_argument("--db", default="webstar.db", help="SQLite 数据库路径")
    args = parser.parse_args()

    db = VodDatabase(args.db)

    if args.export:
        export_all(db, args.export)
        return

    if args.fill_detail:
        async with WebstarCrawler(db=db) as crawler:
            count = await crawler.fill_missing_details(limit=args.limit)
            print(f"补齐详情完成：{count} 条")
        return

    if args.search:
        crawler = WebstarCrawler(db=db)
        searcher = WebstarSearch(crawler=crawler)
        result = await searcher.search(
            args.search,
            max_pages=args.pages,
            fetch_play=args.detail,
            progress_callback=lambda cur, total, saved: print(
                f"搜索进度: {cur}/{total}, 已保存 {saved}"
            ),
        )
        print("搜索完成:", result)
        return

    if args.type:
        async with WebstarCrawler(db=db) as crawler:
            result = await crawler.crawl_list(
                args.type,
                max_pages=args.pages,
                fetch_play=args.detail,
                progress_callback=lambda cur, total, saved: print(
                    f"分类进度: {cur}/{total}, 已保存 {saved}"
                ),
            )
        print("分类采集完成:", result)
        return

    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())

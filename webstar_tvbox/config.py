# -*- coding: utf-8 -*-
"""
webstar.cn (456电影网) 站点配置与 URL 构造器
数据来源：https://www.webstar.cn/
模板：MacCMS v10 / mytheme-reying
"""
from urllib.parse import quote

# 站点根域名
HOST = "https://www.webstar.cn"

# 请求头，模拟桌面 Chrome
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": HOST,
    "Connection": "keep-alive",
}

# 异步并发数与重试配置
CONCURRENCY = 8
RETRY_TIMES = 3
RETRY_DELAY = 1.0
REQUEST_TIMEOUT = 20

# 首页导航提取的分类（id -> 名称）
# 来源：<ul class="myui-header__menu"> 与频道下拉菜单
CATEGORIES = {
    1: "电影",
    2: "电视剧",
    3: "综艺",
    4: "动漫",
    6: "动作电影",
    7: "喜剧电影",
    8: "爱情电影",
    9: "科幻电影",
    10: "恐怖电影",
    11: "剧情电影",
    12: "战争电影",
    13: "国产剧",
    14: "港剧",
    15: "台剧",
    20: "短剧",
    21: "纪录电影",
    35: "动画片",
    37: "Netflix作品",
    45: "香港电影",
    48: "动漫电影",
}

# TVBox 需要返回的分类列表（按常见顺序）
TYPE_LIST = [
    {"type_id": "1", "type_name": "电影"},
    {"type_id": "2", "type_name": "电视剧"},
    {"type_id": "3", "type_name": "综艺"},
    {"type_id": "4", "type_name": "动漫"},
    {"type_id": "20", "type_name": "短剧"},
    {"type_id": "35", "type_name": "动画片"},
]


def join_url(path: str) -> str:
    """拼接绝对 URL"""
    if path.startswith("http"):
        return path
    return HOST.rstrip("/") + ("/" + path.lstrip("/"))


def list_url(type_id: int, page: int = 1) -> str:
    """
    分类列表地址。
    实际规则：/vodshow/{type_id}--------{page}---.html
    示例：/vodshow/1--------2---.html
    """
    return join_url(f"/vodshow/{type_id}--------{page}---.html")


def detail_url(vod_id) -> str:
    """详情页地址，vod_id 为数字字符串或整数"""
    return join_url(f"/voddetail/{vod_id}.html")


def play_url(vod_id, sid: int = 1, nid: int = 1) -> str:
    """播放页地址，sid=线路号，nid=集数号"""
    return join_url(f"/vodplay/{vod_id}-{sid}-{nid}.html")


def search_url(keyword: str, page: int = 1) -> str:
    """
    搜索地址。
    实际规则：/vodsearch/{keyword}----------{page}---.html
    关键词需 URL 编码。
    """
    kw = quote(keyword, safe="")
    return join_url(f"/vodsearch/{kw}----------{page}---.html")


# lxml / css 选择器配置
SELECTORS = {
    # 首页/分类页列表项
    "cat_item": "//li[contains(@class,'myui-vodlist__box')]/a[contains(@class,'myui-vodlist__thumb')]",
    "cat_thumb": "./@data-original",
    "cat_title": "./@title",
    "cat_href": "./@href",
    "cat_remark": "./span[contains(@class,'pic-text')]/text()",

    # 搜索结果列表项
    "search_item": "//ul[@id='searchList']/li",
    "search_thumb": ".//a[contains(@class,'myui-vodlist__thumb')]/@data-original",
    "search_title": ".//a[contains(@class,'myui-vodlist__thumb')]/@title",
    "search_href": ".//a[contains(@class,'myui-vodlist__thumb')]/@href",
    "search_remark": ".//span[contains(@class,'pic-text')]/text()",

    # 详情页
    "detail_title": "//div[contains(@class,'myui-content__detail')]//h1/text() | //div[contains(@class,'myui-content__detail')]//h2/text() | //div[contains(@class,'myui-content__detail')]//h3/text()",
    "detail_poster": "//div[contains(@class,'myui-content__thumb')]//img/@data-original",
    "detail_info_rows": "//div[contains(@class,'myui-content__detail')]//p",
    "detail_content_data": "//div[contains(@class,'text-collapse')]//span[contains(@class,'data')]/text()",
    "detail_content_sketch": "//div[contains(@class,'text-collapse')]//span[contains(@class,'sketch')]/text()",

    # 播放页
    "player_json_re": r'var player_aaaa=(\{.*?\});',
    "playlist_items": "//ul[contains(@id,'playlist')]//a",
    "source_tabs": "//div[@id='player-sidebar']//ul[contains(@class,'nav-tabs')]//a",
}

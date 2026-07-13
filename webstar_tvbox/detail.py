# -*- coding: utf-8 -*-
"""
详情页与播放页解析
说明：
- 详情页字段来自 .myui-content__detail 区域与 meta description。
- 播放地址直接来自页面内 var player_aaaa={...}; 的 JSON，无需额外请求播放器接口。
"""
import re
import json
import html
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from lxml import etree
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


def _extract_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/voddetail/(\d+)\.html", url)
    if m:
        return m.group(1)
    m = re.search(r"/vodplay/(\d+)-", url)
    if m:
        return m.group(1)
    return None


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_list_item(elem: etree._Element, is_search: bool = False) -> Optional[Dict]:
    """
    解析一个列表项，返回最简字段：vod_id, vod_name, vod_pic, vod_remarks。
    支持首页/分类页（a.myui-vodlist__thumb）和搜索结果（li.myui-vodlist__media li）。
    """
    try:
        if is_search:
            a = elem.xpath(".//a[contains(@class,'myui-vodlist__thumb')]")
        else:
            a = [elem] if elem.tag == "a" else elem.xpath("./a[contains(@class,'myui-vodlist__thumb')]")
        if not a:
            return None
        a = a[0]
        href = a.get("href", "")
        vod_id = _extract_id_from_url(href)
        if not vod_id:
            return None
        vod_name = _clean_text(a.get("title", ""))
        vod_pic = a.get("data-original", "")
        if not vod_pic:
            img = a.xpath(".//img/@data-original")
            vod_pic = img[0] if img else ""
        remark = a.xpath(".//span[contains(@class,'pic-text')]/text()")
        vod_remarks = _clean_text(remark[0]) if remark else ""
        return {
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_remarks": vod_remarks,
        }
    except Exception as exc:
        logger.warning("parse_list_item failed: %s", exc)
        return None


def parse_detail(html_text: str, type_name: str = "") -> Dict:
    """
    解析详情页 HTML，返回完整 vod 字段。
    若解析不到标题，会抛出 ValueError。
    """
    tree = etree.HTML(html_text)

    # 1. vod_id：优先从页面中 link rel=canonical 或 URL 模式取
    vod_id = ""
    canonical = tree.xpath("//link[@rel='canonical']/@href")
    if canonical:
        vod_id = _extract_id_from_url(canonical[0]) or ""
    if not vod_id:
        m = re.search(r"/voddetail/(\d+)\.html", html_text)
        if m:
            vod_id = m.group(1)

    # 2. 标题：尝试 h1/h2/h3，兜底 title 标签
    title = ""
    for expr in config.SELECTORS["detail_title"].split(" | "):
        nodes = tree.xpath(expr)
        if nodes:
            title = _clean_text(str(nodes[0]))
            if title:
                break
    if not title:
        m = re.search(r"<title>(.*?)</title>", html_text, re.S | re.I)
        if m:
            title = _clean_text(m.group(1).split("_")[1] if "_" in m.group(1) else m.group(1))

    # 3. 海报
    poster_nodes = tree.xpath(config.SELECTORS["detail_poster"])
    vod_pic = _clean_text(poster_nodes[0]) if poster_nodes else ""

    # 4. 信息行：分类/地区/年份/主演/导演/更新/简介
    info = _parse_info_rows(tree, html_text)

    # 5. 内容/简介：优先取隐藏的完整 data，再取 sketch，最后 meta description
    content = ""
    data_nodes = tree.xpath(config.SELECTORS["detail_content_data"])
    if data_nodes:
        content = _clean_text(data_nodes[0])
    if not content:
        sketch_nodes = tree.xpath(config.SELECTORS["detail_content_sketch"])
        if sketch_nodes:
            content = _clean_text(sketch_nodes[0])
    if not content:
        m = re.search(r'name="description" content="(.*?)"', html_text, re.S | re.I)
        if m:
            content = _clean_text(m.group(1))
            if "剧情介绍:" in content:
                content = content.split("剧情介绍:", 1)[1]

    # 6. last_update：从“更新：”字段或当前时间
    last_update = info.get("更新", "")
    if not last_update and vod_id:
        # 兜底：当前采集时间
        from datetime import datetime
        last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "vod_id": vod_id,
        "vod_name": title,
        "vod_pic": vod_pic,
        "vod_remarks": info.get("状态", ""),
        "vod_year": info.get("年份", ""),
        "vod_area": info.get("地区", ""),
        "vod_lang": info.get("语言", ""),
        "vod_actor": info.get("主演", ""),
        "vod_director": info.get("导演", ""),
        "vod_content": content,
        "type_name": type_name or info.get("分类", ""),
        "last_update": last_update,
    }


def _parse_info_rows(tree: etree._Element, raw_html: str) -> Dict[str, str]:
    """
    解析详情页信息行。
    站点信息行格式：<p><span class="text-muted">分类：</span>恐怖电影 ...</p>
    也兼容纯文本模式（去掉 HTML 标签后按冒号匹配）。
    """
    result = {}
    # 方案 A：按 p 标签解析
    rows = tree.xpath(config.SELECTORS["detail_info_rows"])
    for row in rows:
        text = _clean_text("".join(row.itertext()))
        if "：" in text:
            label, value = text.split("：", 1)
            label = label.strip()
            value = value.strip()
            if label in ("分类", "地区", "年份", "语言", "主演", "导演", "更新", "状态", "简介"):
                result[label] = value

    # 方案 B：若方案 A 没拿到年份/地区，用正则兜底（兼容页面文本被压缩到同一行）
    if not result:
        plain = re.sub(r"<[^>]+>", " ", raw_html)
        plain = _clean_text(plain)
        patterns = {
            "分类": r"分类[：:]\s*([^\s]+?)(?=\s+地区|$)",
            "地区": r"地区[：:]\s*([^\s]+?)(?=\s+年份|$)",
            "年份": r"年份[：:]\s*(\d{4})",
            "主演": r"主演[：:]\s*(.*?)(?=\s+导演|$)",
            "导演": r"导演[：:]\s*(.*?)(?=\s+简介|$)",
            "更新": r"更新[：:]\s*([^\s]+)",
            "状态": r"状态[：:]\s*([^\s]+)",
        }
        for label, pat in patterns.items():
            if label not in result:
                m = re.search(pat, plain)
                if m:
                    result[label] = _clean_text(m.group(1))

    return result


def parse_play(html_text: str) -> Tuple[List[str], List[List[Dict]]]:
    """
    解析播放页：
    - 返回 (play_from_list, episodes_list)
    - play_from_list: 线路名称列表，如 ["云播资源"]
    - episodes_list: 每个线路下的集数列表，元素为 {"name": "HD", "url": "m3u8地址"}
    说明：
    - 单线路时，player_aaaa 直接给出当前集 m3u8；
    - 多线路/多集时，需要从 #playlist 提取集数链接，再逐个访问播放页获取真实地址。
    本函数先返回当前页可解析的线路与集数；多集情况由调用方继续展开。
    """
    tree = etree.HTML(html_text)

    # 1. 播放器 JSON
    player_match = re.search(config.SELECTORS["player_json_re"], html_text, re.S)
    player_data = json.loads(player_match.group(1)) if player_match else {}

    # 2. 线路名称
    source_names = []
    tabs = tree.xpath(config.SELECTORS["source_tabs"])
    for tab in tabs:
        name = _clean_text("".join(tab.itertext()))
        if name:
            source_names.append(name)
    # 兜底：用 player_aaaa.from 或固定名称
    if not source_names and player_data.get("from"):
        source_names.append(player_data.get("from"))
    if not source_names:
        source_names.append("云播资源")

    # 3. 当前线路的 playlist
    episodes = []
    playlist = tree.xpath(config.SELECTORS["playlist_items"])
    for item in playlist:
        href = item.get("href", "")
        name = _clean_text(item.text or "")
        # 当前播放项可能 href 为空或自己，真实地址来自 player_aaaa.url
        if not href and player_data.get("url"):
            href = player_data.get("url", "")
        episodes.append({"name": name, "url": href})

    # 若 playlist 为空但 player_aaaa 有 url，说明单集
    if not episodes and player_data.get("url"):
        episodes.append({
            "name": player_data.get("nid", "HD"),
            "url": player_data.get("url", ""),
        })

    return source_names, [episodes]


def build_play_strings(
    source_names: List[str],
    episodes_list: List[List[Dict]],
) -> Tuple[str, str]:
    """
    将线路与集数转换成 TVBox 标准格式：
    - vod_play_from: "线路1$$$线路2"
    - vod_play_url: "第1集$http...#第2集$http...$$$第1集$http..."
    """
    from_str = "$$$".join(source_names)
    url_parts = []
    for episodes in episodes_list:
        parts = [f"{ep.get('name', '未知')}${ep.get('url', '')}" for ep in episodes if ep.get("url")]
        url_parts.append("#".join(parts))
    url_str = "$$$".join(url_parts)
    return from_str, url_str


def merge_detail_play(detail: Dict, source_names: List[str], episodes_list: List[List[Dict]]) -> Dict:
    """把详情页字段与播放字段合并"""
    detail = dict(detail)
    detail["vod_play_from"], detail["vod_play_url"] = build_play_strings(source_names, episodes_list)
    return detail

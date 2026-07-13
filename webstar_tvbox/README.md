# webstar.cn 影视数据采集与 TVBox 数据源

目标站点：`https://www.webstar.cn/`（页面展示名：456电影网）  
模板：MacCMS v10 / mytheme-reying

## 一、项目结构

```
webstar_tvbox/
├── config.py          # 站点配置、URL 构造器、选择器
├── crawler.py         # 异步分类采集器（翻页、并发、重试、去重）
├── detail.py          # 详情页与播放页解析
├── search.py          # 搜索采集
├── database.py        # SQLite 存储与增量更新
├── export.py          # JSON 导出
├── tvbox.py           # TVBox/影视仓/OK影视/猫影视 数据接口
├── run.py             # 命令行采集入口
├── requirements.txt   # 依赖
└── README.md          # 说明
```

## 二、站点规则摘要

| 项目 | 规则 | 示例 |
|---|---|---|
| 首页分类 | `/vodtype/{id}.html` | `/vodtype/1.html` |
| 分类列表 | `/vodshow/{type_id}--------{page}---.html` | `/vodshow/1--------2---.html` |
| 详情页 | `/voddetail/{vod_id}.html` | `/voddetail/100631.html` |
| 播放页 | `/vodplay/{vod_id}-{sid}-{nid}.html` | `/vodplay/100631-1-1.html` |
| 搜索 | `/vodsearch/{keyword}----------{page}---.html` | `/vodsearch/%E5%8F%98%E5%BD%A2%E9%87%91%E5%88%9A----------1---.html` |
| 真实视频地址 | 播放页 `var player_aaaa={...};` 中 `url` 字段 | `https://v11.ppqrrs.com/.../index.m3u8` |

### 主要分类 ID

```
1 电影 | 2 电视剧 | 3 综艺 | 4 动漫
6 动作电影 | 7 喜剧电影 | 8 爱情电影 | 9 科幻电影 | 10 恐怖电影
11 剧情电影 | 12 战争电影 | 13 国产剧 | 14 港剧 | 15 台剧
20 短剧 | 21 纪录电影 | 35 动画片 | 37 Netflix作品 | 45 香港电影 | 48 动漫电影
```

## 三、安装依赖

```bash
pip install -r requirements.txt
```

## 四、采集用法

```bash
# 1. 仅采集电影分类前 3 页列表（不抓详情）
python run.py --type 1 --pages 3

# 2. 采集电影分类前 3 页，并抓取详情+播放地址
python run.py --type 1 --pages 3 --detail

# 3. 搜索“变形金刚”，抓 2 页并补全详情
python run.py --search 变形金刚 --pages 2 --detail

# 4. 对数据库中缺少详情/播放地址的记录做增量补齐
python run.py --fill-detail --limit 50

# 5. 导出全部数据到 JSON
python run.py --export webstar_all.json
```

## 五、TVBox 接口服务

```bash
python tvbox.py --port 8080
```

接口地址：

- 分类：`http://127.0.0.1:8080/api.php?ac=list`
- 列表：`http://127.0.0.1:8080/api.php?ac=videolist&t=1&pg=1`
- 详情：`http://127.0.0.1:8080/api.php?ac=detail&ids=100631`
- 搜索：`http://127.0.0.1:8080/search?wd=变形金刚&pg=1`

TVBox 数据源配置示例：

```json
{
  "name": "456电影-webstar",
  "api": "http://你的IP:8080/api.php",
  "type": 1,
  "searchable": 1,
  "quickSearch": 1,
  "filterable": 1
}
```

## 六、数据字段映射

| 输出字段 | 数据来源 |
|---|---|
| vod_id | 详情页 URL `/voddetail/{id}.html` 或 canonical |
| vod_name | `.myui-content__detail h1/h2/h3`，兜底 `<title>` |
| vod_pic | `.myui-content__thumb img@data-original` |
| vod_remarks | 信息行“状态：”或列表页 `.pic-text` |
| vod_year | 信息行“年份：” |
| vod_area | 信息行“地区：” |
| vod_lang | 信息行“语言：” |
| vod_actor | 信息行“主演：” |
| vod_director | 信息行“导演：” |
| vod_content | `.text-collapse .data` → `.sketch` → `meta description` |
| vod_play_from | 播放页线路名称，多个用 `$$$` 分隔 |
| vod_play_url | 播放页 `player_aaaa.url`，多集用 `#`、多线路用 `$$$` 分隔 |
| type_name | 配置分类名或详情页“分类：” |
| last_update | 信息行“更新：” |

## 七、注意事项

1. 本方案仅采集站点公开页面数据，播放器 JSON 中的 `url` 即为真实 m3u8 地址。  
2. 默认并发 8、重试 3 次，可在 `config.py` 调整。  
3. 数据库使用 `vod_id` 主键去重，内容变化时自动更新。  
4. 如站点模板变更，优先检查 `config.SELECTORS` 与 `detail.py` 中的正则。

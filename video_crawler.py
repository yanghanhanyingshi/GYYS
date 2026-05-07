import requests
import os
import time
import random
import sys
from threading import Thread, Lock
from urllib.parse import urlparse
from datetime import datetime

SAVE_DIR = "videos"
os.makedirs(SAVE_DIR, exist_ok=True)

VIDEO_APIS = [
    ("高质量", "http://api.tinise.cn/api/xjjsp"),
    ("小姐姐(高质量)", "http://api.yujn.cn/api/zzxjj.php?type=video"),
    ("小姐姐2(高质量)", "https://api.dwo.cc/api/ksvideo"),
    ("小姐姐3(高质量)", "http://api.qemao.com/api/douyin/"),
    ("随机小姐姐聚合", "https://sucyan.top/api/video/?msg=jk"),
    ("狱卒系列", "http://api.yujn.cn/api/jpmt.php"),
    ("美腿玉足", "https://sbtxqq.com/api/yzxl.php"),
    ("黑丝系列", "http://api.yujn.cn/api/heisis.php?type=video"),
    ("黑白丝", "http://api.tinise.cn/api/baisi"),
    ("黑白丝2", "http://api.tinise.cn/api/heisi"),
    ("抖音小姐姐", "http://api.qemao.com/api/douyin/"),
    ("高质量美女", "http://www.wudada.online/Api/NewSp"),
    ("完美身材", "http://api.yujn.cn/api/wmsc.php?type=video"),
    ("快手变装", "http://api.yujn.cn/api/ksbianzhuang.php?type=video"),
    ("抖音变装", "http://api.yujn.cn/api/bianzhuang.php?"),
    ("白丝系列", "http://api.yujn.cn/api/baisis.php?type=video"),
    ("快手女大学生", "https://api.yujn.cn/api/nvda.php?type=video"),
    ("抖音瞳瞳", "https://api.yujn.cn/api/tongtong.php?type=video"),
    ("丝滑舞蹈", "http://api.yujn.cn/api/shwd.php?type=video"),
    ("鞠婧祎系列", "http://api.yujn.cn/api/jjy.php?type=video"),
    ("美女穿搭", "http://api.yujn.cn/api/chuanda.php?type=video"),
    ("章若楠", "http://api.yujn.cn/api/zrn.php?type=video"),
    ("古风类", "http://api.yujn.cn/api/hanfu.php?type=video"),
    ("慢摇系列", "http://api.yujn.cn/api/manyao.php?type=video"),
    ("吊带系列", "http://api.yujn.cn/api/diaodai.php?type=video"),
    ("清纯系列", "http://api.yujn.cn/api/qingchun.php?type=video"),
    ("COS系列", "http://api.yujn.cn/api/COS.php?type=video"),
    ("纯情女高", "http://api.yujn.cn/api/nvgao.php?type=video"),
    ("街拍系列", "http://api.yujn.cn/api/jiepai.php?type=video"),
    ("变装系列", "http://api.yujn.cn/api/ksbianzhuang.php?type=video"),
    ("萝莉系列", "http://api.yujn.cn/api/luoli.php?type=video"),
    ("甜妹系列", "http://api.yujn.cn/api/tianmei.php?type=video"),
    ("随机美女", "https://v2.api-m.com/api/meinv?return=302"),
    ("随机小姐姐1", "http://api.yujn.cn/api/xjj.php?type=video"),
    ("随机小姐姐2", "http://api.yujn.cn/api/ksxjjsp.php?"),
    ("随机小姐姐3", "https://img.8845.top/xjj"),
    ("随机小姐姐4", "https://api.mhimg.cn/api/Sj_girls_video"),
    ("随机小姐姐5", "http://api.yujn.cn/api/juhexjj.php?type=video"),
]

count_lock = Lock()
total_ok = 0
total_fail = 0
log_lock = Lock()
last_run_file = "last_run.txt"

def log_message(msg):
    """记录带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_lock:
        print(f"[{timestamp}] {msg}")
        with open("crawler.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")

def get_random_user_agent():
    """随机获取User-Agent"""
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/537.36",
        "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36"
    ]
    return random.choice(ua_list)

def download_one(name, url, dest_dir, retries=3):
    global total_ok, total_fail
    safe = "".join(c for c in name if c.isalnum() or c in " _-").strip()
    d = os.path.join(dest_dir, safe)
    os.makedirs(d, exist_ok=True)
    
    for r in range(retries):
        try:
            hd = {
                "User-Agent": get_random_user_agent(),
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": "https://github.com/"
            }
            resp = requests.get(url, headers=hd, timeout=30, stream=True, allow_redirects=True)
            if resp.status_code != 200:
                log_message(f"  [{safe}] HTTP {resp.status_code}, retry {r+1}")
                time.sleep(2)
                continue
            
            ts = int(time.time() * 1000)
            fp = os.path.join(d, f"{ts}.mp4")
            
            with open(fp, "wb") as f:
                for chunk in resp.iter_content(65536):
                    if chunk:
                        f.write(chunk)
            
            kb = os.path.getsize(fp) / 1024
            if kb < 100:
                os.remove(fp)
                log_message(f"  [{safe}] 文件太小({kb:.0f}KB), retry {r+1}")
                continue
            
            with count_lock:
                total_ok += 1
            
            log_message(f"  ✓ [{safe}] {os.path.basename(fp)} ({kb:.0f}KB)")
            return True
            
        except Exception as e:
            log_message(f"  ✗ [{safe}] {str(e)[:100]}")
            time.sleep(2)
    
    with count_lock:
        total_fail += 1
    return False

def worker(name, url, dest, n, target_count):
    for i in range(n):
        if total_ok >= target_count:
            break
        download_one(name, url, dest)

def save_report():
    """保存运行报告"""
    report_file = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"爬虫运行报告\n")
        f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"成功: {total_ok}\n")
        f.write(f"失败: {total_fail}\n")
        f.write(f"成功率: {total_ok/(total_ok+total_fail)*100:.1f}%\n" if total_ok+total_fail>0 else "无数据\n")
    return report_file

def cleanup_old_videos(days=30):
    """清理超过指定天数的旧视频"""
    now = time.time()
    deleted = 0
    for root, dirs, files in os.walk(SAVE_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            if os.path.getmtime(filepath) < now - days * 86400:
                try:
                    os.remove(filepath)
                    deleted += 1
                except:
                    pass
    if deleted > 0:
        log_message(f"清理了 {deleted} 个超过 {days} 天的旧视频")

def main():
    global total_ok, total_fail
    
    # 读取上次运行记录
    last_run = ""
    if os.path.exists(last_run_file):
        with open(last_run_file, "r") as f:
            last_run = f.read().strip()
    
    log_message("=" * 60)
    log_message("  妹子发电站 · 38源批量视频爬虫 (GitHub Actions版)")
    log_message(f"  保存路径: {SAVE_DIR}")
    if last_run:
        log_message(f"  上次运行: {last_run}")
    log_message("=" * 60)
    
    # 从环境变量获取配置,如果没有则使用默认值
    videos_per_source = int(os.getenv("VIDEOS_PER_SOURCE", "2"))
    concurrency = int(os.getenv("CONCURRENCY", "2"))
    max_videos = int(os.getenv("MAX_VIDEOS", "50"))
    
    log_message(f"配置: 每源{videos_per_source}个, 并发{concurrency}, 最多{max_videos}个")
    
    start = time.time()
    
    for i in range(0, len(VIDEO_APIS), concurrency):
        if total_ok >= max_videos:
            log_message(f"已达到最大视频数 {max_videos}, 停止爬取")
            break
            
        batch = VIDEO_APIS[i:i+concurrency]
        threads = []
        for name, url in batch:
            if total_ok >= max_videos:
                break
            t = Thread(target=worker, args=(name, url, SAVE_DIR, videos_per_source, max_videos))
            t.start()
            threads.append(t)
            time.sleep(0.5)  # 稍微延迟避免请求过快
        
        for t in threads:
            t.join()
    
    elapsed = time.time() - start
    
    # 生成报告
    report_file = save_report()
    cleanup_old_videos(30)  # 清理30天前的视频
    
    log_message("=" * 60)
    log_message(f"完成! 成功={total_ok}, 失败={total_fail}, 耗时={elapsed:.0f}s")
    log_message(f"报告已保存: {report_file}")
    log_message(f"视频保存在: {SAVE_DIR}")
    log_message("=" * 60)
    
    # 保存本次运行时间
    with open(last_run_file, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 返回状态码，失败太多则返回非0
    if total_ok == 0:
        sys.exit(1)
    return 0

if __name__ == "__main__":
    main()

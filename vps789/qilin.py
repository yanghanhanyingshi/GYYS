from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        # 无头模式 + 禁用图片/视频加载，大幅提速防超时
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-images",
                "--disable-media"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()

        try:
            print("正在打开：api.uouin.com/cloudflare.html")
            
            # 访问页面（更长超时 + 更强等待）
            page.goto(
                "https://api.uouin.com/cloudflare.html",
                wait_until="load",
                timeout=60000
            )
            time.sleep(5)  # 强制等待页面完全渲染

            print("开始提取优选IP数据...")
            ip_data = []
            
            # 通用匹配，不依赖固定ID，彻底解决找不到元素问题
            rows = page.query_selector_all("table tbody tr")
            
            for row in rows:
                tds = row.query_selector_all("td")
                if len(tds) < 4:
                    continue

                ip = tds[0].inner_text().strip()
                ping_text = tds[3].inner_text().strip()

                # 过滤无效IP
                if not ip or "." not in ip:
                    continue

                # 提取延迟数值
                try:
                    ping = int(''.join(filter(str.isdigit, ping_text)))
                except:
                    continue

                # 延迟 ≤ 300ms 才保留（可自行修改）
                if ping <= 300:
                    ip_data.append((ip, ping))

            # 去重 + 按延迟从小到大排序
            ip_dict = {}
            for ip, ping in ip_data:
                if ip not in ip_dict:
                    ip_dict[ip] = ping

            sorted_ips = sorted(ip_dict.keys(), key=lambda x: ip_dict[x])

            # 保存文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_path = os.path.join(current_dir, "qilin_ip.txt")

            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(sorted_ips))

            print(f"✅ 抓取完成！去重+测速后优质IP数量：{len(sorted_ips)}")

        except Exception as e:
            print(f"❌ 抓取失败：{str(e)}")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    run()

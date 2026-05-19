from playwright.sync_api import sync_playwright
import time
import os

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-images",
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        try:
            print("正在打开：api.uouin.com/cloudflare.html")

            page.goto(
                "https://api.uouin.com/cloudflare.html",
                wait_until="load",
                timeout=60000
            )

            print("等待IP数据加载...")
            time.sleep(10)  # 足够加载动态数据

            ip_data = []
            
            # 正确、稳定、无错误的CSS选择器
            rows = page.query_selector_all("#ipTable tbody tr")
            
            # 备用方案：如果上面没找到，用这个
            if len(rows) == 0:
                rows = page.query_selector_all("table tbody tr")

            print(f"找到 {len(rows)} 行数据")

            for row in rows:
                tds = row.query_selector_all("td")
                if len(tds) < 4:
                    continue

                ip = tds[0].inner_text().strip()
                ping_str = tds[3].inner_text().strip()

                if not ip or "." not in ip:
                    continue

                # 提取延迟数字
                try:
                    ping = int(''.join(filter(str.isdigit, ping_str)))
                except:
                    ping = 9999

                # 只保留延迟 ≤ 300ms 的优质IP
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

            print(f"✅ 抓取完成！有效优质IP：{len(sorted_ips)} 个")

        except Exception as e:
            print(f"❌ 错误：{str(e)}")
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    run()

from playwright.sync_api import sync_playwright
import re
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
                "--disable-web-security",  # 可选，减少一些限制
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            print("正在打开：https://api.uouin.com/cloudflare.html")
            page.goto("https://api.uouin.com/cloudflare.html", timeout=60000)
            
            # 更可靠的等待方式
            print("等待页面加载...")
            # 1. 等待加载提示消失
            page.wait_for_selector("text=正在加载", state="hidden", timeout=30000)
            
            # 2. 或者等待表格出现且有内容
            page.wait_for_selector("table", timeout=30000)
            
            # 额外保险等待
            time.sleep(5)
            
            # 获取完整 body 文本
            page_text = page.inner_text("body")
            
            # 提取所有 IPv4
            ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
            all_ips = ip_pattern.findall(page_text)
            
            # 过滤合法 IP 并去重
            valid_ips = []
            for ip in all_ips:
                parts = ip.split(".")
                if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts):
                    valid_ips.append(ip)
            
            unique_ips = sorted(list(set(valid_ips)))
            
            # 保存文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            save_path = os.path.join(current_dir, "qilin_ip.txt")
            
            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(unique_ips))
            
            print(f"✅ 抓取完成！共获取 {len(unique_ips)} 个优选IP")
            print(f"文件保存至：{save_path}")
            
        except Exception as e:
            print(f"❌ 错误：{str(e)}")
            # 调试用：保存页面截图和源码
            try:
                page.screenshot(path="error_debug.png")
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print("已保存 error_debug.png 和 error_page.html 用于调试")
            except:
                pass
            raise
        finally:
            browser.close()

if __name__ == "__main__":
    run()

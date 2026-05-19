import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://vps789.com/cfip/"

def get_best_cf_domain():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 Windows Chrome")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(URL)
        # 等待页面加载完成
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        html = driver.page_source

        # 精准匹配页面内所有优选域名
        pattern = r"[a-zA-Z0-9_-]+\.(?:cdn-b100\.xn--b6gac\.eu\.org|cdn-all\.xn--b6gac\.eu\.org|cloudflare\.com|workers\.dev|pages\.dev)"
        raw_domains = re.findall(pattern, html)

        # 去重 + 过滤
        domain_list = sorted(list(set(raw_domains)))
        valid_domains = [d for d in domain_list if len(d) > 10]

        # 写入txt
        with open("cf_domains.txt", "w", encoding="utf-8") as f:
            f.write("# CF高速优选域名 优化版\n")
            f.write(f"# 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# 来源：vps789.com/cfip 精选可用域名\n")
            f.write("# 适配：节点优选、测速、反代、Worker加速\n\n")
            for dom in valid_domains:
                f.write(dom + "\n")

        print(f"✅ 成功抓取 {len(valid_domains)} 个优选域名")

    except Exception as e:
        print(f"❌ 抓取失败：{e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    get_best_cf_domain()

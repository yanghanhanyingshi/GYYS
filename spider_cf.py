import requests
import re
from datetime import datetime

URL = "https://vps789.com/cfip/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def get_best_cf_domain():
    try:
        res = requests.get(URL, headers={"User-Agent":UA}, timeout=15)
        res.encoding = "utf-8"
        html = res.text

        # 精准匹配页面内CF优选域名格式
        rule = r'[0-9a-zA-Z\-]+\.(?:eu\.org|cloudflare\.com|workers\.dev|pages\.dev|cf\.com|jsdelivr\.net)'
        raw_list = re.findall(rule, html)

        # 严格去重+排序
        domain_set = sorted(list(set(raw_list)))

        # 二次过滤无效短域名
        final_list = [d for d in domain_set if len(d) >= 12]

        # 写入TXT
        with open("cf_domains.txt", "w", encoding="utf-8") as f:
            f.write("# CF高速优选域名 优化版\n")
            f.write(f"# 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# 来源：vps789.com/cfip 精选可用域名\n")
            f.write("# 适配：节点优选、测速、反代、Worker加速\n\n")
            for dom in final_list:
                f.write(dom + "\n")

        print(f"抓取成功！精选可用域名：{len(final_list)} 个")
    except Exception as e:
        print("抓取失败：",e)

if __name__ == "__main__":
    get_best_cf_domain()

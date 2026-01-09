import requests
from cloudscraper import create_scraper
from collections import OrderedDict

scraper = create_scraper()

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "referer": "https://auth.openai.com/log-in/password",
    "sec-ch-ua": "\"Chromium\";v=\"110\", \"Not A(Brand\";v=\"24\", \"Google Chrome\";v=\"110\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def parse_cookie_str(cookie_str: str) -> dict:
    """
    把 'a=1; b=2' 解析成 {'a': '1', 'b': '2'}。
    忽略空段/没有=的段。
    """
    jar = {}
    if not cookie_str:
        return jar
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        jar[k.strip()] = v.strip()
    return jar

def merge_cookie_str(*cookie_strs: str) -> str:
    """
    合并多段 cookie_str，后面的覆盖前面的同名 key。
    返回 'k=v; k2=v2' 格式
    """
    jar = OrderedDict()
    for s in cookie_strs:
        for k, v in parse_cookie_str(s).items():
            jar[k] = v  # 覆盖更新
    return "; ".join([f"{k}={v}" for k, v in jar.items()])

def redirect(url, cookies, proxies=None):
    full_url = url
    full_cookies = cookies
    for i in range(6):
        headers["cookie"] = full_cookies
        resp = scraper.get(full_url, headers=headers,allow_redirects=False, proxies=proxies)
        # 1) 抓原始 Set-Cookie（最完整）
        cookies = "; ".join([f"{k}={v}" for k, v in resp.cookies.items()])
        print(f'[{i}] {cookies}')
        full_cookies = merge_cookie_str(full_cookies, cookies)

        print(f"[{i}] {resp.status_code} {full_url}")

        # 2) 如果不是重定向，结束
        if resp.status_code not in (301, 302, 303, 307, 308):
            break

        # 3) 获取 Location
        location = resp.headers.get("Location")
        if not location:
            print("❌ 没有 Location，无法继续跳转")
            break

        if 'https://chatgpt.com/api/auth/callback/openai?code' in location:
            headers["referer"] = 'https://auth.openai.com/'

        # 4) 拼出下一跳绝对 URL
        full_url = location

    return full_cookies
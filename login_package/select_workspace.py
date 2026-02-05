import requests
import json


headers = {
    "accept": "application/json",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": "https://auth.openai.com",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://auth.openai.com/workspace",
    "sec-ch-ua": "\"Chromium\";v=\"110\", \"Not A(Brand\";v=\"24\", \"Google Chrome\";v=\"110\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "traceparent": "00-000000000000000091c6aff832c6b959-4fa94ed81c57ff73-01",
    "tracestate": "dd=s:1;o:rum",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "x-datadog-origin": "rum",
    "x-datadog-parent-id": "5740205890155839347",
    "x-datadog-sampling-priority": "1",
    "x-datadog-trace-id": "10504276661426895193",
    "cookie":""
}
url = "https://auth.openai.com/api/accounts/workspace/select"

def select_workspace(cookies, workspace_id, proxies=None):

    data = {
        "workspace_id": workspace_id
    }
    headers["cookie"] = cookies

    response = requests.post(url, headers=headers, json=data, proxies=proxies)

    cookie_str = "; ".join([f"{k}={v}" for k, v in response.cookies.items()])
    return cookie_str, response.json()

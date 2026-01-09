import requests

cookies = {
    '__cf_bm': '5lCLPp7oGWm4OhJBTeSz2AEZt8ODZUiINON7RAVpmeU-1767084617-1.0.1.1-kQEhn453pVje.72u696kwfFCC4JkcN4K17XhiryILfYf9x.C6MV7SMFRw2uPi_DiC2yXlP.KMYUCVVXH297iV3DbFZDzKpozU.yTWKe1Qrs',
    '__Host-next-auth.csrf-token': '587e05577148b5441c206db90c3142746a179c6b13efe81bbb6fa44991f61568%7Ca95993519612816285dafedd5a140efa941f2e5569a0d33c64c17698eb0a32fd',
    'oai-did': '1a53f94a-26bb-4983-a7e6-c62aad26539d',
    '__cflb': '0H28vzvP5FJafnkHxisjP7gwPFCytXteGkumZV8Ee59',
    '_cfuvid': 'nD6_KriJ4SdATQiCLzNrQ720Qfuny5DLrkMrIJpkzgo-1767084617854-0.0.1.1-604800000',
    '_dd_s': 'aid=320c7dbf-80cd-4735-899c-344ec80abb7a&rum=0&expire=1767085519754&logs=1&id=13cfb9b4-ed6a-4532-a9a6-4e7c0b1b73f0&created=1767084619754',
    'cf_clearance': 'j3ESp3x_irtJe0Ic0nyiozeJEz5U8DYOFWMb1vr.J68-1767084620-1.2.1.1-kYod4oJU4kXiuqzvDiTieAsvO5D87ar_i2XnXs.ykMVjJFuxH64IgluyuaTUIIs6E_FulKu4gGkjmW3i8PJzDNtx.MCAczSg_AqDLb9zGfJDrt8ZATJmxF3AJ7OP9rG69.whG81gDaZg.T9SFx.soG7KG.sGURFovgMi_jOwBHoDWbOwPd.mqepna_31iV_QXeFnbNfTLThvNP5MQ128yfAxAtn7.0CdbtwN8WKPJZo',
    'oai-hm': 'READY_WHEN_YOU_ARE%20%7C%20SHOULD_WE_BEGIN',
    'g_state': '{"i_l":0,"i_ll":1767084620324,"i_b":"GTDWVZidWPq7ep2bL/P0W+8oiT3XkNzzbx2CMaxLh6c","i_e":{"enable_itp_optimization":0}}',
    'oai-sc': '0gAAAAABpU5JNs0Ul3LzW_hdnnhgdiioh-cKKYUhDUuy--L7yiJ4onbPV0g82AsRCdSU2lLFi4w4wD89l5OckbwhEWAood8r3agpsNNKlcSkgJMgDEGAsGDqsZxr7L6VxtxTP2vYc5_PqVWw1ikFjlPy_w5Cf2KGZU5B6hGETY6EyuMZMYtrW2K5cN_U5dDhdEBtqEddPaqUhrgdI5s9_wOFzre8sux_yijsycL8MflM6kjvtubFx6DQ',
    'oai-asli': 'fb8f14ed-68ea-4906-9a33-6043aef9eb2a',
    '__Secure-next-auth.callback-url': 'https%3A%2F%2Fchatgpt.com%2F',
}

headers = {
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'cache-control': 'no-cache',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://chatgpt.com',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://chatgpt.com/',
    'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-full-version': '"110.0.5481.177"',
    'sec-ch-ua-full-version-list': '"Chromium";v="110.0.5481.177", "Not A(Brand";v="24.0.0.0", "Google Chrome";v="110.0.5481.177"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"macOS"',
    'sec-ch-ua-platform-version': '"10.15.7"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    # 'cookie': '__cf_bm=5lCLPp7oGWm4OhJBTeSz2AEZt8ODZUiINON7RAVpmeU-1767084617-1.0.1.1-kQEhn453pVje.72u696kwfFCC4JkcN4K17XhiryILfYf9x.C6MV7SMFRw2uPi_DiC2yXlP.KMYUCVVXH297iV3DbFZDzKpozU.yTWKe1Qrs; __Host-next-auth.csrf-token=587e05577148b5441c206db90c3142746a179c6b13efe81bbb6fa44991f61568%7Ca95993519612816285dafedd5a140efa941f2e5569a0d33c64c17698eb0a32fd; oai-did=1a53f94a-26bb-4983-a7e6-c62aad26539d; __cflb=0H28vzvP5FJafnkHxisjP7gwPFCytXteGkumZV8Ee59; _cfuvid=nD6_KriJ4SdATQiCLzNrQ720Qfuny5DLrkMrIJpkzgo-1767084617854-0.0.1.1-604800000; _dd_s=aid=320c7dbf-80cd-4735-899c-344ec80abb7a&rum=0&expire=1767085519754&logs=1&id=13cfb9b4-ed6a-4532-a9a6-4e7c0b1b73f0&created=1767084619754; cf_clearance=j3ESp3x_irtJe0Ic0nyiozeJEz5U8DYOFWMb1vr.J68-1767084620-1.2.1.1-kYod4oJU4kXiuqzvDiTieAsvO5D87ar_i2XnXs.ykMVjJFuxH64IgluyuaTUIIs6E_FulKu4gGkjmW3i8PJzDNtx.MCAczSg_AqDLb9zGfJDrt8ZATJmxF3AJ7OP9rG69.whG81gDaZg.T9SFx.soG7KG.sGURFovgMi_jOwBHoDWbOwPd.mqepna_31iV_QXeFnbNfTLThvNP5MQ128yfAxAtn7.0CdbtwN8WKPJZo; oai-hm=READY_WHEN_YOU_ARE%20%7C%20SHOULD_WE_BEGIN; g_state={"i_l":0,"i_ll":1767084620324,"i_b":"GTDWVZidWPq7ep2bL/P0W+8oiT3XkNzzbx2CMaxLh6c","i_e":{"enable_itp_optimization":0}}; oai-sc=0gAAAAABpU5JNs0Ul3LzW_hdnnhgdiioh-cKKYUhDUuy--L7yiJ4onbPV0g82AsRCdSU2lLFi4w4wD89l5OckbwhEWAood8r3agpsNNKlcSkgJMgDEGAsGDqsZxr7L6VxtxTP2vYc5_PqVWw1ikFjlPy_w5Cf2KGZU5B6hGETY6EyuMZMYtrW2K5cN_U5dDhdEBtqEddPaqUhrgdI5s9_wOFzre8sux_yijsycL8MflM6kjvtubFx6DQ; oai-asli=fb8f14ed-68ea-4906-9a33-6043aef9eb2a; __Secure-next-auth.callback-url=https%3A%2F%2Fchatgpt.com%2F',
}

params = {
    'prompt': 'login',
    'screen_hint': 'login_or_signup',
    'ext-oai-did': 'a9c9e9a0-f72d-4fbc-800e-2d0e1e3c3b54',
    'auth_session_logging_id': 'fb8f14ed-68ea-4906-9a33-6043aef9eb2a',
}

data = {
    'callbackUrl': 'https://chatgpt.com/',
    'csrfToken': '587e05577148b5441c206db90c3142746a179c6b13efe81bbb6fa44991f61568',
    'json': 'true',
}


def openai(proxies=None):
    response = requests.post('https://chatgpt.com/api/auth/signin/openai', params=params, cookies=cookies, headers=headers, data=data, proxies=proxies)

    print(response.text)
    print(response.status_code)
    cookie_str = "; ".join([f"{k}={v}" for k, v in response.cookies.items()])

    print(cookie_str)
    return cookie_str, response.json()

if __name__ == '__main__':
    cookies, json_data = openai()
    print(json_data)
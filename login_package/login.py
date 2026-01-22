from . import authorize
from . import auth_continue
from . import login_verify
from . import session
from . import red
from . import openai
import time
import json
from collections import OrderedDict

# 配置你的邮箱和密码
email = ''
password = ''

def parse_proxy_str(proxy_str: str) -> dict:
    """
    解析代理字符串 "socks5,1.1.1.1,8888,user,pass" 为 requests proxies 格式
    """
    if not proxy_str:
        return None
    try:
        parts = proxy_str.split(',')
        if len(parts) != 5:
            print(f"代理格式错误: {proxy_str}，应为: type,ip,port,user,pass")
            return None
        
        p_type, ip, port, user, pwd = parts
        # 构造 requests 格式: scheme://user:pass@host:port
        proxy_url = f"{p_type}://{user}:{pwd}@{ip}:{port}"
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    except Exception as e:
        print(f"解析代理失败: {e}")
        return None

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

def login(email, password, proxy_str=None):
    print('开始 login 流程')
    
    proxies = parse_proxy_str(proxy_str)
    if proxies:
        print(f"使用代理: {proxies}")

    # 1. 初始化 openai 配置
    print('1. 获取初始配置 (openai)')
    openai_cookie, json_data = openai.openai(proxies=proxies)
    
    # 维护一个全局 cookie 字符串，逐步合并
    all_cookie = ''
    all_cookie = merge_cookie_str(all_cookie, openai_cookie)
    
    # 2. 授权 (Authorize)
    print('2. 进行授权 (authorize)')
    auth_cookie = authorize.authorize(json_data['url'], proxies=proxies)
    all_cookie = merge_cookie_str(all_cookie, auth_cookie)
    
    # 3. 继续授权 (Auth Continue)
    print('3. 提交账号信息 (auth_continue)')
    time.sleep(2)
    # 注意：auth_continue 返回的 cookie 是下一步 login_verify 需要的
    cookie, auth_json = auth_continue.auth_continue(cookie_str=auth_cookie, email=email, proxies=proxies)
    all_cookie = merge_cookie_str(all_cookie, cookie)
    
    # 4. 检查流程分支
    # 如果返回的页面类型是 create_account_password，说明需要注册，这里直接返回 None
    if 'page' in auth_json and auth_json['page']['type'] == 'create_account_password':
        print('错误：检测到该邮箱需要注册账号，脚本仅支持登录。')
        return None
        
    # 5. 登录验证 (Login Verify)
    # 只有非注册流程才进入这里
    print('4. 验证密码 (login_verify)')
    cookie, json_data = login_verify.login_verify(cookie, email, password, proxies=proxies)
    all_cookie = merge_cookie_str(all_cookie, cookie)
    
    if 'continue_url' not in json_data:
        # 尝试提取错误信息
        error_msg = "未知错误"
        if 'details' in json_data:
            error_msg = json_data['details']
        elif 'error' in json_data:
            err = json_data['error']
            if isinstance(err, dict):
                error_msg = err.get('message', str(err))
            else:
                error_msg = str(err)
        
        print(f"登录验证失败: {error_msg}, 原始数据: {json_data}")
        raise Exception(f"登录失败: {error_msg}")

    time.sleep(2)
    
    # 6. 重定向 (Redirect)
    print('5. 跳转 (redirect)')
    # redirect 需要使用 accumulated all_cookie
    cookies = red.redirect(json_data['continue_url'], all_cookie, proxies=proxies)
    all_cookie = merge_cookie_str(all_cookie, cookies)
    
    time.sleep(2)
    
    # 7. 获取 Session
    print('6. 获取会话 (get_session)')
    # get_session 使用的是 redirect 返回的 cookies
    session_json = session.get_session(cookies, proxies=proxies)
    
    return json.dumps(session_json, ensure_ascii=False)

if __name__ == '__main__':
    result = login(email, password)
    if result:
        print('登录成功！Session信息：')
        print(result)
    else:
        print('登录流程未完成或失败。')

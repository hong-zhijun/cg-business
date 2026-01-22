from database import Team, ProxyAddress

def get_proxies_by_account(account_id):
    """
    根据 account_id 获取 requests 兼容的代理字典
    """
    if not account_id:
        return None

    # 1. 查找 Team
    team = Team.get_by_account_id(account_id)
    if not team or not team.get('proxy_id'):
        return None

    # 2. 查找 Proxy
    proxy = ProxyAddress.get_by_id(team['proxy_id'])
    if not proxy:
        return None

    # 3. 构造代理字符串
    protocol = proxy['protocol']  # http, socks5 等
    ip = proxy['ip']
    port = proxy['port']
    username = proxy.get('username')
    password = proxy.get('password')

    if username and password:
        # 格式: protocol://user:pass@ip:port
        proxy_url = f"{protocol}://{username}:{password}@{ip}:{port}"
    else:
        # 格式: protocol://ip:port
        proxy_url = f"{protocol}://{ip}:{port}"

    return {
        "http": proxy_url,
        "https": proxy_url
    }

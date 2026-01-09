import sys
import os
import socks
import socket

# 将当前文件的上级目录（即 xieyi 文件夹）添加到 sys.path
# 这样 Python 才能找到 'login_package' 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from login_package import login

# ================= 配置区域 =================

# 1. 账号密码
email = 'KaylaRobinson5900@outlook.com'
password = 'zkrpre44416@'

# 2. 前置代理 (本地 Clash 配置)
# 作用：因为本地无法直连远程代理 IP，所以需要先走本地 Clash
# 如果不需要前置代理，请将 use_upstream_proxy 设为 False
use_upstream_proxy = True
clash_ip = '127.0.0.1'
clash_port = 7897  # 请确认你的 Clash 混合/SOCKS5 端口

if use_upstream_proxy:
    # 设置默认代理为本地 Clash (实现代理链：本地 -> Clash -> 远程代理 -> 目标)
    socks.set_default_proxy(socks.SOCKS5, clash_ip, clash_port)
    socket.socket = socks.socksocket
    print(f"已启用前置代理 (Clash): {clash_ip}:{clash_port}")

    # 关键修正：针对 urllib3/requests 的 DNS 解析问题
    # 如果不加这一行，requests 可能会尝试本地解析远程代理域名/IP，导致解析失败或连接被阻断
    # 让 PySocks 接管 DNS 解析，强制通过代理进行
    def getaddrinfo(*args):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]
    # socket.getaddrinfo = getaddrinfo 
    # (注：PySocks 的 socksocket 已经处理了 connect 时的域名，但在多层代理场景下，
    # 显式 patch 可能会有帮助，不过我们先试试仅 patch socket)

# 3. 目标代理 (远程代理配置)
# 格式: 代理类型,ip,端口,用户名,密码
proxy_str = 'http,168.158.184.148,6159,nssenska,hsi4elcmh1o2' 

# ===========================================

# 调用登录接口
# 成功会返回 session 信息，失败返回 None
# 如果不需要代理，可以将 proxy_str 设为 None
result = login(email, password, proxy_str=proxy_str)

if result:
    print('登录成功！')
    print('Session信息：', result)
else:
    print('登录失败。')

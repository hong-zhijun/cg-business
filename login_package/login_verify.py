import requests
import json
from .sentinel_token import get_sentinel_token_by_flow


headers = {
    "accept": "application/json",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "openai-sentinel-token": "{\"p\":\"gAAAAABWzMwMDAsIlR1ZSBEZWMgMzAgMjAyNSAxNjozNTozNSBHTVQrMDgwMCAo5Lit5Zu95qCH5YeG5pe26Ze0KSIsNDI5NDk2NzI5Niw1MCwiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzE0My4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiaHR0cHM6Ly9zZW50aW5lbC5vcGVuYWkuY29tL2JhY2tlbmQtYXBpL3NlbnRpbmVsL3Nkay5qcyIsbnVsbCwiemgtQ04iLCJ6aC1DTiIsMTIsIm1lZGlhRGV2aWNlc+KIkltvYmplY3QgTWVkaWFEZXZpY2VzXSIsImxvY2F0aW9uIiwiaW5uZXJXaWR0aCIsMzI2ODU3LjA5OTk5OTk5OTYsIjdlZjFhM2U5LTY5YmQtNDkwYy04Y2NkLTVjMjNkNjMzNTEzMyIsIiIsMTIsMTc2NzA4MzQwODU0NC4zXQ==~S\",\"t\":\"ShEdAxkGAAwOFXBxHld1cFBsdU8FdmxDcnV7SWV/cGJjVxUdER8MGQMADA4VYltoY3FWA2x8QEl9aGVEd3t/BG1zRE1RdlZma3xASXd2WGF5YUZteXByd3V1VnZrdmVGcWlMeVNgHwVmZmZNeXNWam98QElyeXFyY3VvfXJycR5tdnBQZnVlQmpoYXlQYHhMc3RERVJ2Y1hqdmVCcGxlZld3aG5uY2ZKdmBjZmJ2ZUJ2aWVUeXtJfXFzcRZ5YHd5dmZARnxsBEAMEQIWBQEdFxYNE31qU0J+d2sJFR0RGwQZBAEMDhV8WWdBeXVmExYbEwoYGgMCERQWeUt2W3pzUg4MGBUBHRkFFQsRT1xxQWQfXGBpA11hUV0Kf3V1aFFrBmV5ZEllc3RiZ3lwRnJqV0AMDgwYFQAKAAADEwkMdXZ0DgwYFQgCAAYFEwkMcQVVa3xyfQFieExVY2JdYFVnZXRsBklSaHFhZGZFW2JjA2BXb111aGZhQX98TFNUZX8BdWZleGNkdwJ0YnFSfGZxYWRmRURTZmV3YHRnV0xjcWtyf3xhVGtoRH9gA2Bnb1l+S2ZxAHh7YnFoa3tAZmBfF2xkAHlLbAZreH9iW2dlRVxTZmV8bGAAQ3picWd7eVh9Z2FFdmZkX0pVZnd1enFADA4MGBUJBAADBhMJDHZmDA4MGBUDHRsFFQsRbWUKDBECFgIHHRwAFQsRfVxxYWJCbm5pAEJQYgFlTHB2BXRtdXJUdGxiZmNmF1BgAl95ZgZ/VXxmcmRxf1d0cGJnY2FaV31mBlkEeHJhUHVJBHV5RFZiZmdxT2Vac2p/ZnJkcWxHY2R2aG1gdH0dZwdjd3lmcmRxSXlTdGZ0Zm9daUxjX2h9b3V6ZnFsR2NjdkplZgBYfHJ2ZHxvQ3pydUVQbmIDWm1UAGFqY1tGZW1DclBgfwkKEx8MAwAfCwwOFXByb3V2cHJvdXZwcm91dnByb3V2cHJvdRUdERcHGQEKDA4HHwodBQIDBBkNBwAAHAIFAwcCFgEDHRgGFQsRbXVteHIfbmJkWFlzdWd6aWBmdHV7TA5VYmhucWB2SmBwZHl5bGJVVnZYBklreHlRc0tBdXZWWGZ8ZmB7ZmF1UGV7enRmWEVVYABxb2NaRVJ2WFN5ZkIBYmcAaHVvXUt5dXF3cXtyDlNle3puaXZsfHABeWZgB3N2eXJmcGEeemZkZmRmVndbdnV2cHdsZW5mcm9ldXBEZHxmAHFmbGEAYmYFdWFlHw1iZ0RsZmZncUhjBmd3eXJPcGFWX3ZyS0V2c0Zib3xAZHYMGBUFBgAAABMJDHtjcEZjYFwMEQIWAwAdGAMVCxF5YVNQYWtle3lyaGJmWmVMdXFFe3hyBmFrfFhkaXZjVmAABnt1BgBpZl95YWEeZnBpdVZlFUw=\",\"c\":\"gAAAAABpU45fkgo7NJ-4Spid19k3aR5d6RvAiSalfHXBtl_quszr6QKk8uDhC6ynkFWqq4HV-hkq350FRP2o8NILn8f0Q-42Upr1tU5EfBXg5lAGM1cg26_NjYMJHGTX2Xg7Lsq0Ls26WQ2MOh41GGBeoEqOSRlhicIMoKp8U-NTwCUbBs_9NA5YkSsIaf0yz-dSLsfDrKE90-dqaOA1lNyqqihBqjGqvIb9zHD4m9L2ddlmj1pZv2GYlPfbsiI31CRLD2Qy2wuuAr275Kru4IIb_PXGHI9xCGQQ1aGLuZaNf_GccUlSxUfU4yCDpOcKPB7Eek1KQR5s1wF8NUj8swWhEXTgpjl3L8MbSxRjzHk18MaOvy1cKkwpAYsmY3175KyERLaXvX4Nn0F05RUV5H7tMnDlY9H4g1TcRdCJ_jcrSAdkN7RxRRQMvjNOQ8LYLFYq0niFjlKspfuj6jckSwvj_SKXcxm_V2Y38GOLAMztMRySBolYLK2jFpFsWV2wNBi_pMJBKh4R5n8GYLeQk2CL1NetWGamZedFGEcPz6r_chJ8tU4YOa9eZ0MM_ZCWMc2EbJ0NNUj4e2J8r3v5AmAy2k-1rJpSApwPY-rpI3LHRTf4IjbSqzBfW7vdt8O1WuEuaw6jMfuzfFcTEjyMIo0l_fmxLDM_3Jb6ukm-9Fu6LZTKQYnkQygDTxscuPPXrPfbcciX700C2KgCD-NHE5YmTXyxllKjMynhMd1dM165kJrqL8Ij27Z9S8apPRNtKll6H5rZ9WB5AQrQ1bdtsGD_ro5-czDgXRHRwlwHN6xBTX7ian3ZE-OTEjKYHmUnRz4vZcgGG9m3eD8z_mcWbwO6Bb1Mo6sl75hJxpIR3Uei2iY8Ij6_HkpHvc3c3VfKli9RFuI-rVMhh8zu8P6KfPDaU-8iwn_C3ilm2tMIqwwzIA_3MCqMtltQwOo26eQ6PAmMhvUgn3awANjnmraLkWtjBSGyAOE_U976IxkZY48Dj0OF5uBqbmRXH_tNUHQ3nwrrB6JV53XFb0sGeHuZsBsLEQjoKOzLHSR7dQn4Hcc3A-Mv5LBEOmDbrTgrU-CsAowkpTHN1sUOlonxyxo0TaF7UlPnCJtS_gmmY8ZrvsV6Go64EchCH24EQ66rL2Ai-SHSvcXVYDn5OKljLJcKAJfK_y-ZcHt9RkJEnyoXjlVM3b_Tzxxm5CUNTl5ZBe8InCCz67xgomxzCoB31xyhsEb9GaJRbONlOyjFo5GPkWHAVeRTEvA7jmxozW6b9VZWl0k8cTpCEjchLVrMwdPzisNeAjICUnv-ZrMyna7EEMhA_YmUxvX65c2OBzlKtmv224MMlO_Ud9YexmNKOHgbmusaQwC9IBta6S1p__80xcqv9Y36CilA3crd5z42YSXxcEngUSmGugyOJ2gSU6JtNrGfvanJoVO-Q-2wKhAshnYE58AIPGx89kYsyzyN59BAWY-uTLRyOWZ-6lDi4EiMEETSp2cacqXhdFW8ic5IuszALKxAHqbCab7UK-nNo7XLXr_Z0CiDHdP7-DMsMdp--30EfKJo0ryVI9bxyMClgMiPZ6E-Kk9NYKrOr25pZgsT6YTw2F-rLT-HCKPHPufLnxcZcHeAeZlx66wEmkFtkczxs7IOX6-s4VRfvDEEaCv4VAcZioJsqOKmk2rLs6esIbHvkvHWjSqH4Uh51k5DpxUITATnIb1yNrDmvT7BCDZUjs1IezvyVgF1\",\"id\":\"8d181987-e570-4954-b957-88ab5e4655a8\",\"flow\":\"password_verify\"}",
    "origin": "https://auth.openai.com",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://auth.openai.com/log-in/password",
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
url = "https://auth.openai.com/api/accounts/password/verify"

headers['openai-sentinel-token'] = get_sentinel_token_by_flow('password_verify')

def login_verify(cookies,email,password, proxies=None):
    headers['cookie'] = cookies
    data = {
        "username": email,
        "password": password
    }
    response = requests.post(url, headers=headers,  json=data, proxies=proxies)

    print(response.text)
    print(response)
    cookie_str = "; ".join([f"{k}={v}" for k, v in response.cookies.items()])
    return cookie_str,response.json()
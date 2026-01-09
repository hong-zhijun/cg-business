# ChatGPT 登录代码迁移计划 (Migration Plan)

本文档旨在规划将 `chatgpt-login` 目录下的登录脚本从 `requests` / `cloudscraper` 迁移到 `curl_cffi` 的流程，并统一设备指纹，以解决风控问题并提高稳定性。

## 🎯 目标

1.  **统一技术栈**：与主应用 (`app_new.py`) 保持一致，使用 `curl_cffi` 处理网络请求。
2.  **增强抗风控**：利用 `curl_cffi` 的 TLS 指纹模拟能力 (`impersonate`)，避免被识别为 Python 脚本。
3.  **统一设备指纹**：确保登录阶段与后续 API 调用阶段的 User-Agent 和设备特征一致（建议统一为 macOS / Chrome）。

---

## 🛠️ 1. 环境准备

-   确认已安装 `curl_cffi` 库：
    ```bash
    pip install curl_cffi
    ```

---

## 📝 2. 代码修改详细流程

### Phase 1: 基础配置调整

1.  **定义统一的 Headers (在 `login.py` 或单独的 `config.py` 中)**
    -   **移除**：旧代码中针对 Windows 的 User-Agent 和硬编码的 `Sec-CH-UA`。
    -   **新增**：使用与 `app_new.py` 一致的 Mac User-Agent。
    ```python
    # 示例
    COMMON_HEADERS = {
        "accept-language": "zh-CN,zh;q=0.9",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        # 其他通用 header，不要包含 sec-ch-ua 等具体指纹字段，交给 curl_cffi 处理
    }
    ```

### Phase 2: 逐步替换请求模块

需要按登录流程顺序，依次修改以下文件：

#### Step 1: `openai.py` (获取初始配置)

-   **当前**：使用 `requests.post`，包含大量硬编码 Cookie (`__cf_bm`, `oai-did`)。
-   **修改**：
    -   引入 `from curl_cffi import requests as cf_requests`。
    -   替换 `requests.post` 为 `cf_requests.post`。
    -   **移除** 所有硬编码的 Cookies（特别是 `__cf_bm`，让库自动处理）。
    -   添加参数 `impersonate="chrome110"`。
    -   确保 `proxies` 参数格式正确传递。

#### Step 2: `authorize.py` (授权页面)

-   **当前**：使用 `cloudscraper` 绕过 CF。
-   **修改**：
    -   完全移除 `cloudscraper` 依赖。
    -   使用 `cf_requests.get(..., impersonate="chrome110")`。
    -   此步骤主要为了获取 CSRF Token 和初始 Session，`curl_cffi` 可以轻松穿透 CF 验证。

#### Step 3: `auth_continue.py` (提交邮箱)

-   **当前**：使用 `requests.post`。
-   **修改**：
    -   替换为 `cf_requests.post`。
    -   保持 `impersonate="chrome110"`。
    -   检查 `Referer` 和 `Origin` 是否指向 `https://auth0.openai.com` (根据实际抓包调整)。

#### Step 4: `login_verify.py` (验证密码)

-   **当前**：使用 `requests.post` 提交密码。
-   **修改**：
    -   替换为 `cf_requests.post`。
    -   **关键点**：此步骤最容易触发风控。确保 `impersonate` 参数与前面步骤完全一致，保持 Session (Cookies) 的连续性。建议使用 `cf_requests.Session()` 来管理整个会话，而不是每次请求都手动传 Cookie 字符串。

#### Step 5: `session.py` (获取最终 Token)

-   **当前**：请求 `https://chatgpt.com/api/auth/session`。
-   **修改**：
    -   替换为 `cf_requests.get`。
    -   确保最终返回的 Access Token 有效。

### Phase 3: 工具类与代理优化

1.  **Cookie 管理 (`login.py`)**

    -   **建议**：不再手动解析和拼接 Cookie 字符串 (`parse_cookie_str`, `merge_cookie_str`)。
    -   **优化**：改用 `cf_requests.Session()` 对象。它会自动管理 Cookie Jar，就像浏览器一样。
    -   **重构 `login()` 函数**：实例化一个 `session = cf_requests.Session()`，将这个 session 对象传递给各个子模块，而不是传递 cookie 字符串。

2.  **代理处理 (`login.py`)**
    -   `curl_cffi` 的代理格式与 `requests` 略有不同（通常通用，但需测试 `socks5h` 等协议的支持情况）。
    -   确保 `parse_proxy_str` 返回的格式能被 `curl_cffi` 正确识别。

---

## ⚠️ 风险与注意事项

1.  **指纹一致性**：整个流程必须使用 **同一个** `Session` 对象和 **同一个** `impersonate` 参数（如 `chrome110`），切勿混用。
2.  **PoW (Proof of Work)**：
    -   如果 OpenAI 启用了复杂的 PoW 验证（如 `proof_of_work.py` 中的逻辑），`curl_cffi` 本身不负责计算 PoW，只负责发送。
    -   如果现有 PoW 计算逻辑依赖特定的浏览器环境值（如 `screen` 尺寸），需要确保这些值与我们模拟的 Mac 指纹相符。
3.  **Arkose Labs (验证码)**：
    -   如果登录过程中弹出 Arkose 验证码（拼图/旋转图片），纯协议脚本无法处理，需要对接打码平台或抛出异常提示用户。

## ✅ 验收标准

1.  代码中不再包含 `import requests` 或 `import cloudscraper`。
2.  所有请求均通过 `curl_cffi` 发起。
3.  成功登录并打印出 Access Token。
4.  生成的 Token 在主应用 (`app_new.py`) 中能正常使用，不报 403 错误。

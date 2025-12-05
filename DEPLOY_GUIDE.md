# 🚀 服务器部署指南

本指南将帮助您将 ChatGPT Team 自动管理系统部署到服务器上。支持 Linux (推荐) 和 Windows Server。

---

## 🐧 Linux 服务器部署 (推荐)

适用于 Ubuntu 20.04+, Debian 10+, CentOS 7+ 等主流 Linux 发行版。

### 1. 上传代码

将本地所有文件上传到服务器的任意目录（例如 `/root/chatgpt-team`）。
可以使用 `scp`、`FileZilla` 或其他工具。

### 2. 运行一键部署脚本

以 root 用户身份执行以下命令：

```bash
# 赋予脚本执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh
```

### 3. 部署完成

脚本会自动完成以下操作：

-   ✅ 安装 Python3 和 pip
-   ✅ 安装项目依赖
-   ✅ 创建系统服务 (Systemd)
-   ✅ 配置防火墙端口 (5002)
-   ✅ 启动服务并设置开机自启

**部署成功后，您将看到如下信息：**

```
✅ 部署成功！
📍 访问地址：
   用户页面: http://<服务器IP>:5002/
   管理后台: http://<服务器IP>:5002/admin
🔑 管理员密码: Qq3142016904 (脚本默认)
```

### 4. 常用维护命令

-   **查看状态**: `systemctl status chatgpt-team`
-   **查看日志**: `journalctl -u chatgpt-team -f`
-   **重启服务**: `systemctl restart chatgpt-team`
-   **停止服务**: `systemctl stop chatgpt-team`

---

## 🪟 Windows Server 部署

### 1. 环境准备

1.  **安装 Python**: 下载并安装 Python 3.10+ ([下载地址](https://www.python.org/downloads/windows/))。
    -   ⚠️ 安装时务必勾选 **"Add Python to PATH"**。
2.  **上传代码**: 将项目文件复制到服务器上的文件夹（例如 `C:\chatgpt-team`）。

### 2. 安装依赖

打开 PowerShell 或 CMD，进入项目目录，运行：

```powershell
pip install -r requirements_new.txt
```

### 3. 启动服务

#### 方式 A: 简单运行 (测试用)

直接双击运行目录下的 **`start_server.bat`**。

-   **优点**: 简单方便。
-   **缺点**: 关闭窗口服务就会停止，无法开机自启。

#### 方式 B: 使用 NSSM 注册为服务 (生产环境推荐)

1.  下载 [NSSM](https://nssm.cc/download) 并解压。
2.  将 `nssm.exe` (选择 64 位版本) 复制到 `C:\Windows\System32`。
3.  以管理员身份打开 CMD，运行：
    ```cmd
    nssm install ChatGPTTeam
    ```
4.  在弹出的窗口中配置：
    -   **Path**: 选择 python.exe 的路径 (例如 `C:\Python310\python.exe`)
    -   **Startup directory**: 选择项目目录 (例如 `C:\chatgpt-team`)
    -   **Arguments**: 输入 `app_new.py`
5.  点击 "Install service"。
6.  启动服务：
    ```cmd
    nssm start ChatGPTTeam
    ```

---

## ⚙️ 配置文件说明

部署前或部署后，您可以修改 `config.py` 文件来自定义配置：

```python
# 管理员密码
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '123456')

# 服务端口
PORT = int(os.environ.get('PORT', 5002))
```

-   **Linux**: 修改 `/etc/systemd/system/chatgpt-team.service` 中的 `Environment` 变量，然后运行 `systemctl daemon-reload && systemctl restart chatgpt-team`。
-   **Windows**: 直接修改 `config.py` 文件，然后重启服务。

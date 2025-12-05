#!/bin/bash

# ChatGPT Team 自动邀请系统 - 一键部署脚本

set -e

echo "🚀 ChatGPT Team 自动邀请系统 - 一键部署"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  请使用 root 用户或 sudo 运行此脚本"
    exit 1
fi

# 1. 安装依赖
echo ""
echo "📦 步骤 1/5: 安装系统依赖..."
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y python3 python3-pip
elif command -v yum &> /dev/null; then
    yum install -y python3 python3-pip
else
    echo "❌ 不支持的操作系统"
    exit 1
fi

# 2. 准备项目文件
echo ""
echo "📁 步骤 2/5: 准备项目文件..."
PROJECT_DIR="/opt/chatgpt-team"
mkdir -p $PROJECT_DIR

# 复制当前目录下的所有文件到项目目录
cp -r ./* $PROJECT_DIR/
cd $PROJECT_DIR

# 3. 安装 Python 依赖
echo ""
echo "🐍 步骤 3/5: 安装 Python 依赖..."
pip3 install -r requirements_new.txt

# 4. 配置系统服务
echo ""
echo "⚙️  步骤 4/5: 配置系统服务..."
cat > /etc/systemd/system/chatgpt-team.service << 'EOF'
[Unit]
Description=ChatGPT Team Auto Invite Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/chatgpt-team
Environment="ADMIN_PASSWORD=${ADMIN_PASSWORD:-Moyu123456@}"
Environment="PORT=5002"
ExecStart=/usr/bin/python3 /opt/chatgpt-team/app_new.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 5. 启动/重启服务
echo ""
echo "🎯 步骤 5/5: 检查并启动服务..."
systemctl daemon-reload

if systemctl is-enabled chatgpt-team &> /dev/null; then
    echo "🔄 服务已存在，正在重启..."
    systemctl restart chatgpt-team
else
    echo "✨ 服务首次安装，正在启动..."
    systemctl enable chatgpt-team
    systemctl start chatgpt-team
fi

# 等待服务启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet chatgpt-team; then
    echo ""
    echo "=========================================="
    echo "✅ 部署成功！"
    echo "=========================================="
    echo ""
    echo "📍 访问地址："
    echo "   用户页面: http://$(hostname -I | awk '{print $1}'):5002/"
    echo "   管理后台: http://$(hostname -I | awk '{print $1}'):5002/admin"
    echo ""
    echo "🔑 管理员密码: ${ADMIN_PASSWORD:-Moyu123456@}"
    echo ""
    echo "📊 常用命令："
    echo "   查看状态: systemctl status chatgpt-team"
    echo "   查看日志: journalctl -u chatgpt-team -f"
    echo "   重启服务: systemctl restart chatgpt-team"
    echo "   停止服务: systemctl stop chatgpt-team"
    echo ""
    echo "⚠️  注意："
    echo "   1. 请确保云服务器安全组已开放 5002 端口"
    echo "   2. 建议配置 Nginx 反向代理和 HTTPS"
    echo "   3. 定期备份数据库文件: /opt/chatgpt-team/chatgpt_team.db"
    echo ""
else
    echo ""
    echo "❌ 服务启动失败，请查看日志："
    echo "   journalctl -u chatgpt-team -n 50"
    exit 1
fi

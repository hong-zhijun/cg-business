#!/bin/bash

# ChatGPT Team 保持数据重新部署脚本
# 用于在服务器上更新代码的同时保留数据库数据

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 ChatGPT Team 保持数据重新部署"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_FILE="chatgpt_team.db"
OLD_DB_BACKUP="${BACKUP_DIR}/chatgpt_team_before_update_${TIMESTAMP}.db"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

echo "📋 步骤 1/6: 检查当前环境"
echo "----------------------------------------"

# 检查是否在正确的目录
if [ ! -f "app_new.py" ]; then
    echo -e "${RED}❌ 错误: 未找到 app_new.py,请确保在项目根目录运行此脚本${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 当前目录正确${NC}"

# 检查数据库是否存在
if [ -f "${DB_FILE}" ]; then
    echo -e "${GREEN}✅ 找到现有数据库: ${DB_FILE}${NC}"
    HAS_OLD_DB=true
else
    echo -e "${YELLOW}⚠️  未找到现有数据库,将创建新数据库${NC}"
    HAS_OLD_DB=false
fi

echo ""
echo "📦 步骤 2/6: 备份现有数据"
echo "----------------------------------------"

if [ "$HAS_OLD_DB" = true ]; then
    cp ${DB_FILE} ${OLD_DB_BACKUP}
    echo -e "${GREEN}✅ 数据库已备份到: ${OLD_DB_BACKUP}${NC}"
    
    # 导出 Teams 信息到 JSON (用于手动恢复)
    echo "📤 导出 Teams 信息..."
    python3 << 'EOF'
import sqlite3
import json
from datetime import datetime

try:
    conn = sqlite3.connect('chatgpt_team.db')
    cursor = conn.cursor()
    
    # 尝试读取 teams 表
    cursor.execute("SELECT id, name, account_id, organization_id, created_at FROM teams")
    teams = cursor.fetchall()
    
    teams_data = []
    for team in teams:
        teams_data.append({
            'id': team[0],
            'name': team[1],
            'account_id': team[2],
            'organization_id': team[3],
            'created_at': team[4]
        })
    
    # 保存到 JSON
    backup_file = f'backups/teams_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(teams_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Teams 信息已导出到: {backup_file}")
    print(f"   共 {len(teams_data)} 个 Team")
    
    conn.close()
except Exception as e:
    print(f"⚠️  导出 Teams 信息失败: {e}")
    print("   这可能是因为数据库结构不同,请手动检查")
EOF
else
    echo -e "${YELLOW}⚠️  没有现有数据需要备份${NC}"
fi

echo ""
echo "🔄 步骤 3/6: 停止现有服务"
echo "----------------------------------------"

# 尝试停止现有进程
if pgrep -f "app_new.py" > /dev/null; then
    echo "🛑 停止现有的 app_new.py 进程..."
    pkill -f "app_new.py" || true
    sleep 2
    echo -e "${GREEN}✅ 服务已停止${NC}"
else
    echo -e "${YELLOW}⚠️  未发现运行中的服务${NC}"
fi

echo ""
echo "📥 步骤 4/6: 拉取最新代码"
echo "----------------------------------------"

# 检查是否是 git 仓库
if [ -d ".git" ]; then
    echo "🔄 从 GitHub 拉取最新代码..."
    git pull origin main
    echo -e "${GREEN}✅ 代码更新完成${NC}"
else
    echo -e "${RED}❌ 错误: 不是 git 仓库,请先执行:${NC}"
    echo "   git clone https://github.com/siyutaosiyutao/chagpt.git"
    exit 1
fi

echo ""
echo "🗄️  步骤 5/6: 数据库处理"
echo "----------------------------------------"

if [ "$HAS_OLD_DB" = true ]; then
    echo -e "${YELLOW}⚠️  检测到旧数据库${NC}"
    echo ""
    echo "由于新版本数据库结构发生重大变化,你有两个选择:"
    echo ""
    echo "  1) 保留旧数据库 (不推荐,可能导致错误)"
    echo "  2) 创建新数据库 (推荐,旧数据已备份)"
    echo ""
    read -p "请选择 [1/2] (默认: 2): " choice
    choice=${choice:-2}
    
    if [ "$choice" = "2" ]; then
        echo "🗑️  移除旧数据库..."
        mv ${DB_FILE} ${BACKUP_DIR}/old_${DB_FILE}
        echo "✅ 旧数据库已移至备份目录"
        
        echo "🆕 创建新数据库结构..."
        python3 -c "from database import init_db; init_db()"
        echo -e "${GREEN}✅ 新数据库创建成功${NC}"
        
        echo ""
        echo -e "${YELLOW}📝 重要提示:${NC}"
        echo "   - 旧数据库已备份到: ${OLD_DB_BACKUP}"
        echo "   - Teams 信息已导出到: backups/teams_backup_*.json"
        echo "   - 请在新的 Admin 界面重新添加 Teams"
        echo "   - 需要重新配置 Auto-Kick 设置"
    else
        echo -e "${YELLOW}⚠️  保留旧数据库,可能会遇到兼容性问题${NC}"
    fi
else
    echo "🆕 创建新数据库..."
    python3 -c "from database import init_db; init_db()"
    echo -e "${GREEN}✅ 数据库创建成功${NC}"
fi

echo ""
echo "🚀 步骤 6/6: 启动服务"
echo "----------------------------------------"

# 检查依赖
echo "📦 检查 Python 依赖..."
if [ -f "requirements_new.txt" ]; then
    pip3 install -r requirements_new.txt -q
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
fi

# 启动服务
echo "🚀 启动服务..."
nohup python3 app_new.py > app.log 2>&1 &
sleep 2

# 检查服务是否启动成功
if pgrep -f "app_new.py" > /dev/null; then
    echo -e "${GREEN}✅ 服务启动成功!${NC}"
    echo ""
    echo "📊 服务信息:"
    echo "   - 进程 ID: $(pgrep -f app_new.py)"
    echo "   - 日志文件: app.log"
    echo "   - 访问地址: http://localhost:5000"
    echo ""
    echo "查看日志: tail -f app.log"
else
    echo -e "${RED}❌ 服务启动失败,请查看日志: tail -f app.log${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 部署完成!${NC}"
echo "=========================================="
echo ""
echo "📋 新功能说明:"
echo "   1. ✅ Fail2ban 防护 - 登录失败 5 次锁定 30 分钟"
echo "   2. ✅ 无限邀请码 - 每个 Team 可生成无限邀请码"
echo "   3. ✅ 4人上限 - 每个 Team 最多 4 个成员"
echo "   4. ✅ 成员管理 - Admin 可直接邀请和踢出成员"
echo "   5. ✅ 1日邀请码 - 临时邀请,24小时后自动踢出"
echo ""
echo "🔗 访问管理后台:"
echo "   http://your-server-ip:5000/admin/login"
echo ""
echo "📚 备份文件位置:"
echo "   - 数据库备份: ${OLD_DB_BACKUP}"
echo "   - Teams 信息: backups/teams_backup_*.json"
echo ""
echo "⚠️  如果选择了创建新数据库,请:"
echo "   1. 访问 Admin 界面"
echo "   2. 重新添加 Teams (使用备份的 session JSON)"
echo "   3. 重新配置 Auto-Kick 设置"
echo ""


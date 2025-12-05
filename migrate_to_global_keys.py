"""
数据库迁移脚本 - 将邀请码从绑定 Team 改为全局邀请码
"""
import sqlite3
import shutil
from datetime import datetime

# 备份数据库
backup_file = f"chatgpt_team_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy('chatgpt_team.db', backup_file)
print(f"✅ 数据库已备份到: {backup_file}")

# 连接数据库
conn = sqlite3.connect('chatgpt_team.db')
cursor = conn.cursor()

print("\n🔄 开始迁移数据库...")

# 1. 修改 access_keys 表 - 移除 team_id 字段
print("\n1️⃣ 迁移 access_keys 表...")
try:
    # 创建新表 (不包含 team_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_keys_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_code TEXT NOT NULL UNIQUE,
            is_temp BOOLEAN DEFAULT 0,
            temp_hours INTEGER DEFAULT 0,
            is_cancelled BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 迁移数据 (去除 team_id)
    cursor.execute('''
        INSERT INTO access_keys_new (id, key_code, is_temp, temp_hours, is_cancelled, created_at)
        SELECT id, key_code, is_temp, temp_hours, is_cancelled, created_at
        FROM access_keys
    ''')
    
    # 删除旧表,重命名新表
    cursor.execute('DROP TABLE access_keys')
    cursor.execute('ALTER TABLE access_keys_new RENAME TO access_keys')
    
    print("   ✅ access_keys 表迁移完成 - 邀请码已改为全局模式")
except Exception as e:
    print(f"   ⚠️  access_keys 表迁移失败: {e}")

# 提交更改
conn.commit()
conn.close()

print("\n✅ 数据库迁移完成!")
print(f"📦 备份文件: {backup_file}")
print("\n💡 提示:")
print("   - 邀请码不再绑定特定 Team")
print("   - 用户使用邀请码时,系统会自动从未满员的 Team 中选择")
print("   - 优先填满快满的 Team (按成员数从多到少排序)")
print("   - 如果一个 Team 邀请失败,会自动尝试下一个 Team")


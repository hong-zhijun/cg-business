"""
数据库迁移脚本 - 从旧结构迁移到新结构
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

# 1. 修改 access_keys 表
print("\n1️⃣ 迁移 access_keys 表...")
try:
    # 创建新表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_keys_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            key_code TEXT NOT NULL UNIQUE,
            is_temp BOOLEAN DEFAULT 0,
            temp_hours INTEGER DEFAULT 0,
            is_cancelled BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
        )
    ''')
    
    # 迁移数据 - 将旧的 is_used 密钥转换为新的邀请记录
    cursor.execute('''
        INSERT INTO access_keys_new (id, team_id, key_code, is_temp, temp_hours, is_cancelled, created_at)
        SELECT id, team_id, key_code, 0, 0, 
               CASE WHEN is_used = 1 THEN 1 ELSE 0 END,
               created_at
        FROM access_keys
    ''')
    
    # 删除旧表,重命名新表
    cursor.execute('DROP TABLE access_keys')
    cursor.execute('ALTER TABLE access_keys_new RENAME TO access_keys')
    
    print("   ✅ access_keys 表迁移完成")
except Exception as e:
    print(f"   ⚠️  access_keys 表已经是新结构或迁移失败: {e}")

# 2. 修改 invitations 表
print("\n2️⃣ 迁移 invitations 表...")
try:
    # 创建新表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invitations_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            key_id INTEGER,
            email TEXT NOT NULL,
            user_id TEXT,
            invite_id TEXT,
            status TEXT DEFAULT 'pending',
            is_temp BOOLEAN DEFAULT 0,
            temp_expire_at TIMESTAMP,
            is_confirmed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
            FOREIGN KEY (key_id) REFERENCES access_keys (id) ON DELETE SET NULL
        )
    ''')
    
    # 迁移数据
    cursor.execute('''
        INSERT INTO invitations_new (id, team_id, key_id, email, user_id, invite_id, status, is_temp, temp_expire_at, is_confirmed, created_at)
        SELECT id, team_id, key_id, email, NULL, invite_id, status, 0, NULL, 0, created_at
        FROM invitations
    ''')
    
    # 删除旧表,重命名新表
    cursor.execute('DROP TABLE invitations')
    cursor.execute('ALTER TABLE invitations_new RENAME TO invitations')
    
    print("   ✅ invitations 表迁移完成")
except Exception as e:
    print(f"   ⚠️  invitations 表已经是新结构或迁移失败: {e}")

# 3. 创建 login_attempts 表
print("\n3️⃣ 创建 login_attempts 表...")
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            username TEXT,
            success BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_login_attempts_ip 
        ON login_attempts(ip_address, created_at)
    ''')
    
    print("   ✅ login_attempts 表创建完成")
except Exception as e:
    print(f"   ⚠️  login_attempts 表已存在或创建失败: {e}")

# 提交更改
conn.commit()
conn.close()

print("\n✅ 数据库迁移完成!")
print(f"📦 备份文件: {backup_file}")
print("\n💡 提示:")
print("   - 旧的 access_keys 中 is_used=1 的密钥已被标记为 is_cancelled=1")
print("   - 所有邀请记录已保留,但新增了临时邀请相关字段")
print("   - 新增了 login_attempts 表用于 fail2ban 功能")


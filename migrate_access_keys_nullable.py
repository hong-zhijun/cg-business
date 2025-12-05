"""
迁移脚本: 允许 access_keys.team_id 为空,以便在邀请码使用时再分配 Team
"""
import shutil
import sqlite3
from datetime import datetime

DB_PATH = 'chatgpt_team.db'

backup_file = f"chatgpt_team_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy(DB_PATH, backup_file)
print(f"✅ 数据库已备份到: {backup_file}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("🔄 开始迁移 access_keys 表结构...")

try:
    cursor.execute('PRAGMA foreign_keys = OFF;')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_keys_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER,
            key_code TEXT NOT NULL UNIQUE,
            is_temp BOOLEAN DEFAULT 0,
            temp_hours INTEGER DEFAULT 0,
            is_cancelled BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        INSERT INTO access_keys_new (id, team_id, key_code, is_temp, temp_hours, is_cancelled, created_at)
        SELECT id, team_id, key_code, is_temp, temp_hours, is_cancelled, created_at
        FROM access_keys
    ''')

    cursor.execute('DROP TABLE access_keys')
    cursor.execute('ALTER TABLE access_keys_new RENAME TO access_keys')

    cursor.execute('PRAGMA foreign_keys = ON;')
    conn.commit()
    print("✅ access_keys 表迁移完成! team_id 现在允许为空。")
except Exception as exc:
    conn.rollback()
    print(f"⚠️  迁移失败: {exc}")
finally:
    conn.close()

print("🎉 迁移结束,请确认功能正常后再删除备份。")

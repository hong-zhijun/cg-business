#!/usr/bin/env python3
"""
数据库迁移脚本：为teams表添加last_invite_at字段
"""
import sqlite3
import shutil
from datetime import datetime

DB_PATH = 'chatgpt_team.db'

def backup_database():
    """备份数据库"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'{DB_PATH}.backup_{timestamp}'
    shutil.copy(DB_PATH, backup_file)
    print(f"✅ 数据库已备份到: {backup_file}")
    return backup_file

def migrate():
    """执行迁移"""
    print("开始迁移...")

    # 备份数据库
    backup_file = backup_database()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(teams)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'last_invite_at' in columns:
            print("⚠️  last_invite_at 字段已存在，无需迁移")
            conn.close()
            return

        # 添加last_invite_at字段
        print("正在添加 last_invite_at 字段...")
        cursor.execute('''
            ALTER TABLE teams
            ADD COLUMN last_invite_at TIMESTAMP
        ''')

        conn.commit()
        print("✅ last_invite_at 字段添加成功")

        # 验证
        cursor.execute("PRAGMA table_info(teams)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"✅ 当前teams表字段: {', '.join(columns)}")

        conn.close()
        print("✅ 迁移完成！")

    except Exception as e:
        print(f"❌ 迁移失败: {str(e)}")
        print(f"请从备份恢复: cp {backup_file} {DB_PATH}")
        raise

if __name__ == '__main__':
    migrate()

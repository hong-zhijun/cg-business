"""
配置文件
"""
import os
import secrets

# 管理员密码（首次运行时会提示设置）
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '123456')  # 部署时请修改

# 数据库配置
DATABASE_PATH = 'chatgpt_team.db'

# 每个 Team 最多生成的密钥数量
MAX_KEYS_PER_TEAM = 4

# 密钥长度
KEY_LENGTH = 32

# Flask 配置
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5002))

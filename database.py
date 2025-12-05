"""
数据库模型
"""
import sqlite3
import secrets
import time
from datetime import datetime
from contextlib import contextmanager
from config import DATABASE_PATH, MAX_KEYS_PER_TEAM, KEY_LENGTH


def execute_with_retry(func, max_retries=3):
    """数据库操作重试装饰器，处理数据库锁定错误"""
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and attempt < max_retries - 1:
                # 指数退避: 0.1s, 0.2s, 0.3s
                time.sleep(0.1 * (attempt + 1))
            else:
                raise
    return None


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # 开启外键约束支持
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Teams 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                account_id TEXT NOT NULL,
                access_token TEXT NOT NULL,
                organization_id TEXT,
                email TEXT,
                last_invite_at TIMESTAMP,
                token_error_count INTEGER DEFAULT 0,
                token_status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 为已存在的表添加新字段（如果不存在）
        try:
            cursor.execute('ALTER TABLE teams ADD COLUMN token_error_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # 字段已存在
        
        try:
            cursor.execute('ALTER TABLE teams ADD COLUMN token_status TEXT DEFAULT "active"')
        except sqlite3.OperationalError:
            pass  # 字段已存在

        try:
            cursor.execute('ALTER TABLE teams ADD COLUMN member_check_error_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # 字段已存在

        try:
            cursor.execute('ALTER TABLE teams ADD COLUMN member_check_first_error_at TIMESTAMP')
        except sqlite3.OperationalError:
            pass  # 字段已存在

        try:
            cursor.execute('ALTER TABLE teams ADD COLUMN active_start TIMESTAMP')
        except sqlite3.OperationalError:
            pass  # 字段已存在

        try:
            cursor.execute('ALTER TABLE teams ADD COLUMN active_until TIMESTAMP')
        except sqlite3.OperationalError:
            pass  # 字段已存在

        try:
            cursor.execute('ALTER TABLE teams ADD COLUMN member_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # 字段已存在

        # Access Keys 表 (重构: 每个邀请码对应一个 Team)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_keys (
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
        
        # Invitations 表（记录所有邀请）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invitations (
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

        # 自动检测配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_kick_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled BOOLEAN DEFAULT 0,
                check_interval_min INTEGER DEFAULT 90,
                check_interval_max INTEGER DEFAULT 120,
                start_time TEXT DEFAULT '09:00',
                end_time TEXT DEFAULT '22:00',
                timezone TEXT DEFAULT 'Asia/Shanghai',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 插入默认配置（如果不存在）
        cursor.execute('SELECT COUNT(*) FROM auto_kick_config')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO auto_kick_config (enabled, check_interval_min, check_interval_max, start_time, end_time)
                VALUES (0, 90, 120, '09:00', '22:00')
            ''')

        # 踢人日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kick_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                email TEXT NOT NULL,
                reason TEXT,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS member_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                note TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(team_id, user_id),
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
            )
        ''')

        # 登录失败记录表 (fail2ban)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                username TEXT,
                success BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建索引加速查询
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_login_attempts_ip
            ON login_attempts(ip_address, created_at)
        ''')

        conn.commit()


class Team:
    @staticmethod
    def create(name, account_id, access_token, organization_id=None, email=None):
        """创建新 Team（不自动生成密钥,需要手动生成）"""
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO teams (name, account_id, access_token, organization_id, email)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, account_id, access_token, organization_id, email))
            team_id = cursor.lastrowid

            return team_id
    
    @staticmethod
    def get_all():
        """获取所有 Teams"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teams ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_by_id(team_id):
        """根据 ID 获取 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_organization_id(organization_id):
        """根据 organization_id 获取 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM teams WHERE organization_id = ?', (organization_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_token(team_id, access_token):
        """更新 Team 的 access_token，并重置错误计数"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE teams
                SET access_token = ?, 
                    token_error_count = 0,
                    token_status = 'active',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (access_token, team_id))

    @staticmethod
    def update_team_info(team_id, name=None, account_id=None, access_token=None, email=None):
        """更新 Team 的完整信息"""
        with get_db() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            if name is not None:
                updates.append('name = ?')
                params.append(name)
            if account_id is not None:
                updates.append('account_id = ?')
                params.append(account_id)
            if access_token is not None:
                updates.append('access_token = ?')
                params.append(access_token)
            if email is not None:
                updates.append('email = ?')
                params.append(email)

            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(team_id)
                sql = f"UPDATE teams SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql, params)

    @staticmethod
    def update_subscription_info(team_id, active_start, active_until):
        """更新 Team 的订阅时间信息"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE teams
                SET active_start = ?, 
                    active_until = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (active_start, active_until, team_id))

    @staticmethod
    def update_member_count(team_id, count):
        """更新 Team 的成员数量"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE teams
                SET member_count = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (count, team_id))

    @staticmethod
    def delete(team_id):
        """删除 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM teams WHERE id = ?', (team_id,))

    @staticmethod
    def get_available_teams():
        """获取所有未满员的 Team (轮询机制: 按最后邀请时间排序，最久未使用的优先)"""
        teams = Team.get_all()
        available = []
        for team in teams:
            invitations = Invitation.get_by_team(team['id'])
            member_count = len({inv['email'] for inv in invitations if inv['status'] == 'success'})
            if member_count < 4:
                team_copy = dict(team)
                team_copy['member_count'] = member_count
                available.append(team_copy)

        # 排序逻辑：
        # 1. 优先选择从未使用过的team (last_invite_at is None)
        # 2. 其次按最后邀请时间从早到晚排序（最久未使用的优先）
        # 3. 同等条件下按id排序
        available.sort(key=lambda item: (
            item.get('last_invite_at') is not None,  # None排在前面
            item.get('last_invite_at') or '',  # None转为空字符串
            item['id']
        ))
        return available

    @staticmethod
    def update_last_invite(team_id):
        """更新Team的最后邀请时间"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE teams
                SET last_invite_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (team_id,))
    
    @staticmethod
    def increment_token_error(team_id):
        """增加token错误计数，如果达到5次则标记为expired"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE teams
                SET token_error_count = token_error_count + 1,
                token_status = CASE 
                    WHEN token_error_count + 1 >= 5 THEN 'expired'
                    ELSE token_status
                END,
                updated_at = CURRENT_TIMESTAMP
            ''', (team_id,))
            
            # 返回更新后的错误计数
            cursor.execute('SELECT token_error_count, token_status FROM teams WHERE id = ?', (team_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def reset_token_error(team_id):
        """重置token错误计数（当token更新或请求成功时）"""
        with get_db() as conn:
            cursor = conn.cursor()

            # 获取检查成员的错误状态，判断是否应该保持expired
            cursor.execute('''
                SELECT member_check_error_count, member_check_first_error_at
                FROM teams WHERE id = ?
            ''', (team_id,))
            row = cursor.fetchone()

            if row:
                member_check_count = row[0] or 0
                first_error_at = row[1]

                # 判断检查成员那边是否过期（10分钟内>3次）
                member_check_expired = False
                if first_error_at and member_check_count > 3:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    first_error_dt = datetime.fromisoformat(first_error_at.replace('Z', '+00:00'))
                    if first_error_dt.tzinfo is None:
                        first_error_dt = first_error_dt.replace(tzinfo=timezone.utc)
                    time_diff = (now - first_error_dt).total_seconds()
                    # 10分钟内才算过期
                    if time_diff <= 600:
                        member_check_expired = True

                # 只有当检查成员那边也没过期时，才设置为active
                if not member_check_expired:
                    cursor.execute('''
                        UPDATE teams
                        SET token_error_count = 0,
                        token_status = 'active',
                        updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (team_id,))
                else:
                    # 检查成员那边已经标记为expired，保持expired状态
                    cursor.execute('''
                        UPDATE teams
                        SET token_error_count = 0,
                        updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (team_id,))
            else:
                # 没有记录，直接重置
                cursor.execute('''
                    UPDATE teams
                    SET token_error_count = 0,
                    token_status = 'active',
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (team_id,))

    @staticmethod
    def increment_member_check_error(team_id):
        """增加检查成员时的token错误计数（10分钟内超过3次则标记为expired）"""
        with get_db() as conn:
            cursor = conn.cursor()

            # 获取当前状态
            cursor.execute('''
                SELECT member_check_error_count, member_check_first_error_at
                FROM teams WHERE id = ?
            ''', (team_id,))
            row = cursor.fetchone()

            if not row:
                return None

            current_count = row[0] or 0
            first_error_at = row[1]

            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)

            # 如果是第一次错误，或者距离第一次错误超过10分钟，重新开始计数
            if not first_error_at:
                # 第一次错误，不修改token_status
                cursor.execute('''
                    UPDATE teams
                    SET member_check_error_count = 1,
                    member_check_first_error_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (now.isoformat(), team_id))

                # 获取当前token_status（可能被邀请那边设置为expired）
                cursor.execute('SELECT token_status FROM teams WHERE id = ?', (team_id,))
                row = cursor.fetchone()
                current_status = row[0] if row else 'active'
                return {'member_check_error_count': 1, 'token_status': current_status}

            # 解析第一次错误时间
            first_error_dt = datetime.fromisoformat(first_error_at.replace('Z', '+00:00'))
            if first_error_dt.tzinfo is None:
                first_error_dt = first_error_dt.replace(tzinfo=timezone.utc)

            time_diff = (now - first_error_dt).total_seconds()

            # 如果超过10分钟，重置计数
            if time_diff > 600:  # 600秒 = 10分钟
                cursor.execute('''
                    UPDATE teams
                    SET member_check_error_count = 1,
                    member_check_first_error_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (now.isoformat(), team_id))

                # 获取当前token_status（可能被邀请那边设置为expired）
                cursor.execute('SELECT token_status FROM teams WHERE id = ?', (team_id,))
                row = cursor.fetchone()
                current_status = row[0] if row else 'active'
                return {'member_check_error_count': 1, 'token_status': current_status}

            # 10分钟内，增加计数
            new_count = current_count + 1

            # 只有超过3次（即第4次）才标记为过期
            if new_count > 3:
                cursor.execute('''
                    UPDATE teams
                    SET member_check_error_count = ?,
                    token_status = 'expired',
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_count, team_id))
                return {'member_check_error_count': new_count, 'token_status': 'expired'}
            else:
                # 未达到阈值，只更新计数，不修改token_status
                cursor.execute('''
                    UPDATE teams
                    SET member_check_error_count = ?,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_count, team_id))

                # 获取当前token_status
                cursor.execute('SELECT token_status FROM teams WHERE id = ?', (team_id,))
                row = cursor.fetchone()
                current_status = row[0] if row else 'active'
                return {'member_check_error_count': new_count, 'token_status': current_status}

    @staticmethod
    def reset_member_check_error(team_id):
        """重置检查成员的错误计数（当请求成功时）"""
        with get_db() as conn:
            cursor = conn.cursor()

            # 获取邀请成员的错误计数，判断是否应该保持expired状态
            cursor.execute('''
                SELECT token_error_count FROM teams WHERE id = ?
            ''', (team_id,))
            row = cursor.fetchone()
            invite_error_count = row[0] if row else 0

            # 只有当邀请成员错误计数也小于5时，才设置为active
            if invite_error_count < 5:
                cursor.execute('''
                    UPDATE teams
                    SET member_check_error_count = 0,
                    member_check_first_error_at = NULL,
                    token_status = 'active',
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (team_id,))
            else:
                # 邀请成员那边已经标记为expired，保持expired状态
                cursor.execute('''
                    UPDATE teams
                    SET member_check_error_count = 0,
                    member_check_first_error_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (team_id,))

    @staticmethod
    def get_token_status(team_id):
        """获取token状态"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT token_error_count, token_status FROM teams WHERE id = ?', (team_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_expired_teams():
        """获取所有token已过期的teams"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, token_error_count, token_status, created_at
                FROM teams
                WHERE token_status = 'expired'
                ORDER BY updated_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def delete_expired_teams():
        """批量删除所有token已过期的teams，返回删除的数量和详情"""
        expired_teams = Team.get_expired_teams()
        deleted_count = 0
        deleted_teams = []

        with get_db() as conn:
            cursor = conn.cursor()
            for team in expired_teams:
                try:
                    cursor.execute('DELETE FROM teams WHERE id = ?', (team['id'],))
                    deleted_count += 1
                    deleted_teams.append(team)
                except Exception as e:
                    print(f"删除Team {team['id']} 失败: {e}")

        return {
            'deleted_count': deleted_count,
            'deleted_teams': deleted_teams
        }


class AccessKey:
    @staticmethod
    def create(team_id=None, is_temp=False, temp_hours=0):
        """创建新的邀请码, team_id 可选 (将在使用时分配)"""
        key_code = secrets.token_urlsafe(KEY_LENGTH)
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO access_keys (team_id, key_code, is_temp, temp_hours)
                VALUES (?, ?, ?, ?)
            ''', (team_id, key_code, is_temp, temp_hours))
            return {
                'id': cursor.lastrowid,
                'key_code': key_code
            }

    @staticmethod
    def assign_team(key_id, team_id):
        """在邀请码首次使用时绑定 Team"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE access_keys
                SET team_id = ?
                WHERE id = ?
            ''', (team_id, key_id))

    @staticmethod
    def get_all():
        """获取所有密钥"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ak.*,
                       t.name as team_name,
                       (SELECT COUNT(*) FROM invitations WHERE key_id = ak.id AND status = 'success') as usage_count
                FROM access_keys ak
                LEFT JOIN teams t ON ak.team_id = t.id
                WHERE ak.is_cancelled = 0
                ORDER BY ak.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_code(key_code):
        """根据密钥获取信息"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ak.*,
                       (SELECT COUNT(*) FROM invitations WHERE key_id = ak.id) as usage_count
                FROM access_keys ak
                WHERE ak.key_code = ? AND ak.is_cancelled = 0
            ''', (key_code,))
            row = cursor.fetchone()
            return dict(row) if row else None



    @staticmethod
    def cancel(key_id):
        """取消邀请码"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE access_keys
                SET is_cancelled = 1
                WHERE id = ?
            ''', (key_id,))

    @staticmethod
    def delete(key_id):
        """删除邀请码"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM access_keys WHERE id = ?', (key_id,))


class Invitation:
    @staticmethod
    def create(team_id, email, key_id=None, user_id=None, invite_id=None,
               status='pending', is_temp=False, temp_expire_at=None):
        """创建邀请记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO invitations (team_id, key_id, email, user_id, invite_id,
                                        status, is_temp, temp_expire_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (team_id, key_id, email, user_id, invite_id, status, is_temp, temp_expire_at))
            return cursor.lastrowid

    @staticmethod
    def get_by_team(team_id):
        """获取 Team 的所有邀请"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM invitations
                WHERE team_id = ?
                ORDER BY created_at DESC
            ''', (team_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all():
        """获取所有邀请"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.*, t.name as team_name
                FROM invitations i
                JOIN teams t ON i.team_id = t.id
                ORDER BY i.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all_emails_by_team(team_id):
        """获取 Team 的所有已邀请邮箱列表（包括所有状态，避免误踢pending成员）"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT email FROM invitations
                WHERE team_id = ?
            ''', (team_id,))
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def get_success_count_by_team(team_id):
        """获取 Team 的成功邀请数量（用于判断Team是否已满）"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(DISTINCT email) FROM invitations
                WHERE team_id = ? AND status = 'success'
            ''', (team_id,))
            return cursor.fetchone()[0]

    @staticmethod
    def get_temp_expired():
        """获取所有已过期的临时邀请（使用UTC时间比较）"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM invitations
                WHERE is_temp = 1
                  AND is_confirmed = 0
                  AND temp_expire_at IS NOT NULL
                  AND datetime(temp_expire_at) < datetime('now')
                ORDER BY temp_expire_at
            ''')
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def confirm(invitation_id):
        """确认邀请(管理员取消自动踢出)"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE invitations
                SET is_confirmed = 1
                WHERE id = ?
            ''', (invitation_id,))

    @staticmethod
    def update_user_id(invitation_id, user_id):
        """更新邀请的 user_id"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE invitations
                SET user_id = ?
                WHERE id = ?
            ''', (user_id, invitation_id,))

    @staticmethod
    def get_teams_by_email(email):
        """通过邮箱查找该成员可能所在的所有Team ID列表"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT team_id
                FROM invitations
                WHERE LOWER(email) = LOWER(?)
                  AND status = 'success'
                ORDER BY created_at DESC
            ''', (email,))
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def delete_by_email(team_id, email):
        """删除指定team中指定email的邀请记录（线程安全版本，带重试机制）"""
        def _delete():
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM invitations
                    WHERE team_id = ? AND LOWER(email) = LOWER(?)
                ''', (team_id, email))
                return cursor.rowcount > 0

        return execute_with_retry(_delete)

    @staticmethod
    def get_by_user_id(team_id, user_id):
        """根据user_id获取邀请记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM invitations
                WHERE team_id = ? AND user_id = ?
                LIMIT 1
            ''', (team_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None


class AutoKickConfig:
    @staticmethod
    def get():
        """获取配置"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM auto_kick_config LIMIT 1')
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update(enabled=None, check_interval_min=None, check_interval_max=None,
               start_time=None, end_time=None):
        """更新配置"""
        with get_db() as conn:
            cursor = conn.cursor()

            updates = []
            params = []

            if enabled is not None:
                updates.append('enabled = ?')
                params.append(enabled)
            if check_interval_min is not None:
                updates.append('check_interval_min = ?')
                params.append(check_interval_min)
            if check_interval_max is not None:
                updates.append('check_interval_max = ?')
                params.append(check_interval_max)
            if start_time is not None:
                updates.append('start_time = ?')
                params.append(start_time)
            if end_time is not None:
                updates.append('end_time = ?')
                params.append(end_time)

        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            sql = f"UPDATE auto_kick_config SET {', '.join(updates)}"
            cursor.execute(sql, params)


class MemberNote:
    @staticmethod
    def get(team_id, user_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT note FROM member_notes WHERE team_id = ? AND user_id = ?', (team_id, user_id))
            row = cursor.fetchone()
            return row[0] if row else None

    @staticmethod
    def set(team_id, user_id, note):
        def _exec():
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO member_notes (team_id, user_id, note, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(team_id, user_id)
                    DO UPDATE SET note = excluded.note, updated_at = CURRENT_TIMESTAMP
                ''', (team_id, user_id, note))
        return execute_with_retry(_exec)


class KickLog:
    @staticmethod
    def create(team_id, user_id, email, reason, success=True, error_message=None):
        """创建踢人日志（线程安全版本，带重试机制）"""
        def _create():
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO kick_logs (team_id, user_id, email, reason, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (team_id, user_id, email, reason, success, error_message))
                return cursor.lastrowid
        
        return execute_with_retry(_create)

    @staticmethod
    def get_all(limit=100):
        """获取所有踢人日志"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT k.*, t.name as team_name
                FROM kick_logs k
                JOIN teams t ON k.team_id = t.id
                ORDER BY k.created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_by_team(team_id, limit=50):
        """获取指定 Team 的踢人日志"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM kick_logs
                WHERE team_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (team_id, limit))
            return [dict(row) for row in cursor.fetchall()]


class LoginAttempt:
    """登录尝试记录 (fail2ban)"""

    @staticmethod
    def record(ip_address, username=None, success=False):
        """记录登录尝试"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO login_attempts (ip_address, username, success)
                VALUES (?, ?, ?)
            ''', (ip_address, username, success))

    @staticmethod
    def get_recent_failures(ip_address, minutes=30):
        """获取最近 N 分钟内的失败次数"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM login_attempts
                WHERE ip_address = ?
                  AND success = 0
                  AND created_at > datetime('now', '-' || ? || ' minutes')
            ''', (ip_address, minutes))
            row = cursor.fetchone()
            return row[0] if row else 0

    @staticmethod
    def is_blocked(ip_address, max_attempts=5, minutes=30):
        """检查 IP 是否被封禁"""
        failures = LoginAttempt.get_recent_failures(ip_address, minutes)
        return failures >= max_attempts

    @staticmethod
    def cleanup_old_records(days=7):
        """清理旧记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM login_attempts
                WHERE created_at < datetime('now', '-' || ? || ' days')
            ''', (days,))

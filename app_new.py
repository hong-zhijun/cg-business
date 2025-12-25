"""
ChatGPT Team 自动邀请系统 - 主应用
"""
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from curl_cffi import requests as cf_requests
import json
import sqlite3
from functools import wraps
from database import init_db, Team, AccessKey, Invitation, AutoKickConfig, KickLog, LoginAttempt, MemberNote, Source
from datetime import datetime, timedelta
import time
import pytz
from config import *
from auto_kick_service import auto_kick_service
import threading
from database import SystemConfig
import mail_service


def convert_to_beijing_time(timestamp_str):
    """
    将 UTC 时间字符串转换为北京时间字符串
    输入格式支持:
    1. ISO8601 (e.g., '2023-10-27T10:00:00Z', '2023-10-27T10:00:00+00:00')
    2. Unix Timestamp (int/float)
    
    返回格式: 'YYYY-MM-DD HH:MM:SS'
    """
    if not timestamp_str:
        return None
        
    try:
        # 如果是数字（时间戳）
        if isinstance(timestamp_str, (int, float)):
            dt = datetime.fromtimestamp(timestamp_str, pytz.UTC)
        else:
            # 如果是字符串
            # 处理 Z 结尾
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str.replace('Z', '+00:00')
            
            dt = datetime.fromisoformat(timestamp_str)
            # 如果没有时区信息，默认为 UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
                
        # 转换为北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        dt_beijing = dt.astimezone(beijing_tz)
        
        return dt_beijing.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"时间转换错误: {e} (Input: {timestamp_str})")
        return timestamp_str  # 转换失败返回原值


app = Flask(__name__)
app.secret_key = SECRET_KEY

# 初始化数据库
init_db()


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated_function


def invite_to_team(access_token, account_id, email, team_id=None):
    """调用 ChatGPT API 邀请成员"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"
    
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "content-type": "application/json",
        "oai-device-id": "a9c9e9a0-f72d-4fbc-800e-2d0e1e3c3b54",
        "oai-language": "zh-CN",
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    payload = {
        "email_addresses": [email],
        "role": "standard-user",
        "resend_emails": False
    }
    
    try:
        response = cf_requests.post(url, headers=headers, json=payload, impersonate="chrome110")
        
        if response.status_code in [200, 201]:
            data = response.json()
            invites = data.get('account_invites', [])
            # 成功时重置错误计数
            if team_id:
                Team.reset_token_error(team_id)
            if invites:
                return {"success": True, "invite_id": invites[0].get('id')}
            return {"success": True}
        elif response.status_code == 401:
            # 检测到401，增加错误计数
            if team_id:
                status = Team.increment_token_error(team_id)
                if status and status['token_status'] == 'expired':
                    return {
                        "success": False, 
                        "error": "Token已过期，请更新该Team的Token",
                        "error_code": "TOKEN_EXPIRED",
                        "status_code": 401
                    }
            return {"success": False, "error": response.text, "status_code": response.status_code}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def cancel_invite_from_openai(access_token, account_id, email):
    """调用 ChatGPT API 撤销邀请"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"
    
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "content-type": "application/json",
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    payload = {
        "email_address": email
    }
    
    try:
        response = cf_requests.delete(url, headers=headers, json=payload, impersonate="chrome110")
        
        if response.status_code in [200, 204]:
            return {"success": True}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_team_subscription(access_token, account_id):
    """获取 Team 订阅信息"""
    url = f"https://chatgpt.com/backend-api/subscriptions?account_id={account_id}"
    
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "content-type": "application/json",
        "oai-device-id": "a9c9e9a0-f72d-4fbc-800e-2d0e1e3c3b54",
        "oai-language": "zh-CN",
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True, 
                "active_start": convert_to_beijing_time(data.get('active_start')),
                "active_until": convert_to_beijing_time(data.get('active_until'))
            }
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 用户端路由 ====================

@app.route('/')
def index():
    """用户首页"""
    return render_template('user.html')


@app.route('/api/join', methods=['POST'])
def join_team():
    """用户加入 Team (自动重试所有可用Team直到成功)"""
    data = request.json
    email = data.get('email', '').strip()
    key_code = data.get('key_code', '').strip()

    if not email or not key_code:
        return jsonify({"success": False, "error": "请输入邮箱和访问密钥"}), 400

    # 验证密钥
    key_info = AccessKey.get_by_code(key_code)
    
    if not key_info:
        return jsonify({"success": False, "error": "无效的访问密钥"}), 400

    # 检查邀请码是否绑定了特定Team
    assigned_team_id = key_info.get('team_id')
    
    if assigned_team_id:
        # 邀请码绑定了特定Team，只能加入该Team
        team = Team.get_by_id(assigned_team_id)
        if not team:
            return jsonify({"success": False, "error": "该邀请码绑定的Team不存在"}), 400
        
        if team.get('token_status') == 'expired':
            return jsonify({"success": False, "error": "该Team的Token已过期，请联系管理员"}), 400
        
        # 检查Team是否已满
        invited_count = Invitation.get_success_count_by_team(team['id'])
        if invited_count >= 4:
            return jsonify({"success": False, "error": f"{team['name']} 已达到人数上限"}), 400
        
        # 只尝试这一个Team
        available_teams = [team]
        max_attempts = 1
    else:
        # 邀请码未绑定Team，走智能分配逻辑
        # 1. 获取所有Team（排除token过期的）
        all_teams = Team.get_all()
        all_teams = [t for t in all_teams if t.get('token_status') != 'expired']

        if not all_teams:
            return jsonify({"success": False, "error": "当前无可用 Team，请联系管理员"}), 400

        # 2. 只选择通过我们系统邀请的成员数 < 4 的Team
        available_teams = []
        for team in all_teams:
            invited_count = Invitation.get_success_count_by_team(team['id'])
            if invited_count < 4:
                team['invited_count'] = invited_count  # 保存邀请数
                available_teams.append(team)

        if not available_teams:
            return jsonify({"success": False, "error": "所有 Team 名额已满，请联系管理员"}), 400

        # 3. 按最近邀请时间排序（最近成功的在前，命中率更高）
        available_teams.sort(key=lambda t: t.get('last_invite_at') or '', reverse=True)
        
        # 最多尝试3个Team
        max_attempts = 3

    tried_teams = []
    last_error = None

    # 遍历可用Team，最多尝试3次
    for i, team in enumerate(available_teams):
        if i >= max_attempts:
            break  # 限制最多尝试3次

        tried_teams.append(team['name'])

        # 检查实际成员数（API获取）
        members_result = get_team_members(team['access_token'], team['account_id'], team['id'])
        if not members_result['success']:
            last_error = f"无法获取{team['name']}成员列表"
            continue

        members = members_result.get('members', [])
        non_owner_members = [m for m in members if m.get('role') != 'account-owner']

        # 实际成员数已满，跳过此Team
        if len(non_owner_members) >= 4:
            last_error = f"{team['name']}实际成员已满"
            continue

        # 检查该邮箱是否已在此Team中
        member_emails = [m.get('email', '').lower() for m in members]
        if email.lower() in member_emails:
            # 已经是成员，直接返回成功
            Invitation.create(
                team_id=team['id'],
                email=email,
                key_id=key_info['id'],
                status='success',
                is_temp=False
            )
            AccessKey.cancel(key_info['id'])
            return jsonify({
                "success": True,
                "message": "✅ 您已是团队成员！",
                "team_name": team['name'],
                "email": email
            })

        # 尝试邀请
        result = invite_to_team(
            team['access_token'],
            team['account_id'],
            email,
            team['id']
        )

        if result['success']:
            # 邀请成功！计算过期时间
            temp_expire_at = None
            if key_info['is_temp'] and key_info['temp_hours'] > 0:
                now = datetime.utcnow()
                temp_expire_at = (now + timedelta(hours=key_info['temp_hours'])).strftime('%Y-%m-%d %H:%M:%S')

            # 记录邀请
            Invitation.create(
                team_id=team['id'],
                email=email,
                key_id=key_info['id'],
                invite_id=result.get('invite_id'),
                status='success',
                is_temp=key_info['is_temp'],
                temp_expire_at=temp_expire_at
            )

            # 邀请码使用一次后立即取消
            AccessKey.cancel(key_info['id'])
            Team.update_last_invite(team['id'])

            message = f"🎉 加入成功！\n\n📧 请立即查收邮箱 {email} 的邀请邮件并确认加入。\n\n💡 提示：邮件可能在垃圾箱中，请注意查看。"
            if key_info['is_temp'] and key_info['temp_hours'] > 0:
                message += f"\n\n⏰ 注意：这是一个 {key_info['temp_hours']} 小时临时邀请，到期后如果管理员未确认，将自动踢出。"

            if len(tried_teams) > 1:
                message += f"\n\n💡 尝试了 {len(tried_teams)} 个Team后成功"

            return jsonify({
                "success": True,
                "message": message,
                "team_name": team['name'],
                "email": email
            })
        else:
            # 邀请失败，验证是否实际成功
            import time
            time.sleep(1)

            # 检查pending列表
            pending_result = get_pending_invites(team['access_token'], team['account_id'])
            if pending_result['success']:
                pending_emails = [inv.get('email_address', '').lower() for inv in pending_result.get('invites', [])]
                if email.lower() in pending_emails:
                    # 实际已成功
                    temp_expire_at = None
                    if key_info['is_temp'] and key_info['temp_hours'] > 0:
                        now = datetime.utcnow()
                        temp_expire_at = (now + timedelta(hours=key_info['temp_hours'])).strftime('%Y-%m-%d %H:%M:%S')

                    Invitation.delete_by_email(team['id'], email)
                    Invitation.create(
                        team_id=team['id'],
                        email=email,
                        key_id=key_info['id'],
                        invite_id=None,
                        status='success',
                        is_temp=key_info['is_temp'],
                        temp_expire_at=temp_expire_at
                    )
                    AccessKey.cancel(key_info['id'])
                    Team.update_last_invite(team['id'])

                    message = f"🎉 加入成功！（验证确认）\n\n📧 请立即查收邮箱 {email} 的邀请邮件并确认加入。"
                    if key_info['is_temp'] and key_info['temp_hours'] > 0:
                        message += f"\n\n⏰ 注意：这是一个 {key_info['temp_hours']} 小时临时邀请。"

                    return jsonify({
                        "success": True,
                        "message": message,
                        "team_name": team['name'],
                        "email": email
                    })

            # 确实失败，记录错误并尝试下一个Team
            last_error = f"{team['name']}: {result.get('error', '未知错误')}"
            continue

    # 所有Team都试过了，仍然失败
    return jsonify({
        "success": False,
        "error": f"尝试了 {len(tried_teams)} 个Team均失败\n最后错误: {last_error}\n尝试的Team: {', '.join(tried_teams)}"
    }), 500


# ==================== 管理员端路由 ====================

@app.route('/admin')
def admin_page():
    """管理员页面"""
    if not session.get('is_admin'):
        return render_template('admin_login.html')
    return render_template('admin_new.html')


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录 (带 fail2ban 防护)"""
    data = request.json
    password = data.get('password', '')
    ip_address = request.remote_addr

    # 检查 IP 是否被封禁
    if LoginAttempt.is_blocked(ip_address, max_attempts=5, minutes=30):
        return jsonify({
            "success": False,
            "error": "登录失败次数过多,请 30 分钟后再试"
        }), 429

    if password == ADMIN_PASSWORD:
        # 登录成功,记录
        LoginAttempt.record(ip_address, 'admin', success=True)
        session['is_admin'] = True
        return jsonify({"success": True})
    else:
        # 登录失败,记录
        LoginAttempt.record(ip_address, 'admin', success=False)

        # 获取剩余尝试次数
        failures = LoginAttempt.get_recent_failures(ip_address, minutes=30)
        remaining = 5 - failures

        if remaining > 0:
            return jsonify({
                "success": False,
                "error": f"密码错误,还剩 {remaining} 次尝试机会"
            }), 401
        else:
            return jsonify({
                "success": False,
                "error": "登录失败次数过多,已被封禁 30 分钟"
            }), 429


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """管理员登出"""
    session.pop('is_admin', None)
    return jsonify({"success": True})


@app.route('/api/admin/teams', methods=['GET'])
@admin_required
def get_teams():
    """获取所有 Teams (新逻辑: 读取数据库成员数，不实时查询)"""
    teams = Team.get_all()

    # 为每个 Team 添加成员信息
    for team in teams:
        # 从数据库读取 member_count，如果没有则默认为0
        # 注意：member_count 需要在 create/update token 以及 get_members 时更新
        member_count = team.get('member_count')
        if member_count is None:
            member_count = 0
            
        team['member_count'] = member_count
        
        # 仍然获取邀请记录，以防前端其他地方需要
        invitations = Invitation.get_by_team(team['id'])
        team['invitations'] = invitations
        
        team['available_slots'] = max(0, 4 - team['member_count'])

    return jsonify({"success": True, "teams": teams})


@app.route('/api/admin/teams', methods=['POST'])
@admin_required
def create_team():
    """创建新 Team（从 session JSON）- 支持自动识别并更新已存在的组织"""
    data = request.json

    # 解析 session JSON
    session_data = data.get('session_data')
    if isinstance(session_data, str):
        try:
            session_data = json.loads(session_data)
        except:
            return jsonify({"success": False, "error": "无效的 JSON 格式"}), 400

    name = data.get('name', '').strip()
    if not name:
        # 使用邮箱作为默认名称
        name = session_data.get('user', {}).get('email', 'Unknown Team')

    account_id = session_data.get('account', {}).get('id')
    access_token = session_data.get('accessToken')
    organization_id = session_data.get('account', {}).get('organizationId')
    email = session_data.get('user', {}).get('email')

    if not account_id or not access_token:
        return jsonify({"success": False, "error": "缺少必要的账户信息"}), 400

    try:
        # 检查是否已存在相同的 organization_id
        existing_team = None
        if organization_id:
            existing_team = Team.get_by_organization_id(organization_id)

        target_team_id = None
        message = ""
        is_updated = False

        if existing_team:
            # 已存在,更新 Token 和其他信息
            Team.update_team_info(
                existing_team['id'],
                name=name,
                account_id=account_id,
                access_token=access_token,
                email=email
            )
            target_team_id = existing_team['id']
            message = f"检测到已存在的组织 (ID: {organization_id}),已自动更新 Token 和信息"
            is_updated = True
        else:
            # 不存在,创建新 Team
            team_id = Team.create(name, account_id, access_token, organization_id, email)
            target_team_id = team_id
            message = "Team 创建成功"
            is_updated = False

        # 获取并更新订阅信息
        sub_info = get_team_subscription(access_token, account_id)
        if sub_info['success']:
            Team.update_subscription_info(target_team_id, sub_info['active_start'], sub_info['active_until'])

        # 获取并更新成员数量
        members_result = get_team_members(access_token, account_id, target_team_id)
        if members_result['success']:
            members = members_result.get('members', [])
            non_owner_members = [m for m in members if m.get('role') != 'account-owner']
            Team.update_member_count(target_team_id, len(non_owner_members))

        return jsonify({
            "success": True,
            "team_id": target_team_id,
            "message": message,
            "updated": is_updated
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/<int:team_id>', methods=['DELETE'])
@admin_required
def delete_team(team_id):
    """删除 Team"""
    try:
        Team.delete(team_id)
        return jsonify({"success": True, "message": "Team 删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/delete-expired', methods=['POST'])
@admin_required
def delete_expired_teams():
    """批量删除所有token已过期的teams"""
    try:
        result = Team.delete_expired_teams()
        deleted_count = result['deleted_count']
        deleted_teams = result['deleted_teams']

        if deleted_count > 0:
            team_names = [team['name'] for team in deleted_teams]
            return jsonify({
                "success": True,
                "message": f"成功删除 {deleted_count} 个Token已过期的Team",
                "deleted_count": deleted_count,
                "deleted_teams": team_names
            })
        else:
            return jsonify({
                "success": True,
                "message": "没有Token已过期的Team需要删除",
                "deleted_count": 0
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/<int:team_id>/token', methods=['PUT'])
@admin_required
def update_team_token(team_id):
    """更新 Team 的 Token"""
    data = request.json
    session_data = data.get('session_data')
    
    if isinstance(session_data, str):
        try:
            session_data = json.loads(session_data)
        except:
            return jsonify({"success": False, "error": "无效的 JSON 格式"}), 400
    
    access_token = session_data.get('accessToken')
    if not access_token:
        return jsonify({"success": False, "error": "缺少 accessToken"}), 400
    
    try:
        Team.update_token(team_id, access_token)
        
        # 更新后顺便刷新一下成员数量和订阅信息
        team = Team.get_by_id(team_id)
        if team:
            # 刷新成员数
            members_result = get_team_members(access_token, team['account_id'], team_id)
            if members_result['success']:
                members = members_result.get('members', [])
                non_owner_members = [m for m in members if m.get('role') != 'account-owner']
                Team.update_member_count(team_id, len(non_owner_members))
                
            # 刷新订阅信息
            sub_info = get_team_subscription(access_token, team['account_id'])
            if sub_info['success']:
                Team.update_subscription_info(team_id, sub_info['active_start'], sub_info['active_until'])
        
        return jsonify({"success": True, "message": "Token 更新成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/<int:team_id>/note', methods=['PUT'])
@admin_required
def update_team_note(team_id):
    """更新 Team 的备注"""
    data = request.json
    note = data.get('note', '')
    
    try:
        Team.update_note(team_id, note)
        return jsonify({"success": True, "message": "备注更新成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/<int:team_id>/public', methods=['PUT'])
@admin_required
def update_team_public_status(team_id):
    """更新 Team 的公开状态"""
    data = request.json
    is_public = data.get('is_public', False)
    
    try:
        Team.update_team_info(team_id, is_public=is_public)
        return jsonify({"success": True, "message": "状态更新成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/search', methods=['GET'])
@admin_required
def search_teams_by_email():
    """通过邮箱搜索包含该成员的Team列表"""
    email = request.args.get('email', '').strip()
    
    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400
    
    # 从 invitations 表查询包含该邮箱的 team_id 列表
    team_ids = Invitation.get_teams_by_email(email)
    
    if not team_ids:
        return jsonify({"success": True, "teams": [], "message": f"未找到包含 {email} 的Team"})
    
    # 获取这些team的详细信息
    teams = []
    for team_id in team_ids:
        team = Team.get_by_id(team_id)
        if team:
            teams.append(team)
    
    return jsonify({"success": True, "teams": teams, "count": len(teams)})


@app.route('/api/admin/stats/total-members', methods=['GET'])
@admin_required
def get_total_members_count():
    """统计所有Team的成员总数（不包括所有者）和Team总数"""
    try:
        total_members = MemberNote.get_total_count()
        total_teams = Team.get_total_count()
        
        return jsonify({
            "success": True, 
            "total_members": total_members,
            "total_teams": total_teams
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/teams/<int:team_id>/token-export', methods=['GET'])
@admin_required
def export_team_token(team_id):
    """导出 Team 的 Token 信息"""
    try:
        team = Team.get_by_id(team_id)
        if not team:
            return jsonify({"success": False, "error": "Team 不存在"}), 404

        return jsonify({
            "success": True,
            "access_token": team['access_token'],
            "account_id": team['account_id'],
            "organization_id": team.get('organization_id'),
            "name": team['name'],
            "email": team.get('email')
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/keys', methods=['GET'])
@admin_required
def get_all_keys():
    """获取所有邀请码"""
    try:
        keys = AccessKey.get_all()
        return jsonify({"success": True, "keys": keys})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/keys', methods=['POST'])
@admin_required
def create_invite_key():
    """创建新的邀请码 (不绑定特定 Team),支持批量生成"""
    data = request.json
    team_id_raw = data.get('team_id')
    team_id = None
    is_temp = data.get('is_temp', False)
    temp_hours = data.get('temp_hours', 24) if is_temp else 0
    count = data.get('count', 1)  # 批量生成数量,默认1个

    try:
        # 验证数量
        if not isinstance(count, int) or count < 1 or count > 100:
            return jsonify({"success": False, "error": "数量必须在 1-100 之间"}), 400

        if team_id_raw not in (None, '', 'null'):
            try:
                team_id = int(team_id_raw)
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "无效的 team_id"}), 400

            team = Team.get_by_id(team_id)
            if not team:
                return jsonify({"success": False, "error": "Team 不存在"}), 404

        # 批量生成邀请码
        results = []
        for _ in range(count):
            result = AccessKey.create(team_id=team_id, is_temp=is_temp, temp_hours=temp_hours)
            results.append(result)

        # 返回生成的邀请码列表
        return jsonify({
            "success": True,
            "count": count,
            "keys": results,  # 返回完整的key对象
            "message": f"成功生成 {count} 个邀请码" if count > 1 else "邀请码创建成功"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/keys/<int:key_id>', methods=['DELETE'])
@admin_required
def delete_invite_key(key_id):
    """删除邀请码"""
    try:
        AccessKey.delete(key_id)
        return jsonify({"success": True, "message": "邀请码删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/invitations', methods=['GET'])
@admin_required
def get_invitations():
    """获取所有邀请记录"""
    invitations = Invitation.get_all()
    return jsonify({"success": True, "invitations": invitations})


@app.route('/api/admin/invitations/<int:invitation_id>/confirm', methods=['POST'])
@admin_required
def confirm_invitation(invitation_id):
    """确认邀请 (取消自动踢出)"""
    try:
        Invitation.confirm(invitation_id)
        return jsonify({"success": True, "message": "已确认该邀请,不会自动踢出"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def get_team_members(access_token, account_id, team_id=None):
    """获取 Team 成员列表"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/users"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        if response.status_code == 200:
            data = response.json()
            # 成功时重置检查成员的错误计数
            if team_id:
                Team.reset_member_check_error(team_id)
            return {"success": True, "members": data.get('items', [])}
        elif response.status_code == 401:
            # 检测到401，增加检查成员的错误计数（10分钟内超过3次才标记为过期）
            if team_id:
                status = Team.increment_member_check_error(team_id)
                if status and status['token_status'] == 'expired':
                    return {
                        "success": False,
                        "error": "Token已过期（检查成员失败次数过多），请更新该Team的Token",
                        "error_code": "TOKEN_EXPIRED",
                        "status_code": 401
                    }
            return {"success": False, "error": response.text, "status_code": response.status_code}
        else:
            return {"success": False, "error": response.text, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pending_invites(access_token, account_id):
    """获取待处理的邀请列表"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome110")
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "invites": data.get('items', [])}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def kick_member(access_token, account_id, user_id):
    """踢出成员"""
    url = f"https://chatgpt.com/backend-api/accounts/{account_id}/users/{user_id}"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "chatgpt-account-id": account_id,
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/admin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = cf_requests.delete(url, headers=headers, impersonate="chrome110")
        if response.status_code == 200:
            return {"success": True}
        else:
            return {"success": False, "error": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route('/api/admin/teams/<int:team_id>/members', methods=['GET'])
@admin_required
def get_members(team_id):
    """获取 Team 成员列表 (从数据库查询，合并已加入和待邀请)"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 1. 获取已加入成员 (Status: 2)
    db_members = MemberNote.get_all(team_id)
    
    # 使用字典去重，key为小写邮箱
    merged_members = {}
    
    for member_data in db_members:
        # 构造返回对象
        member = {
            'id': member_data['user_id'],
            'user_id': member_data['user_id'],
            'email': member_data['email'],
            'role': member_data['role'],
            'note': member_data['note'],
            'source': member_data['source'],
            # 使用 join_time 如果存在，否则使用 updated_at
            'created': member_data.get('join_time'),
            'status': 2,  # 2-已加入
            'status_text': '已加入'
        }
        
        # 处理时间显示
        if member['created']:
             try:
                member['created_at'] = convert_to_beijing_time(member['created'])
             except:
                member['created_at'] = member['created']
        else:
             # 如果没有 join_time，尝试使用 updated_at
             member['created_at'] = convert_to_beijing_time(member_data['updated_at'])

        # 获取邀请信息 (补充 is_temp 等信息)
        invitation = Invitation.get_by_user_id(team_id, member['user_id'])
        if invitation:
            member['invitation_id'] = invitation['id']
            member['is_temp'] = invitation['is_temp']
            member['is_confirmed'] = invitation['is_confirmed']
            member['temp_expire_at'] = invitation['temp_expire_at']
        else:
            member['invitation_id'] = None
            member['is_temp'] = False
            member['is_confirmed'] = False
            member['temp_expire_at'] = None
            
        email_key = member['email'].strip().lower() if member['email'] else ''
        if email_key:
            merged_members[email_key] = member
        else:
            # 如果没有邮箱（极少情况），用user_id做key
            merged_members[member['user_id']] = member

    # 2. 获取待处理邀请 (Status: 1)
    invitations = Invitation.get_by_team(team_id)
    
    for inv in invitations:
        email = inv.get('email', '').strip().lower()
        if not email:
            continue
            
        # 如果该邮箱已经在 merged_members 中，说明已加入，跳过（以 MemberNote 为准）
        if email in merged_members:
            continue
            
        # 确定状态文本
        status_text = '已邀请'
        if inv.get('status') == 'success':
             status_text = '已发送邀请' # 但未同步到member_notes
        elif inv.get('status') == 'failed':
             status_text = '邀请失败'
        elif inv.get('status') == 'expired':
             status_text = '已过期'
        
        invite_obj = {
            'id': inv.get('user_id') or f"invite_{inv.get('id')}",
            'user_id': inv.get('user_id'),
            'email': inv.get('email'),
            'role': 'member', # 默认角色
            'note': '',
            'source': inv.get('source'),
            'created': inv.get('created_at'),
            'status': 1, # 1-已邀请/待进组
            'status_text': status_text,
            'invite_status': inv.get('status'),
            
            # 邀请相关字段
            'invitation_id': inv.get('id'),
            'is_temp': inv.get('is_temp'),
            'is_confirmed': inv.get('is_confirmed'),
            'temp_expire_at': inv.get('temp_expire_at')
        }
        
        # 处理时间
        if invite_obj['created']:
             try:
                invite_obj['created_at'] = convert_to_beijing_time(invite_obj['created'])
             except:
                invite_obj['created_at'] = invite_obj['created']
                
        merged_members[email] = invite_obj

    # 转为列表并按时间排序 (倒序)
    results = list(merged_members.values())
    
    def get_sort_time(x):
        t = x.get('created')
        if not t: return ''
        return str(t)

    results.sort(key=get_sort_time, reverse=True)

    return jsonify({"success": True, "members": results})


@app.route('/api/admin/teams/<int:team_id>/members/refresh', methods=['POST'])
@admin_required
def refresh_members(team_id):
    """刷新 Team 成员列表 (调用 OpenAI API 并同步到数据库)"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    result = get_team_members(team['access_token'], team['account_id'], team_id)

    if result['success']:
        members = result.get('members', [])
        
        # 更新数据库中的成员数量
        non_owner_members = [m for m in members if m.get('role') != 'account-owner']
        Team.update_member_count(team_id, len(non_owner_members))

        # 同步每个成员到 member_notes
        current_user_ids = []
        for member in members:
            user_id = member.get('id')
            if not user_id:
                continue
            
            current_user_ids.append(user_id)
            
            email = member.get('email')
            role = member.get('role')
            # API 返回的是 created_time (ISO 8601 string)，例如 "2025-12-11T07:45:52.666554Z"
            # 数据库需要的是 join_time (Unix timestamp int)
            created_time_str = member.get('created_time')
            join_time = None
            if created_time_str:
                try:
                    # 处理 Z 结尾
                    if created_time_str.endswith('Z'):
                        created_time_str = created_time_str.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(created_time_str)
                    join_time = int(dt.timestamp())
                except Exception as e:
                    print(f"Error parsing created_time: {e}")
                    # 如果解析失败，尝试使用 created 字段（旧版API）或当前时间
                    join_time = member.get('created')
            else:
                 join_time = member.get('created')

            MemberNote.sync_member(team_id, user_id, email, role, join_time)
            
        # 删除不在当前列表中的成员（即已退出的成员）
        MemberNote.delete_not_in(team_id, current_user_ids)
        
        # 同步清理失效的邀请记录 (修复成员已踢出但邀请记录占位的问题)
        current_emails = [m.get('email') for m in members if m.get('email')]
        Invitation.sync_invitations(team_id, current_emails)
            
        return jsonify({"success": True, "message": "成员列表已刷新"})
    else:
        return jsonify(result), result.get('status_code', 500)


@app.route('/api/admin/teams/<int:team_id>/members/<user_id>/note', methods=['PUT'])
@admin_required
def update_member_note(team_id, user_id):
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    data = request.json
    note = data.get('note', '')
    source = data.get('source')
    MemberNote.update_note_and_source(team_id, user_id, note, source)
    return jsonify({"success": True})


@app.route('/api/admin/teams/<int:team_id>/members/<user_id>/local-delete', methods=['DELETE'])
@admin_required
def local_delete_team_member(team_id, user_id):
    """仅从本地数据库删除成员记录，不调用OpenAI API"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 删除 member_notes 记录
    deleted = MemberNote.delete_by_user_id(team_id, user_id)
    
    # 尝试查找并删除可能的邀请记录（释放位置）
    # 需要先获取email，但如果MemberNote已经被删除了，可能拿不到
    # 所以这里只尝试做 Invitation 清理，不做强关联
    
    if deleted:
        return jsonify({"success": True, "message": "成员记录已从本地删除"})
    else:
        return jsonify({"success": False, "error": "未找到成员记录"}), 404


@app.route('/api/admin/teams/<int:team_id>/members/<user_id>', methods=['DELETE'])
@admin_required
def kick_team_member(team_id, user_id):
    """踢出 Team 成员"""
    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 获取成员信息
    members_result = get_team_members(team['access_token'], team['account_id'], team_id)
    if not members_result['success']:
        return jsonify({"success": False, "error": "无法获取成员列表"}), 500

    # 找到要踢的成员
    # 数据结构中 id 即为 user_id (例如: user-LtBJrah9f9r36s2Gm6Ft4jMD)
    member = next((m for m in members_result['members'] if m.get('id') == user_id), None)
    if not member:
        return jsonify({"success": False, "error": "成员不存在"}), 404

    # 执行踢人
    result = kick_member(team['access_token'], team['account_id'], user_id)

    if result['success']:
        # 从invitations表中删除记录，释放位置
        Invitation.delete_by_email(team_id, member.get('email', ''))

        # 记录日志
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=member.get('email', 'unknown'),
            reason='管理员手动踢出',
            success=True
        )
        return jsonify({"success": True, "message": "成员已踢出"})
    else:
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=member.get('email', 'unknown'),
            reason='管理员手动踢出',
            success=False,
            error_message=result.get('error')
        )
        return jsonify({"success": False, "error": result.get('error')}), 500


@app.route('/api/admin/teams/<int:team_id>/invitations', methods=['DELETE'])
@admin_required
def cancel_team_invitation(team_id):
    """取消/撤销邀请"""
    data = request.get_json()
    email = data.get('email_address')
    
    if not email:
        return jsonify({"success": False, "error": "邮箱不能为空"}), 400

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 1. 查找数据库中的邀请记录，获取 invite_id
    # 注意：invitation 表中可能没有 invite_id (如果是在我们系统之外邀请的，或者旧数据)
    # 但如果是我们系统发起的邀请，应该会有
    invitation = Invitation.get_by_email(team_id, email)
    
    # 2. 如果有 invite_id，尝试调用 OpenAI API 撤销
    api_success = False
    api_message = ""
    
    if invitation and invitation.get('invite_id'):
        result = cancel_invite_from_openai(team['access_token'], team['account_id'], email)
        if result['success']:
            api_success = True
            api_message = " (OpenAI API 同步撤销成功)"
        else:
            api_message = f" (OpenAI API 撤销失败: {result.get('error')})"
    else:
        # 如果没有 invite_id，尝试从 pending 列表中查找
        pending_result = get_pending_invites(team['access_token'], team['account_id'])
        if pending_result['success']:
            target_invite = next((inv for inv in pending_result.get('invites', []) 
                                if inv.get('email_address', '').lower() == email.lower()), None)
            if target_invite:
                result = cancel_invite_from_openai(team['access_token'], team['account_id'], email)
                if result['success']:
                    api_success = True
                    api_message = " (OpenAI API 同步撤销成功)"
                else:
                    api_message = f" (OpenAI API 撤销失败: {result.get('error')})"

    # 3. 无论 API 是否成功，都删除本地记录，释放名额
    Invitation.delete_by_email(team_id, email)
    
    return jsonify({
        "success": True, 
        "message": f"邀请已取消{api_message}"
    })


# ========== 满员预警逻辑封装 ==========
def check_and_send_team_full_warning(team_name, current_count, email):
    """
    检查并发送Team满员预警
    :param team_name: Team名称
    :param current_count: 当前成员数
    :param email: 新邀请的邮箱
    """
    # 检查是否开启预警，且当前人数为3（加上本次邀请即满员）
    warning_enabled = SystemConfig.get('team_full_warning_enabled') == 'true'
    if warning_enabled and current_count == 3:
        try:
            # 获取配置
            bark_server = SystemConfig.get('bark_server', 'https://api.day.app').rstrip('/')
            bark_key = SystemConfig.get('bark_key', '')
            template = SystemConfig.get('team_full_warning_template', 'Team [{team_name}] 即将满员！当前成员数: {current_count}, 新邀请: {email}')
            
            if bark_server and bark_key:
                # 替换模板变量
                message = template.format(
                    team_name=team_name,
                    current_count=current_count,
                    email=email
                )
                
                # 发送推送
                from urllib.parse import quote
                title = quote("ChatGPT Team 满员预警")
                content = quote(message)
                
                # 使用线程异步发送，避免阻塞邀请流程
                def send_warning():
                    try:
                        url = f"{bark_server}/{bark_key}/{title}/{content}"
                        cf_requests.get(url, impersonate="chrome110")
                    except Exception as e:
                        print(f"Warning push failed: {str(e)}")
                
                threading.Thread(target=send_warning, daemon=True).start()
        except Exception as e:
            print(f"Error in team warning logic: {str(e)}")

# ===================================

@app.route('/api/admin/teams/<int:team_id>/invite', methods=['POST'])
@admin_required
def admin_invite_member(team_id):
    """管理员直接邀请成员"""
    data = request.json
    email = data.get('email', '').strip()
    is_temp = data.get('is_temp', False)
    temp_hours = data.get('temp_hours', 24) if is_temp else 0

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 1. 先进行数据库层面的预判
    invited_emails = Invitation.get_all_emails_by_team(team_id)
    if len(invited_emails) >= 4:
        return jsonify({"success": False, "error": "该 Team 已达到人数上限 (4人)"}), 400

    # 检查该邮箱是否已被成功邀请 (本地检查)
    if email in invited_emails:
        return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400

    # 2. 实时调用 API 检查并同步最新状态 (Lazy Sync)
    members_result = get_team_members(team['access_token'], team['account_id'], team_id)
    
    if members_result['success']:
        # 获取最新成员列表
        members = members_result.get('members', [])
        non_owner_members = [m for m in members if m.get('role') != 'account-owner']
        current_count = len(non_owner_members)
        
        # 同步更新数据库
        Team.update_member_count(team_id, current_count)
        
        # 同步成员详情
        current_user_ids = []
        for member in members:
            user_id = member.get('id')
            if user_id:
                current_user_ids.append(user_id)
                email_val = member.get('email')
                role = member.get('role')
                created_time_str = member.get('created_time')
                join_time = member.get('created')
                if created_time_str:
                    try:
                        if created_time_str.endswith('Z'):
                            created_time_str = created_time_str.replace('Z', '+00:00')
                        dt = datetime.fromisoformat(created_time_str)
                        join_time = int(dt.timestamp())
                    except:
                        pass
                MemberNote.sync_member(team_id, user_id, email_val, role, join_time)
        
        # 清理失效数据
        MemberNote.delete_not_in(team_id, current_user_ids)
        current_emails = [m.get('email') for m in members if m.get('email')]
        Invitation.sync_invitations(team_id, current_emails)
        
        # 2. 检查人数
        if current_count >= 4:
            return jsonify({"success": False, "error": "该 Team 已达到人数上限 (4人)"}), 400

        # ========== 满员预警逻辑开始 ==========
        check_and_send_team_full_warning(team['name'], current_count, email)
        # ========== 满员预警逻辑结束 ==========
            
        # 3. 检查邮箱
        member_emails = [m.get('email', '').lower() for m in members]
        if email.lower() in member_emails:
            return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400
    else:
        # API 失败，退化为数据库检查
        invited_emails = Invitation.get_all_emails_by_team(team_id)
        if len(invited_emails) >= 4:
            return jsonify({"success": False, "error": "该 Team 已达到人数上限 (4人)"}), 400
        if email in invited_emails:
            return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400

    # 如果之前有失败记录，先删除（允许重新邀请）
    Invitation.delete_by_email(team_id, email)

    # 执行邀请
    result = invite_to_team(team['access_token'], team['account_id'], email, team_id)

    if result['success']:
        # 计算过期时间 - 使用UTC时间
        temp_expire_at = None
        if is_temp and temp_hours > 0:
            now = datetime.utcnow()
            temp_expire_at = (now + timedelta(hours=temp_hours)).strftime('%Y-%m-%d %H:%M:%S')

        # 记录邀请
        Invitation.create(
            team_id=team_id,
            email=email,
            invite_id=result.get('invite_id'),
            status='success',
            is_temp=is_temp,
            temp_expire_at=temp_expire_at
        )

        # 更新team的最后邀请时间（实现轮询）
        Team.update_last_invite(team_id)

        return jsonify({
            "success": True,
            "message": f"已成功邀请 {email}",
            "invite_id": result.get('invite_id')
        })
    else:
        # 邀请 API 返回失败，验证是否实际成功
        import time
        time.sleep(2)  # 等待 API 同步
        
        # 1. 检查是否在 pending 列表中
        pending_result = get_pending_invites(team['access_token'], team['account_id'])
        if pending_result['success']:
            pending_emails = [inv.get('email_address', '').lower() for inv in pending_result.get('invites', [])]
            if email.lower() in pending_emails:
                # 实际已成功（在 pending 列表中），先删除可能存在的failed记录
                Invitation.delete_by_email(team_id, email)
                
                temp_expire_at = None
                if is_temp and temp_hours > 0:
                    now = datetime.utcnow()
                    temp_expire_at = (now + timedelta(hours=temp_hours)).strftime('%Y-%m-%d %H:%M:%S')
                
                Invitation.create(
                    team_id=team_id,
                    email=email,
                    status='success',
                    is_temp=is_temp,
                    temp_expire_at=temp_expire_at
                )
                Team.update_last_invite(team_id)
                
                return jsonify({
                    "success": True,
                    "message": f"已成功邀请 {email}（验证确认）",
                    "verified": True
                })
        
        # 2. 检查是否已在成员列表中
        members_result = get_team_members(team['access_token'], team['account_id'], team_id)
        if members_result['success']:
            member_emails = [m.get('email', '').lower() for m in members_result.get('members', [])]
            if email.lower() in member_emails:
                # 已经是成员了，先删除可能存在的failed记录
                Invitation.delete_by_email(team_id, email)
                
                Invitation.create(
                    team_id=team_id,
                    email=email,
                    status='success',
                    is_temp=is_temp,
                    temp_expire_at=None
                )
                Team.update_last_invite(team_id)
                
                return jsonify({
                    "success": True,
                    "message": f"{email} 已是团队成员",
                    "already_member": True
                })
        
        # 3. 确实失败
        Invitation.create(
            team_id=team_id,
            email=email,
            status='failed'
        )
        return jsonify({
            "success": False,
            "error": f"邀请失败: {result.get('error', '未知错误')}"
        }), 500


@app.route('/api/admin/teams/<int:team_id>/kick-by-email', methods=['POST'])
@admin_required
def kick_member_by_email(team_id):
    """通过邮箱踢出成员"""
    data = request.json
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404

    # 获取成员列表
    members_result = get_team_members(team['access_token'], team['account_id'], team_id)
    if not members_result['success']:
        return jsonify({"success": False, "error": "无法获取成员列表"}), 500

    # 查找匹配的成员
    member = next((m for m in members_result['members']
                   if m.get('email', '').lower() == email), None)

    if not member:
        # 未找到成员，可能已经离开或拒绝邀请，删除invitations记录释放位置
        deleted = Invitation.delete_by_email(team_id, email)
        if deleted:
            return jsonify({
                "success": True, 
                "message": f"未找到 {email}，但已从邀请记录中删除，释放位置"
            })
        else:
            return jsonify({"success": False, "error": f"未找到邮箱为 {email} 的成员或邀请记录"}), 404

    # 检查是否为所有者
    if member.get('role') == 'account-owner':
        return jsonify({"success": False, "error": "不能踢出团队所有者"}), 400

    user_id = member.get('user_id') or member.get('id')

    # 执行踢人
    result = kick_member(team['access_token'], team['account_id'], user_id)

    if result['success']:
        # 从invitations表中删除记录，释放位置
        Invitation.delete_by_email(team_id, email)

        # 记录日志
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=True
        )
        return jsonify({"success": True, "message": f"已成功踢出 {email}"})
    else:
        KickLog.create(
            team_id=team_id,
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=False,
            error_message=result.get('error')
        )
        return jsonify({"success": False, "error": result.get('error')}), 500


@app.route('/api/admin/invite-auto', methods=['POST'])
@admin_required
def admin_invite_auto():
    """管理员邀请成员(自动分配Team，智能重试)"""
    data = request.json
    email = data.get('email', '').strip()
    is_temp = data.get('is_temp', False)
    temp_hours = data.get('temp_hours', 24) if is_temp else 0

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    # 方案2优化：智能选择Team + 限制重试次数
    # 1. 获取所有Team（排除token过期的）
    all_teams = Team.get_all()
    all_teams = [t for t in all_teams if t.get('token_status') != 'expired']

    if not all_teams:
        return jsonify({"success": False, "error": "当前无可用 Team，请先添加 Team"}), 400

    # 2. 只选择通过我们系统邀请的成员数 < 4 的Team
    available_teams = []
    for team in all_teams:
        invited_count = Invitation.get_success_count_by_team(team['id'])
        if invited_count < 4:
            team['invited_count'] = invited_count
            available_teams.append(team)

    if not available_teams:
        return jsonify({"success": False, "error": "所有 Team 名额已满，请先添加 Team"}), 400

    # 3. 按最近邀请时间排序（最近成功的在前）
    available_teams.sort(key=lambda t: t.get('last_invite_at') or '', reverse=True)

    # 4. 最多尝试3个Team
    max_attempts = 3
    tried_teams = []
    last_error = None

    for i, team in enumerate(available_teams):
        if i >= max_attempts:
            break

        tried_teams.append(team['name'])

        # 检查实际成员数
        members_result = get_team_members(team['access_token'], team['account_id'], team['id'])
        if not members_result['success']:
            last_error = f"无法获取{team['name']}成员列表"
            continue

        members = members_result.get('members', [])
        non_owner_members = [m for m in members if m.get('role') != 'account-owner']

        # 实际成员数已满，跳过
        if len(non_owner_members) >= 4:
            last_error = f"{team['name']}实际成员已满"
            continue

        # 检查该邮箱是否已在此Team中
        member_emails = [m.get('email', '').lower() for m in members]
        if email.lower() in member_emails:
            return jsonify({"success": False, "error": f"该邮箱已在 {team['name']} 团队中"}), 400

        # 执行邀请
        result = invite_to_team(team['access_token'], team['account_id'], email, team['id'])

        if result['success']:
            # 邀请成功！计算过期时间
            temp_expire_at = None
            if is_temp and temp_hours > 0:
                now = datetime.utcnow()
                temp_expire_at = (now + timedelta(hours=temp_hours)).strftime('%Y-%m-%d %H:%M:%S')

            # 记录邀请
            Invitation.create(
                team_id=team['id'],
                email=email,
                invite_id=result.get('invite_id'),
                status='success',
                is_temp=is_temp,
                temp_expire_at=temp_expire_at
            )

            # 更新team的最后邀请时间
            Team.update_last_invite(team['id'])

            message = f"已成功邀请 {email} 加入 {team['name']}"
            if len(tried_teams) > 1:
                message += f"（尝试了 {len(tried_teams)} 个Team）"

            return jsonify({
                "success": True,
                "message": message,
                "team_name": team['name'],
                "invite_id": result.get('invite_id')
            })
        else:
            # 邀请失败，验证是否实际成功（检查pending列表）
            import time
            time.sleep(1)  # 等待API同步

            pending_result = get_pending_invites(team['access_token'], team['account_id'])
            if pending_result['success']:
                pending_emails = [inv.get('email_address', '').lower() for inv in pending_result.get('invites', [])]
                if email.lower() in pending_emails:
                    # 实际已成功（在pending列表中）
                    temp_expire_at = None
                    if is_temp and temp_hours > 0:
                        now = datetime.utcnow()
                        temp_expire_at = (now + timedelta(hours=temp_hours)).strftime('%Y-%m-%d %H:%M:%S')

                    Invitation.create(
                        team_id=team['id'],
                        email=email,
                        invite_id=None,
                        status='success',
                        is_temp=is_temp,
                        temp_expire_at=temp_expire_at
                    )
                    Team.update_last_invite(team['id'])

                    message = f"已成功邀请 {email} 加入 {team['name']}（验证确认）"
                    if len(tried_teams) > 1:
                        message += f"（尝试了 {len(tried_teams)} 个Team）"

                    return jsonify({
                        "success": True,
                        "message": message,
                        "team_name": team['name']
                    })

            # 确实失败，记录错误并尝试下一个Team
            last_error = f"{team['name']}: {result.get('error', '未知错误')}"
            continue

    # 所有Team都试过了，仍然失败
    return jsonify({
        "success": False,
        "error": f"尝试了 {len(tried_teams)} 个Team均失败\n最后错误: {last_error}\n尝试的Team: {', '.join(tried_teams)}"
    }), 500


@app.route('/api/admin/kick-by-email-auto', methods=['POST'])
@admin_required
def kick_member_by_email_auto():
    """通过邮箱踢出成员(自动查找所有Team) - 优化版：优先从数据库查询"""
    data = request.json
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    # 性能优化：先从邀请记录中查找该邮箱可能所在的Team
    candidate_team_ids = Invitation.get_teams_by_email(email)

    found_team = None
    found_member = None

    # 优先检查候选Team（有邀请记录的Team）
    if candidate_team_ids:
        for team_id in candidate_team_ids:
            team = Team.get_by_id(team_id)
            if not team:
                continue

            # 获取成员列表
            members_result = get_team_members(team['access_token'], team['account_id'], team_id)
            if not members_result['success']:
                continue

            # 查找匹配的成员
            member = next((m for m in members_result['members']
                           if m.get('email', '').lower() == email), None)

            if member:
                found_team = team
                found_member = member
                # 确保有 user_id 字段
                if 'user_id' not in found_member:
                    found_member['user_id'] = found_member.get('id')
                break

    # 如果候选Team中没找到，再遍历所有Team（兜底逻辑，处理手动添加的成员）
    if not found_team or not found_member:
        teams = Team.get_all()
        if not teams:
            return jsonify({"success": False, "error": "当前没有 Team"}), 404

        # 排除已检查过的Team
        checked_team_ids = set(candidate_team_ids)

        for team in teams:
            if team['id'] in checked_team_ids:
                continue

            # 获取成员列表
            members_result = get_team_members(team['access_token'], team['account_id'], team['id'])
            if not members_result['success']:
                continue

            # 查找匹配的成员
            member = next((m for m in members_result['members']
                           if m.get('email', '').lower() == email), None)

            if member:
                found_team = team
                found_member = member
                # 确保有 user_id 字段
                if 'user_id' not in found_member:
                    found_member['user_id'] = found_member.get('id')
                break

    if not found_team or not found_member:
        # 未找到成员，可能已经离开或拒绝邀请，删除invitations记录释放位置
        deleted_count = 0
        teams = Team.get_all()
        for team in teams:
            deleted = Invitation.delete_by_email(team['id'], email)
            if deleted:
                deleted_count += 1

        if deleted_count > 0:
            return jsonify({
                "success": True,
                "message": f"未找到 {email}，但已从 {deleted_count} 个Team的邀请记录中删除，释放位置"
            })
        else:
            return jsonify({"success": False, "error": f"未找到邮箱为 {email} 的成员或邀请记录"}), 404

    # 检查是否为所有者
    if found_member.get('role') == 'account-owner':
        return jsonify({"success": False, "error": "不能踢出团队所有者"}), 400

    user_id = found_member.get('user_id') or found_member.get('id')

    # 执行踢人
    result = kick_member(found_team['access_token'], found_team['account_id'], user_id)

    if result['success']:
        # 从invitations表中删除记录，释放位置
        Invitation.delete_by_email(found_team['id'], email)

        # 记录日志
        KickLog.create(
            team_id=found_team['id'],
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=True
        )
        return jsonify({
            "success": True,
            "message": f"已成功从 {found_team['name']} 踢出 {email}"
        })
    else:
        KickLog.create(
            team_id=found_team['id'],
            user_id=user_id,
            email=email,
            reason='管理员通过邮箱手动踢出',
            success=False,
            error_message=result.get('error')
        )
        return jsonify({"success": False, "error": result.get('error')}), 500


@app.route('/api/admin/auto-kick/config', methods=['GET'])
@admin_required
def get_auto_kick_config():
    """获取自动踢人配置"""
    config = AutoKickConfig.get()

    if config:
        # 转换为前端需要的格式
        start_time = config.get('start_time', '00:00')
        end_time = config.get('end_time', '23:59')

        # 提取小时
        start_hour = int(start_time.split(':')[0])
        end_hour = int(end_time.split(':')[0])

        config['check_interval'] = config.get('check_interval_min', 300)
        config['run_hours'] = f"{start_hour}-{end_hour}"

    return jsonify({"success": True, "config": config})


@app.route('/api/admin/auto-kick/config', methods=['POST', 'PUT'])
@admin_required
def update_auto_kick_config():
    """更新自动踢人配置"""
    data = request.json

    check_interval = data.get('check_interval', 300)
    run_hours = data.get('run_hours', '0-23')

    try:
        # 解析运行时间段
        if '-' in run_hours:
            start_hour, end_hour = map(int, run_hours.split('-'))
        else:
            start_hour, end_hour = 0, 23

        AutoKickConfig.update(
            enabled=data.get('enabled', True),
            check_interval_min=check_interval,
            check_interval_max=check_interval,
            start_time=f"{start_hour:02d}:00",
            end_time=f"{end_hour:02d}:59"
        )

        # 如果启用了自动检测,启动服务
        if data.get('enabled', True):
            auto_kick_service.start()
        else:
            auto_kick_service.stop()

        return jsonify({"success": True, "message": "配置更新成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/auto-kick/logs', methods=['GET'])
@admin_required
def get_kick_logs():
    """获取踢人日志"""
    limit = request.args.get('limit', 100, type=int)
    logs = KickLog.get_all(limit)
    return jsonify({"success": True, "logs": logs})


@app.route('/api/admin/auto-kick/check-now', methods=['POST'])
@admin_required
def check_now():
    """立即执行一次检测（优化版本）"""
    try:
        # 检查是否已有检测任务在运行
        if auto_kick_service.is_checking():
            return jsonify({
                "success": False,
                "error": "检测任务已在运行中，请稍后再试"
            }), 409
        
        # 使用 daemon 线程
        import threading
        thread = threading.Thread(
            target=auto_kick_service._check_and_kick,
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "检测任务已启动"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/auto-kick/status', methods=['GET'])
@admin_required
def get_kick_status():
    """获取检测任务状态"""
    try:
        status = auto_kick_service.get_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------
# 来源管理 API
# ---------------------------------------------------------------------

@app.route('/api/admin/stats/source-ranking', methods=['GET'])
def get_source_ranking():
    """获取来源排行榜 (无需鉴权)"""
    try:
        ranking = MemberNote.get_source_ranking()
        return jsonify({"success": True, "ranking": ranking})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/sources', methods=['GET'])
@admin_required
def get_sources():
    """获取所有来源"""
    try:
        sources = Source.get_all()
        return jsonify({"success": True, "sources": sources})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/sources', methods=['POST'])
@admin_required
def add_source():
    """添加来源"""
    data = request.json
    name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not name:
        return jsonify({"success": False, "error": "来源名称不能为空"}), 400
        
    try:
        Source.add(name, username, password)
        return jsonify({"success": True, "message": "添加成功"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "error": "该来源名称或账号已存在"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/sources/<int:source_id>', methods=['DELETE'])
@admin_required
def delete_source(source_id):
    """删除来源"""
    try:
        Source.delete(source_id)
        return jsonify({"success": True, "message": "删除成功"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ================== 系统配置 API ==================

@app.route('/api/admin/config/mail', methods=['GET'])
@admin_required
def get_mail_config():
    """获取邮件配置"""
    configs = SystemConfig.get_all()
    # 过滤掉非邮件配置
    mail_configs = {k: v for k, v in configs.items() if k.startswith('mail_')}
    return jsonify({"success": True, "config": mail_configs})

@app.route('/api/admin/config/mail', methods=['POST'])
@admin_required
def update_mail_config():
    """更新邮件配置"""
    data = request.json
    try:
        SystemConfig.set_bulk(data)
        return jsonify({"success": True, "message": "配置已保存"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/mail/test', methods=['POST'])
@admin_required
def test_mail():
    """发送测试邮件"""
    email = request.json.get('email')
    if not email:
        return jsonify({"success": False, "error": "请输入收件人邮箱"}), 400
        
    success, message = mail_service.send_test_mail(email)
    if success:
        return jsonify({"success": True, "message": "测试邮件已发送，请查收"})
    else:
        return jsonify({"success": False, "error": f"发送失败: {message}"}), 500


@app.route('/api/admin/system-config', methods=['GET'])
@admin_required
def get_system_config():
    """获取系统配置"""
    configs = SystemConfig.get_all_with_desc()
    return jsonify({"success": True, "config": configs})


@app.route('/api/admin/system-config', methods=['POST'])
@admin_required
def update_system_config():
    """更新系统配置"""
    data = request.json
    try:
        # data should be a dict of key-value pairs
        # e.g. {"team_popup_content": "..."}
        # Use set_bulk to update multiple configs at once if needed, 
        # or loop through data and call SystemConfig.set
        
        # Check if SystemConfig has set_bulk
        if hasattr(SystemConfig, 'set_bulk'):
             SystemConfig.set_bulk(data)
        else:
             for key, value in data.items():
                 SystemConfig.set(key, value)

        return jsonify({"success": True, "message": "配置已保存"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/test-bark', methods=['POST'])
@admin_required
def test_bark():
    """测试 Bark 消息发送"""
    data = request.json
    server = data.get('server', '').rstrip('/')
    key = data.get('key', '')
    
    if not server or not key:
        return jsonify({"success": False, "error": "请提供服务器地址和 Key"}), 400
        
    try:
        # 对中文内容进行 URL 编码
        from urllib.parse import quote
        title = quote("ChatGPT Team 通知")
        content = quote("测试消息发送成功")
        
        url = f"{server}/{key}/{title}/{content}"
        response = cf_requests.get(url, impersonate="chrome110")
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": "发送成功"})
        else:
            return jsonify({"success": False, "error": f"服务器返回错误: {response.status_code}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/admin/test-team-full-warning', methods=['POST'])
@admin_required
def test_team_full_warning():
    """测试满员预警消息发送"""
    data = request.json
    server = data.get('server', '').rstrip('/')
    key = data.get('key', '')
    template = data.get('template', '')
    
    if not server or not key:
        return jsonify({"success": False, "error": "请先配置并填写 Bark 服务器地址和 Key"}), 400
    
    if not template:
        return jsonify({"success": False, "error": "请填写预警消息模板"}), 400
        
    try:
        # 获取一个随机 Team 用于测试
        teams = Team.get_all()
        if teams:
            import random
            team = random.choice(teams)
            team_name = team['name']
            current_count = team['member_count']
        else:
            team_name = "测试Team"
            current_count = 3
            
        email = "test_user@example.com"
        
        # 替换模板变量
        try:
            message = template.format(
                team_name=team_name,
                current_count=current_count,
                email=email
            )
        except Exception as e:
            return jsonify({"success": False, "error": f"模板格式错误: {str(e)}"}), 400
        
        # 发送推送
        from urllib.parse import quote
        title = quote("ChatGPT Team 满员预警(测试)")
        content = quote(message)
        
        url = f"{server}/{key}/{title}/{content}"
        response = cf_requests.get(url, impersonate="chrome110")
        
        if response.status_code == 200:
            return jsonify({"success": True, "message": f"测试消息已发送 (模拟Team: {team_name})"})
        else:
            return jsonify({"success": False, "error": f"服务器返回错误: {response.status_code}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/public/system-config', methods=['GET'])
def get_public_system_config():
    """获取公开系统配置"""
    # Only return specific public configs to avoid leaking sensitive info
    public_keys = ['team_popup_content']
    configs = {}
    for key in public_keys:
        configs[key] = SystemConfig.get(key)
    return jsonify({"success": True, "config": configs})



# ================== 公开 Team 页面路由 ==================

@app.route('/team')
def public_teams_page():
    """公开 Team 页面"""
    return render_template('public_teams.html')


@app.route('/team/login')
def public_team_login_page():
    """公开 Team 登录页面"""
    return render_template('team_login.html')


@app.route('/api/public/login', methods=['POST'])
def public_login():
    """公开页面登录验证"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"success": False, "error": "请输入账号和密码"}), 400

    user = Source.verify_user(username, password)
    if user:
        return jsonify({
            "success": True, 
            "message": "登录成功",
            "username": user['username'],
            "name": user['name']
        })
    else:
        return jsonify({"success": False, "error": "账号或密码错误"}), 401


@app.route('/api/public/teams', methods=['POST'])
def get_public_teams():
    """获取公开的 Team 列表 (需账号密码验证)"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    # 验证账号
    user = Source.verify_user(username, password)
    if not user:
        return jsonify({"success": False, "error": "账号或密码错误"}), 403

    try:
        # 获取所有 Team
        all_teams = Team.get_all()
        # 筛选 is_public=True 的 Team
        public_teams = []
        for t in all_teams:
            if t.get('is_public'):
                # 获取该 Team 的成功邀请数量 (用于前端展示进度条: 已加入 vs 已邀请)
                # member_count 是已加入数量
                # invite_count 是总的邀请占位数量 (包含已加入和待加入)
                # 所以待加入数量 = max(0, invite_count - member_count)
                t['invite_count'] = Invitation.get_success_count_by_team(t['id'])
                public_teams.append(t)

        return jsonify({"success": True, "teams": public_teams})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/public/teams/<int:team_id>/invite', methods=['POST'])
def public_invite_member(team_id):
    """公开页面邀请成员 (需账号密码验证)"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')
    email = data.get('email', '').strip()

    # 验证账号
    user = Source.verify_user(username, password)
    if not user:
        return jsonify({"success": False, "error": "账号或密码错误"}), 403

    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404
        
    if not team.get('is_public'):
        return jsonify({"success": False, "error": "该 Team 未公开"}), 403

    # 1. 先进行数据库层面的预判
    # 如果本地记录显示已满，直接拦截，不调用 API。
    # 如果用户发现本地显示已满但实际没满，需要先点击“刷新”按钮同步数据。
    invited_emails = Invitation.get_all_emails_by_team(team_id)
    if len(invited_emails) >= 4:
        return jsonify({"success": False, "error": "该 Team 已达到人数上限 (4人)"}), 400

    # 检查该邮箱是否已被成功邀请 (本地检查)
    if email in invited_emails:
        return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400

    # 2. 实时调用 API 检查并同步最新状态 (Lazy Sync)
    members_result = get_team_members(team['access_token'], team['account_id'], team_id)
    
    if members_result['success']:
        # 获取最新成员列表
        members = members_result.get('members', [])
        non_owner_members = [m for m in members if m.get('role') != 'account-owner']
        current_count = len(non_owner_members)
        
        # 同步更新数据库
        Team.update_member_count(team_id, current_count)
        
        # 同步成员详情 (可选，为了保持数据一致性)
        current_user_ids = []
        for member in members:
            user_id = member.get('id')
            if user_id:
                current_user_ids.append(user_id)
                email_val = member.get('email')
                role = member.get('role')
                # 处理时间格式
                created_time_str = member.get('created_time')
                join_time = member.get('created')
                if created_time_str:
                    try:
                        if created_time_str.endswith('Z'):
                            created_time_str = created_time_str.replace('Z', '+00:00')
                        dt = datetime.fromisoformat(created_time_str)
                        join_time = int(dt.timestamp())
                    except:
                        pass
                MemberNote.sync_member(team_id, user_id, email_val, role, join_time)
        
        # 清理失效数据
        MemberNote.delete_not_in(team_id, current_user_ids)
        current_emails = [m.get('email') for m in members if m.get('email')]
        Invitation.sync_invitations(team_id, current_emails)
        
        # 3. 再次检查人数 (使用最新的实时数据)
        if current_count >= 4:
            return jsonify({"success": False, "error": "该 Team 已达到人数上限 (4人)"}), 400

        # ========== 满员预警逻辑开始 (Public) ==========
        check_and_send_team_full_warning(team['name'], current_count, email)
        # ========== 满员预警逻辑结束 ==========
            
        # 4. 检查该邮箱是否已在此Team中 (实时数据)
        member_emails = [m.get('email', '').lower() for m in members]
        if email.lower() in member_emails:
            return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400
            
    else:
        # 如果 API 调用失败 (例如超时)，退化为依赖数据库检查
        # 这种情况下，我们只能相信数据库
        invited_emails = Invitation.get_all_emails_by_team(team_id)
        if len(invited_emails) >= 4:
            return jsonify({"success": False, "error": "该 Team 已达到人数上限 (4人)"}), 400
        if email in invited_emails:
            return jsonify({"success": False, "error": "该邮箱已被邀请过"}), 400

    # 如果之前有失败记录，先删除（允许重新邀请）
    Invitation.delete_by_email(team_id, email)

    # 执行邀请
    result = invite_to_team(team['access_token'], team['account_id'], email, team_id)

    if result['success']:
        # 记录邀请 (自动归属 source)
        Invitation.create(
            team_id=team_id,
            email=email,
            invite_id=result.get('invite_id'),
            status='success',
            is_temp=False, # 公开页面邀请默认为永久
            temp_expire_at=None,
            source=user['name'] # 记录来源
        )

        # 更新team的最后邀请时间
        Team.update_last_invite(team_id)

        return jsonify({
            "success": True,
            "message": f"已成功邀请 {email}",
            "invite_id": result.get('invite_id')
        })
    else:
        # 邀请 API 返回失败，验证是否实际成功
        import time
        time.sleep(2)  # 等待 API 同步
        
        # 1. 检查是否在 pending 列表中
        pending_result = get_pending_invites(team['access_token'], team['account_id'])
        if pending_result['success']:
            pending_emails = [inv.get('email_address', '').lower() for inv in pending_result.get('invites', [])]
            if email.lower() in pending_emails:
                # 实际已成功
                Invitation.delete_by_email(team_id, email)
                Invitation.create(
                    team_id=team_id,
                    email=email,
                    status='success',
                    is_temp=False,
                    temp_expire_at=None,
                    source=user['name'] # 记录来源
                )
                Team.update_last_invite(team_id)
                
                return jsonify({
                    "success": True,
                    "message": f"已成功邀请 {email}（验证确认）",
                    "verified": True
                })
        
        # 2. 检查是否已在成员列表中
        members_result = get_team_members(team['access_token'], team['account_id'], team_id)
        if members_result['success']:
            member_emails = [m.get('email', '').lower() for m in members_result.get('members', [])]
            if email.lower() in member_emails:
                # 已经是成员了
                Invitation.delete_by_email(team_id, email)
                Invitation.create(
                    team_id=team_id,
                    email=email,
                    status='success',
                    is_temp=False,
                    temp_expire_at=None,
                    source=user['name'] # 记录来源
                )
                Team.update_last_invite(team_id)
                
                return jsonify({
                    "success": True,
                    "message": f"{email} 已是团队成员",
                    "already_member": True
                })
        
        # 3. 确实失败
        Invitation.create(
            team_id=team_id,
            email=email,
            status='failed',
            source=user['name'] # 记录来源（即使失败也记录一下是谁操作的）
        )
        return jsonify({
            "success": False,
            "error": f"邀请失败: {result.get('error', '未知错误')}"
        }), 500


@app.route('/api/public/teams/<int:team_id>/members', methods=['POST'])
def public_get_members(team_id):
    """公开页面查看成员 (需账号密码验证) - 优先从数据库读取，合并邀请状态"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    # 验证账号
    user = Source.verify_user(username, password)
    if not user:
        return jsonify({"success": False, "error": "账号或密码错误"}), 403

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404
        
    if not team.get('is_public'):
        return jsonify({"success": False, "error": "该 Team 未公开"}), 403

    # 1. 获取已加入成员 (Status: 2)
    db_members = MemberNote.get_all(team_id)
    
    # 使用字典去重，key为小写邮箱
    merged_members = {}
    
    for m in db_members:
        safe_m = {
            'email': m.get('email'),
            'role': m.get('role'),
            'created': m.get('join_time'), # 使用 join_time
            'source': m.get('source'), # 返回来源
            'status': 2,
            'status_text': '已加入'
        }
        
        email_key = safe_m['email'].strip().lower() if safe_m['email'] else ''
        if email_key:
            merged_members[email_key] = safe_m
        else:
            # 没有邮箱的情况（极少），这里简单处理，如果 public view 必须依赖 email 可能会有问题
            # 但通常 member 都有 email
            pass

    # 2. 获取待处理邀请 (Status: 1)
    invitations = Invitation.get_by_team(team_id)
    
    for inv in invitations:
        email = inv.get('email', '').strip().lower()
        if not email:
            continue
            
        # 如果该邮箱已经在 merged_members 中，说明已加入，跳过
        if email in merged_members:
            continue
            
        # 确定状态文本
        status_text = '已邀请'
        if inv.get('status') == 'success':
             status_text = '已发送邀请'
        elif inv.get('status') == 'failed':
             status_text = '邀请失败'
        elif inv.get('status') == 'expired':
             status_text = '已过期'
        
        invite_obj = {
            'email': inv.get('email'),
            'role': 'member',
            'created': inv.get('created_at'),
            'source': inv.get('source'),
            'status': 1,
            'status_text': status_text
        }
        
        merged_members[email] = invite_obj

    # 转为列表并按时间排序 (倒序)
    safe_members = list(merged_members.values())
    
    def get_sort_time(x):
        t = x.get('created')
        if not t: return ''
        return str(t)

    safe_members.sort(key=get_sort_time, reverse=True)
        
    return jsonify({"success": True, "members": safe_members})


@app.route('/api/public/teams/<int:team_id>/members/refresh', methods=['POST'])
def public_refresh_members(team_id):
    """公开页面刷新成员 (需账号密码验证)"""
    data = request.json
    username = data.get('username', '')
    password = data.get('password', '')

    # 验证账号
    user = Source.verify_user(username, password)
    if not user:
        return jsonify({"success": False, "error": "账号或密码错误"}), 403

    team = Team.get_by_id(team_id)
    if not team:
        return jsonify({"success": False, "error": "Team 不存在"}), 404
        
    if not team.get('is_public'):
        return jsonify({"success": False, "error": "该 Team 未公开"}), 403

    # 调用 admin 中的刷新逻辑 (复用逻辑，避免代码重复)
    # 这里直接调用内部函数或者复用 refresh_members 的逻辑
    # 由于 refresh_members 是路由函数，我们最好提取公共逻辑，或者在这里重新实现一遍
    
    result = get_team_members(team['access_token'], team['account_id'], team_id)

    if result['success']:
        members = result.get('members', [])
        
        # 更新数据库中的成员数量
        non_owner_members = [m for m in members if m.get('role') != 'account-owner']
        Team.update_member_count(team_id, len(non_owner_members))

        # 同步每个成员到 member_notes
        current_user_ids = []
        for member in members:
            user_id = member.get('id')
            if not user_id:
                continue
            
            current_user_ids.append(user_id)
            
            email = member.get('email')
            role = member.get('role')
            created_time_str = member.get('created_time')
            join_time = None
            if created_time_str:
                try:
                    if created_time_str.endswith('Z'):
                        created_time_str = created_time_str.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(created_time_str)
                    join_time = int(dt.timestamp())
                except Exception as e:
                    join_time = member.get('created')
            else:
                 join_time = member.get('created')

            MemberNote.sync_member(team_id, user_id, email, role, join_time)
            
        # 删除不在当前列表中的成员
        MemberNote.delete_not_in(team_id, current_user_ids)
        
        # 同步清理失效的邀请记录
        current_emails = [m.get('email') for m in members if m.get('email')]
        Invitation.sync_invitations(team_id, current_emails)
            
        return jsonify({"success": True, "message": "成员列表已刷新"})
    else:
        return jsonify(result), result.get('status_code', 500)


@app.route('/api/public/send-tutorial', methods=['POST'])
def public_send_tutorial():
    """发送导出教程邮件 (无需鉴权)"""
    data = request.json
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({"success": False, "error": "请输入邮箱"}), 400
        
    # 获取模板
    template = SystemConfig.get('mail_template_export_tutorial')
    if not template:
        return jsonify({"success": False, "error": "管理员尚未配置教程模板"}), 404
        
    # 发送邮件
    subject = "工作空间记录导出教程"
    success, message = mail_service.send_mail(email, subject, template, is_html=True)
    
    if success:
        return jsonify({"success": True, "message": "教程已发送，请查收邮件"})
    else:
        return jsonify({"success": False, "error": f"发送失败: {message}"}), 500


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    print(f"🚀 ChatGPT Team 自动邀请系统启动")
    print(f"📍 管理员后台: http://{HOST}:{PORT}/admin")
    print(f"📍 用户页面: http://{HOST}:{PORT}/")
    print(f"🔑 管理员密码: {ADMIN_PASSWORD}")
    print(f"⚠️  请在生产环境中修改管理员密码！")

    # 检查自动踢人配置,如果启用则启动服务
    config = AutoKickConfig.get()
    if config and config['enabled']:
        auto_kick_service.start()
    

    app.run(host=HOST, port=PORT, debug=DEBUG)

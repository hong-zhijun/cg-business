import yagmail
from database import SystemConfig

def get_mail_config():
    """获取邮件配置"""
    config = SystemConfig.get_all()
    return {
        'server': config.get('mail_smtp_server'),
        'port': int(config.get('mail_smtp_port') or 465),
        'user': config.get('mail_smtp_user'),
        'password': config.get('mail_smtp_password'),
        'sender_name': config.get('mail_sender_name', 'ChatGPT Team Admin'),
        'use_ssl': config.get('mail_use_ssl', 'true').lower() == 'true',
        'enabled': config.get('mail_enabled', 'false').lower() == 'true'
    }

def send_mail(to_email, subject, content, is_html=False):
    """
    发送邮件 (使用 yagmail 库)
    """
    config = get_mail_config()
    
    if not config['enabled']:
        return False, "邮件功能未启用"
        
    if not all([config['server'], config['user'], config['password']]):
        return False, "邮件配置不完整 (服务器、用户或密码为空)"

    try:
        # yagmail 会自动处理 STARTTLS/SSL
        # 注意: yagmail 默认优先使用 SMTP_SSL (465)，如果端口是 587，它会自动识别并使用 STARTTLS
        
        # 构造发送者字典 {email: name}
        sender_info = {config['user']: config['sender_name']}
        
        # 初始化 SMTP 连接
        # 如果是 QQ 邮箱 (smtp.qq.com)，yagmail 有内置优化
        yag = yagmail.SMTP(
            user=config['user'],
            password=config['password'],
            host=config['server'],
            port=config['port'],
            smtp_starttls=True if config['port'] == 587 else False,
            smtp_ssl=True if config['port'] == 465 else False
        )
        
        # 发送
        # contents 参数可以是列表，yagmail 会自动把 html 字符串识别为 html 内容
        yag.send(
            to=to_email,
            subject=subject,
            contents=[content] if is_html else content,
            headers={"From": f"{config['sender_name']} <{config['user']}>"} # 强制指定 From 头
        )
                
        return True, "发送成功"
    except Exception as e:
        import traceback
        traceback.print_exc()
        # yagmail 的错误通常比较详细，直接返回
        return False, f"发送失败: {str(e)}"

def send_test_mail(to_email):
    """发送测试邮件"""
    subject = "ChatGPT Team 系统 - 邮件测试"
    content = """
    <h1>邮件发送测试</h1>
    <p>如果您收到这就邮件，说明您的 SMTP 配置是正确的。</p>
    <p>Sent from ChatGPT Team Admin System</p>
    """
    return send_mail(to_email, subject, content, is_html=True)

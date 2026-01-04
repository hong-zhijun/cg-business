import requests
import random
import string
import logging
from database import SystemConfig

class CustomMailAPI:
    """
    自建邮件服务 API 客户端
    封装了与自建邮件服务 Worker 的交互逻辑
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _get_config(self):
        """
        从数据库获取必要的配置信息
        """
        config = {
            'base_url': SystemConfig.get('request_base_url'),
            'admin_password': SystemConfig.get('admin_password'),
            'email_domain': SystemConfig.get('email_domain'),
            'site_password': SystemConfig.get('site_password')
        }
        return config

    def _generate_random_name(self, min_length=6, max_length=12):
        """
        生成随机邮箱前缀 (6-12位数字小写英文)
        """
        length = random.randint(min_length, max_length)
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def create_address(self):
        """
        调用自建邮件服务创建新邮箱地址
        
        接口地址: /admin/new_address
        
        Returns:
            dict: API 返回的 JSON 数据, 例如 {"jwt": "<Jwt>"}
        
        Raises:
            ValueError: 配置不完整时抛出
            requests.exceptions.RequestException: 请求失败时抛出
        """
        config = self._get_config()
        
        # 检查配置是否完整
        if not all([config['base_url'], config['admin_password'], config['email_domain'], config['site_password']]):
            missing = [k for k, v in config.items() if not v]
            error_msg = f"自建邮件服务配置不完整，缺少: {', '.join(missing)}。请在系统配置中完善。"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        base_url = config['base_url'].rstrip('/')
        url = f"{base_url}/admin/new_address"
        
        # 生成随机邮箱前缀
        name = self._generate_random_name()
        
        payload = {
            "enablePrefix": False,
            "name": name,
            "domain": config['email_domain']
        }
        
        headers = {
            'x-admin-auth': config['admin_password'],
            'x-custom-auth': config['site_password'],
            "Content-Type": "application/json"
        }
        # 在控制台打印所有请求参数和头print
        print(f"DEBUG Request URL: {url}")
        print(f"DEBUG Request Headers: {headers}")
        print(f"DEBUG Request Payload: {payload}")

        try:
            # 打印请求信息到终端
            print(f"Requesting new email address: {name}@{config['email_domain']}")
            self.logger.info(f"Requesting new email address: {name}@{config['email_domain']}")
            
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # 输出接口返回内容到终端和日志，方便调试
            print(f"Create address API Response: {res.text}")
            self.logger.info(f"Create address API Response: {res.text}")
            
            res.raise_for_status()
            
            result = res.json()
            # 添加生成的邮箱地址到返回结果中
            result['email'] = f"{name}@{config['email_domain']}"
            return result
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create email address: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                 self.logger.error(f"Response status: {e.response.status_code}")
                 self.logger.error(f"Response content: {e.response.text}")
            raise e

if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    api = CustomMailAPI()
    try:
        # 注意：这需要数据库中有真实的配置才能成功运行
        print("Attempting to create email address...")
        result = api.create_address()
        print("Success! Result:", result)
    except Exception as e:
        print(f"Test failed: {e}")

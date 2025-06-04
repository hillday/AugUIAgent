import os
import json

class ConfigManager:
    def __init__(self, config_file="settings.json"):
        # 确保配置目录存在
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 配置文件路径
        self.config_file = os.path.join(self.config_dir, config_file)
        
        # 默认配置
        self.default_config = {
            "api_key": "",
            "api_host": "https://ark.cn-beijing.volces.com/api/v3",
            "models": {
                "vlm_model_ep": "ep-20250418110236-jmbdw",
                "uitars_model_ep": "ep-20250417185159-jzzlk",
                "planning_model_ep": "ep-20250417185051-xg7xf"
            },
            "knowledge_base": {
                "video_dir": "videos",
                "frame_dir": "frames",
                "fps": 0.5
            },
            "tasks": {
                "history_file": "task_history.json",
                "log_dir": "logs"
            }
        }
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件，如果不存在则创建默认配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}，将使用默认配置")
                return self.default_config
        else:
            # 创建默认配置文件
            self.save_config(self.default_config)
            return self.default_config
    
    def save_config(self, config=None):
        """保存配置到文件"""
        if config is not None:
            self.config = config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项，支持使用点号访问嵌套配置"""
        if '.' in key:
            parts = key.split('.')
            value = self.config
            for part in parts:
                if part in value:
                    value = value[part]
                else:
                    return default
            return value
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项，支持使用点号设置嵌套配置"""
        if '.' in key:
            parts = key.split('.')
            config = self.config
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
            config[parts[-1]] = value
        else:
            self.config[key] = value
        
        # 保存更改
        return self.save_config()
    
    def get_api_key(self):
        """获取API密钥"""
        return self.get('api_key', '')
    
    def set_api_key(self, api_key):
        """设置API密钥"""
        return self.set('api_key', api_key)
    
    def get_model_ep(self, model_type):
        """获取指定类型的模型EP"""
        return self.get(f'models.{model_type}', '')
    
    def set_model_ep(self, model_type, ep):
        """设置指定类型的模型EP"""
        return self.set(f'models.{model_type}', ep)
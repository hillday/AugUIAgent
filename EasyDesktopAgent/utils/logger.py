import os
import logging
from logging.handlers import RotatingFileHandler
import json
import sys

class Logger:
    """日志记录器类"""
    
    def __init__(self, config_manager=None):
        """初始化日志记录器
        
        Args:
            config_manager: 配置管理器实例，用于获取日志配置
        """
        self.logger = logging.getLogger('EasyDesktopAgent')
        self.logger.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
        
        # 如果提供了配置管理器，则使用配置中的设置
        if config_manager:
            self._configure_from_manager(config_manager)
        else:
            # 默认日志文件路径
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            log_file = os.path.join(log_dir, 'app.log')
            self._add_file_handler(log_file)
    
    def _configure_from_manager(self, config_manager):
        """从配置管理器获取日志配置"""
        log_level_str = config_manager.get('logging.level', 'INFO')
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        log_file = config_manager.get('logging.file', 'app.log')
        max_size = config_manager.get('logging.max_size', 10 * 1024 * 1024)  # 默认10MB
        backup_count = config_manager.get('logging.backup_count', 5)
        
        # 确保日志目录存在
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_path = os.path.join(log_dir, log_file)
        self._add_file_handler(log_path, max_size, backup_count)
    
    def _add_file_handler(self, log_file, max_size=10*1024*1024, backup_count=5):
        """添加文件处理器"""
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_size, 
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message):
        """记录调试信息"""
        self.logger.debug(message)
    
    def info(self, message):
        """记录一般信息"""
        self.logger.info(message)
    
    def warning(self, message):
        """记录警告信息"""
        self.logger.warning(message)
    
    def error(self, message):
        """记录错误信息"""
        self.logger.error(message)
    
    def critical(self, message):
        """记录严重错误信息"""
        self.logger.critical(message)
    
    def exception(self, message):
        """记录异常信息，包含堆栈跟踪"""
        self.logger.exception(message)

# 创建默认日志记录器实例
logger = Logger()

# 导出日志函数，方便直接调用
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception
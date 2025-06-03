"""
日志工具

提供统一的日志记录功能
"""

import logging
import os
from datetime import datetime
from enum import Enum
from typing import Optional


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    enable_console: bool = True,
    enable_colors: bool = True
) -> logging.Logger:
    """
    设置日志记录
    
    Args:
        log_file: 日志文件路径，如果为None则不写入文件
        log_level: 日志级别
        enable_console: 是否启用控制台输出
        enable_colors: 是否启用颜色输出
        
    Returns:
        配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger("ParadoxModTranslator")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger.level)
        
        if enable_colors:
            console_formatter = ColoredFormatter(log_format, date_format)
        else:
            console_formatter = logging.Formatter(log_format, date_format)
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        try:
            # 确保日志目录存在
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logger.level)
            
            file_formatter = logging.Formatter(log_format, date_format)
            file_handler.setFormatter(file_formatter)
            
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"无法创建日志文件 {log_file}: {e}")
    
    return logger


class ApplicationLogger:
    """应用程序日志记录器包装类"""
    
    def __init__(self, logger_name: str = "ParadoxModTranslator"):
        """
        初始化应用程序日志记录器
        
        Args:
            logger_name: 日志记录器名称
        """
        self.logger = logging.getLogger(logger_name)
        self._log_callbacks = []
    
    def add_log_callback(self, callback):
        """
        添加日志回调函数
        
        Args:
            callback: 回调函数，接收(message, level)参数
        """
        self._log_callbacks.append(callback)
    
    def remove_log_callback(self, callback):
        """
        移除日志回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._log_callbacks:
            self._log_callbacks.remove(callback)
    
    def log_message(self, message: str, level: str = "info"):
        """
        记录日志消息
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        # 标准日志记录
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)
        
        # 调用回调函数
        for callback in self._log_callbacks:
            try:
                callback(message, level)
            except Exception as e:
                self.logger.error(f"日志回调函数执行失败: {e}")
    
    def debug(self, message: str):
        """记录调试信息"""
        self.log_message(message, "debug")
    
    def info(self, message: str):
        """记录信息"""
        self.log_message(message, "info")
    
    def warning(self, message: str):
        """记录警告"""
        self.log_message(message, "warn")
    
    def error(self, message: str):
        """记录错误"""
        self.log_message(message, "error")


def create_session_log_file() -> str:
    """
    创建会话日志文件路径
    
    Returns:
        日志文件路径
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"translator_{timestamp}.log")


def get_log_file_size(log_file: str) -> int:
    """
    获取日志文件大小
    
    Args:
        log_file: 日志文件路径
        
    Returns:
        文件大小（字节），如果文件不存在返回0
    """
    try:
        return os.path.getsize(log_file)
    except (OSError, FileNotFoundError):
        return 0


def rotate_log_file(log_file: str, max_size: int = 10 * 1024 * 1024) -> bool:
    """
    轮转日志文件
    
    Args:
        log_file: 日志文件路径
        max_size: 最大文件大小（字节），默认10MB
        
    Returns:
        是否进行了轮转
    """
    if not os.path.exists(log_file):
        return False
    
    if get_log_file_size(log_file) > max_size:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{log_file}.{timestamp}.bak"
            os.rename(log_file, backup_file)
            return True
        except Exception:
            return False
    
    return False


def cleanup_old_logs(log_dir: str = "logs", max_age_days: int = 30) -> int:
    """
    清理旧的日志文件
    
    Args:
        log_dir: 日志目录
        max_age_days: 最大保留天数
        
    Returns:
        删除的文件数量
    """
    if not os.path.exists(log_dir):
        return 0
    
    deleted_count = 0
    current_time = datetime.now().timestamp()
    max_age_seconds = max_age_days * 24 * 3600
    
    try:
        for filename in os.listdir(log_dir):
            if filename.endswith(('.log', '.bak')):
                file_path = os.path.join(log_dir, filename)
                file_age = current_time - os.path.getmtime(file_path)
                
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    deleted_count += 1
    except Exception:
        pass
    
    return deleted_count

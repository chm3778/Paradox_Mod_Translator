"""
应用程序常量定义

包含所有全局常量和配置参数
"""

import threading

# 全局API锁
GEMINI_API_LOCK = threading.RLock()

# 每分钟令牌数(TPM)定义
MODEL_TPM = {
    "models/gemini-2.0-flash-lite": 1000000,
    "models/gemini-2.0-flash": 1000000,
}

# 每分钟请求数(RPM)定义
MODEL_RPM = {
    "models/gemini-2.0-flash-lite": 30,
    "models/gemini-2.0-flash": 15,
}

# 配置文件相关常量
CONFIG_FILE = "translator_config.json"
DEFAULT_API_KEY_PLACEHOLDER = "YOUR_GEMINI_API_KEY"
DEFAULT_PLACEHOLDER_PATTERNS = [
    r'(\$.*?\$)',
    r'(\[.*?\])',
    r'(@\w+!)',
    r'(#\w+(?:;\w+)*.*?#!|\S*#!)'
]

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    "english": "英语",
    "simp_chinese": "简体中文",
    "trad_chinese": "繁体中文",
    "japanese": "日语",
    "korean": "韩语",
    "french": "法语",
    "german": "德语",
    "spanish": "西班牙语",
    "russian": "俄语"
}

# Gemini模型列表
GEMINI_MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest", 
    "models/gemini-2.0-flash-lite",
    "models/gemini-2.0-flash"
]

# API密钥轮换策略
KEY_ROTATION_STRATEGIES = {
    "round_robin": "轮询",
    "load_balanced": "负载均衡", 
    "priority": "优先级"
}

# 日志级别
LOG_LEVELS = {
    "debug": "调试",
    "info": "信息",
    "warn": "警告", 
    "error": "错误"
}

# UI相关常量
DEFAULT_WINDOW_SIZE = "1200x800"
MIN_WINDOW_SIZE = (800, 600)
PROGRESS_UPDATE_INTERVAL = 100  # 毫秒

# 翻译相关常量
MAX_RETRIES = 3
BACKOFF_TIMES = [2, 4, 8]  # 指数退避时间
DEFAULT_API_DELAY = 3.0
MAX_API_DELAY = 10.0
DEFAULT_CONCURRENT_TASKS = 3
MAX_CONCURRENT_TASKS = 10

# 文件处理常量
SUPPORTED_FILE_EXTENSIONS = ['.yml', '.yaml']
ENCODING = 'utf-8-sig'

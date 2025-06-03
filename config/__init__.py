"""
配置管理模块

提供应用程序配置管理功能，包括：
- 配置文件读写
- 默认值管理
- 配置验证
"""

from .config_manager import ConfigManager
from .constants import *

__all__ = ['ConfigManager', 'DEFAULT_API_KEY_PLACEHOLDER', 'GEMINI_API_LOCK', 'MODEL_TPM', 'MODEL_RPM']

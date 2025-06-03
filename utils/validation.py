"""
输入验证工具

提供各种输入验证功能
"""

import os
import re
from typing import List, Optional, Tuple


def validate_api_key(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    验证API密钥格式
    
    Args:
        api_key: API密钥
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not api_key:
        return False, "API密钥不能为空"
    
    if api_key == "YOUR_GEMINI_API_KEY":
        return False, "请设置真实的API密钥"
    
    # Gemini API密钥通常以AIza开头
    if not api_key.startswith("AIza"):
        return False, "Gemini API密钥格式不正确，应以'AIza'开头"
    
    # 检查长度（通常为39个字符）
    if len(api_key) != 39:
        return False, f"API密钥长度不正确，期望39个字符，实际{len(api_key)}个字符"
    
    # 检查字符集（字母、数字、下划线、连字符）
    if not re.match(r'^[A-Za-z0-9_-]+$', api_key):
        return False, "API密钥包含无效字符"
    
    return True, None


def validate_file_path(file_path: str, must_exist: bool = True) -> Tuple[bool, Optional[str]]:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        must_exist: 文件是否必须存在
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not file_path:
        return False, "文件路径不能为空"
    
    # 检查路径格式
    try:
        normalized_path = os.path.normpath(file_path)
    except Exception as e:
        return False, f"文件路径格式无效: {e}"
    
    if must_exist:
        if not os.path.exists(normalized_path):
            return False, f"文件不存在: {normalized_path}"
        
        if not os.path.isfile(normalized_path):
            return False, f"路径不是文件: {normalized_path}"
    else:
        # 检查父目录是否存在
        parent_dir = os.path.dirname(normalized_path)
        if parent_dir and not os.path.exists(parent_dir):
            return False, f"父目录不存在: {parent_dir}"
    
    return True, None


def validate_directory_path(dir_path: str, must_exist: bool = True) -> Tuple[bool, Optional[str]]:
    """
    验证目录路径
    
    Args:
        dir_path: 目录路径
        must_exist: 目录是否必须存在
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not dir_path:
        return False, "目录路径不能为空"
    
    # 检查路径格式
    try:
        normalized_path = os.path.normpath(dir_path)
    except Exception as e:
        return False, f"目录路径格式无效: {e}"
    
    if must_exist:
        if not os.path.exists(normalized_path):
            return False, f"目录不存在: {normalized_path}"
        
        if not os.path.isdir(normalized_path):
            return False, f"路径不是目录: {normalized_path}"
    
    return True, None


def validate_language_code(language_code: str) -> Tuple[bool, Optional[str]]:
    """
    验证语言代码
    
    Args:
        language_code: 语言代码
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not language_code:
        return False, "语言代码不能为空"
    
    # 检查格式（字母、数字、下划线）
    if not re.match(r'^[a-zA-Z0-9_]+$', language_code):
        return False, "语言代码只能包含字母、数字和下划线"
    
    # 检查长度
    if len(language_code) < 2 or len(language_code) > 20:
        return False, "语言代码长度应在2-20个字符之间"
    
    return True, None


def validate_model_name(model_name: str, available_models: List[str]) -> Tuple[bool, Optional[str]]:
    """
    验证模型名称
    
    Args:
        model_name: 模型名称
        available_models: 可用模型列表
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not model_name:
        return False, "模型名称不能为空"
    
    if model_name not in available_models:
        return False, f"不支持的模型: {model_name}"
    
    return True, None


def validate_concurrent_tasks(num_tasks: int) -> Tuple[bool, Optional[str]]:
    """
    验证并发任务数
    
    Args:
        num_tasks: 并发任务数
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not isinstance(num_tasks, int):
        return False, "并发任务数必须是整数"
    
    if num_tasks < 1:
        return False, "并发任务数不能小于1"
    
    if num_tasks > 10:
        return False, "并发任务数不能大于10"
    
    return True, None


def validate_api_delay(delay: float) -> Tuple[bool, Optional[str]]:
    """
    验证API调用延迟
    
    Args:
        delay: 延迟时间（秒）
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not isinstance(delay, (int, float)):
        return False, "API延迟必须是数字"
    
    if delay < 0:
        return False, "API延迟不能为负数"
    
    if delay > 60:
        return False, "API延迟不能超过60秒"
    
    return True, None


def validate_yml_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    验证YML文件
    
    Args:
        file_path: YML文件路径
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    # 首先验证文件路径
    is_valid, error = validate_file_path(file_path, must_exist=True)
    if not is_valid:
        return is_valid, error
    
    # 检查文件扩展名
    if not file_path.lower().endswith(('.yml', '.yaml')):
        return False, "文件必须是YML格式（.yml或.yaml扩展名）"
    
    # 检查文件大小（避免过大的文件）
    try:
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:  # 100MB
            return False, "文件过大（超过100MB）"
    except Exception as e:
        return False, f"无法获取文件大小: {e}"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除或替换不安全字符
    unsafe_chars = r'<>:"/\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # 移除前后空格和点
    filename = filename.strip(' .')
    
    # 确保文件名不为空
    if not filename:
        filename = "unnamed"
    
    # 限制长度
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename


def validate_text_length(text: str, max_length: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    验证文本长度
    
    Args:
        text: 要验证的文本
        max_length: 最大长度
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if len(text) > max_length:
        return False, f"文本长度超过限制（{len(text)} > {max_length}）"
    
    return True, None


def validate_config_value(key: str, value, expected_type) -> Tuple[bool, Optional[str]]:
    """
    验证配置值
    
    Args:
        key: 配置键
        value: 配置值
        expected_type: 期望的类型
        
    Returns:
        (是否有效, 错误信息) 的元组
    """
    if not isinstance(value, expected_type):
        return False, f"配置项 {key} 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
    
    return True, None

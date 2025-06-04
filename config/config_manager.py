"""
配置管理器

负责应用程序配置的读取、保存和管理
"""

import json
import os
from typing import Any, Dict, List, Optional
from .constants import DEFAULT_API_KEY_PLACEHOLDER, DEFAULT_PLACEHOLDER_PATTERNS


class ConfigManager:
    """应用程序配置管理器"""
    
    def __init__(self, config_file_path: str):
        """
        初始化配置管理器
        
        Args:
            config_file_path: 配置文件路径
        """
        self.config_file_path = config_file_path
        self.defaults = {
            "source_language": "english",
            "target_language": "simp_chinese",
            "game_mod_style": "General video game localization, maintain tone of original.",
            "selected_model": "gemini-1.5-flash-latest",
            "localization_root_path": "",
            "api_keys": [DEFAULT_API_KEY_PLACEHOLDER],
            "api_call_delay": 3.0,
            "max_concurrent_tasks": 3,
            "auto_review_mode": True,
            "delayed_review": True,
            "key_rotation_strategy": "round_robin",
            "placeholder_patterns": DEFAULT_PLACEHOLDER_PATTERNS
            "use_translation_memory": True

        }
        self.config = self.load_config()
        self._migrate_legacy_api_key()

    def load_config(self) -> Dict[str, Any]:
        """
        从文件加载配置
        
        Returns:
            配置字典
        """
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 确保所有默认键都存在
                for key, default_value in self.defaults.items():
                    if key not in loaded_config:
                        loaded_config[key] = default_value
                return loaded_config
        except FileNotFoundError:
            print(f"配置文件未找到: {self.config_file_path}. 使用默认配置创建.")
            return self.defaults.copy()
        except json.JSONDecodeError:
            print(f"配置文件JSON解析错误: {self.config_file_path}. 使用默认配置.")
            return self.defaults.copy()
        except Exception as e:
            print(f"加载配置时发生错误: {e}. 使用默认配置.")
            return self.defaults.copy()

    def save_config(self) -> bool:
        """
        保存配置到文件

        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在（只有当路径包含目录时才创建）
            config_dir = os.path.dirname(self.config_file_path)
            if config_dir:  # 如果有目录部分
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置时发生错误: {e}")
            return False

    def get_setting(self, key: str, default_override: Optional[Any] = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键
            default_override: 覆盖默认值
            
        Returns:
            配置值
        """
        if default_override is not None:
            return self.config.get(key, default_override)
        return self.config.get(key, self.defaults.get(key))
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        设置配置项并立即保存
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否设置成功
        """
        self.config[key] = value
        return self.save_config()
        
    def get_api_keys(self) -> List[str]:
        """
        获取所有有效的API密钥
        
        Returns:
            有效API密钥列表
        """
        keys = self.get_setting("api_keys", [DEFAULT_API_KEY_PLACEHOLDER])
        if not isinstance(keys, list):
            keys = [keys] if keys else []
        
        # 过滤掉空密钥和占位符密钥
        valid_keys = [k for k in keys if k and k != DEFAULT_API_KEY_PLACEHOLDER]
        return valid_keys
    
    def add_api_key(self, new_key: str) -> bool:
        """
        添加新的API密钥
        
        Args:
            new_key: 新的API密钥
            
        Returns:
            是否添加成功
        """
        if not new_key or new_key == DEFAULT_API_KEY_PLACEHOLDER:
            return False
            
        keys = self.get_setting("api_keys", [])
        if not isinstance(keys, list):
            keys = [keys] if keys else []
            
        # 避免重复添加
        if new_key not in keys:
            keys.append(new_key)
            return self.set_setting("api_keys", keys)
        return False
    
    def remove_api_key(self, key_to_remove: str) -> bool:
        """
        移除指定的API密钥
        
        Args:
            key_to_remove: 要移除的API密钥
            
        Returns:
            是否移除成功
        """
        keys = self.get_setting("api_keys", [])
        if not isinstance(keys, list):
            keys = [keys] if keys else []
            
        if key_to_remove in keys:
            keys.remove(key_to_remove)
            # 如果移除后列表为空，添加一个占位符
            if not keys:
                keys = [DEFAULT_API_KEY_PLACEHOLDER]
            return self.set_setting("api_keys", keys)
        return False
    
    def update_api_key(self, old_key: str, new_key: str) -> bool:
        """
        更新API密钥
        
        Args:
            old_key: 旧的API密钥
            new_key: 新的API密钥
            
        Returns:
            是否更新成功
        """
        if not new_key or new_key == DEFAULT_API_KEY_PLACEHOLDER:
            return False
            
        keys = self.get_setting("api_keys", [])
        if not isinstance(keys, list):
            keys = [keys] if keys else []
            
        if old_key in keys:
            index = keys.index(old_key)
            keys[index] = new_key
            return self.set_setting("api_keys", keys)
        return False

    def _migrate_legacy_api_key(self) -> None:
        """将旧版单API密钥配置转换为新版多密钥配置"""
        if "api_key" in self.config:
            # 如果存在旧版api_key，进行迁移
            legacy_key = self.config.pop("api_key")
            if legacy_key and legacy_key != DEFAULT_API_KEY_PLACEHOLDER:
                # 如果已经有api_keys，添加到列表中；否则创建新列表
                if "api_keys" in self.config:
                    if isinstance(self.config["api_keys"], list):
                        if legacy_key not in self.config["api_keys"]:
                            self.config["api_keys"].append(legacy_key)
                    else:
                        self.config["api_keys"] = [self.config["api_keys"], legacy_key]
                else:
                    self.config["api_keys"] = [legacy_key]
            else:
                # 如果旧密钥是占位符或空，确保有默认的api_keys
                if "api_keys" not in self.config:
                    self.config["api_keys"] = [DEFAULT_API_KEY_PLACEHOLDER]
            self.save_config()
            print("已将旧版API密钥配置迁移到新版多密钥配置")

        # 确保api_keys始终是一个列表
        if "api_keys" in self.config and not isinstance(self.config["api_keys"], list):
            self.config["api_keys"] = [self.config["api_keys"]]
            self.save_config()

    def validate_config(self) -> List[str]:
        """
        验证配置的有效性
        
        Returns:
            错误信息列表，空列表表示配置有效
        """
        errors = []
        
        # 验证API密钥
        api_keys = self.get_api_keys()
        if not api_keys:
            errors.append("未配置有效的API密钥")
        
        # 验证并发任务数
        max_tasks = self.get_setting("max_concurrent_tasks", 3)
        if not isinstance(max_tasks, int) or max_tasks < 1 or max_tasks > 10:
            errors.append("并发任务数必须在1-10之间")
        
        # 验证API调用延迟
        delay = self.get_setting("api_call_delay", 3.0)
        if not isinstance(delay, (int, float)) or delay < 0:
            errors.append("API调用延迟必须为非负数")
        
        return errors

    def reset_to_defaults(self) -> bool:
        """
        重置配置为默认值
        
        Returns:
            是否重置成功
        """
        self.config = self.defaults.copy()
        return self.save_config()

    def export_config(self, export_path: str) -> bool:
        """
        导出配置到指定文件
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"导出配置时发生错误: {e}")
            return False

    def import_config(self, import_path: str) -> bool:
        """
        从指定文件导入配置
        
        Args:
            import_path: 导入文件路径
            
        Returns:
            是否导入成功
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 验证导入的配置
            temp_config = self.config
            self.config = imported_config
            errors = self.validate_config()
            
            if errors:
                self.config = temp_config
                print(f"导入的配置无效: {'; '.join(errors)}")
                return False
            
            return self.save_config()
        except Exception as e:
            print(f"导入配置时发生错误: {e}")
            return False

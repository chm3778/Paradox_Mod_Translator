"""
AI模型管理器

负责获取和管理可用的AI模型列表
"""

import threading
import time
from typing import List, Optional, Dict, Any
from config.config_manager import ConfigManager

# 尝试导入Gemini库
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class ModelManager:
    """AI模型管理器，负责获取和缓存可用模型列表"""
    
    def __init__(self, config_manager: ConfigManager, app_ref: Any = None):
        """
        初始化模型管理器
        
        Args:
            config_manager: 配置管理器
            app_ref: 应用程序引用（用于日志记录）
        """
        self.config_manager = config_manager
        self.app_ref = app_ref
        self.lock = threading.RLock()
        
        # 默认模型列表
        self.default_models = [
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro-latest", 
            "models/gemini-2.0-flash-lite",
            "models/gemini-2.0-flash"
        ]
        
        # 缓存的模型列表
        self.cached_models: List[str] = []
        self.cache_timestamp: float = 0
        self.cache_duration: float = 300  # 5分钟缓存
        
        # 获取状态
        self.is_fetching = False
        self.last_fetch_error: Optional[str] = None
    
    def get_available_models(self, force_refresh: bool = False) -> List[str]:
        """
        获取可用的AI模型列表
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            可用模型列表
        """
        with self.lock:
            # 检查缓存是否有效
            if not force_refresh and self._is_cache_valid():
                return self.cached_models if self.cached_models else self.default_models
            
            # 尝试从API获取模型列表
            api_models = self._fetch_models_from_api()
            
            if api_models:
                self.cached_models = api_models
                self.cache_timestamp = time.time()
                self.last_fetch_error = None
                self._log_message(f"成功获取 {len(api_models)} 个可用模型", "info")
                return api_models
            else:
                # 如果API获取失败，返回默认列表
                self._log_message("使用默认模型列表", "warn")
                return self.default_models
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.cached_models:
            return False
        
        current_time = time.time()
        return (current_time - self.cache_timestamp) < self.cache_duration
    
    def _fetch_models_from_api(self) -> Optional[List[str]]:
        """
        从API获取模型列表
        
        Returns:
            模型列表，如果获取失败则返回None
        """
        if not GEMINI_AVAILABLE:
            self._log_message("Gemini API库不可用，无法获取模型列表", "warn")
            return None
        
        # 检查是否有有效的API密钥
        api_keys = self.config_manager.get_api_keys()
        valid_keys = [key for key in api_keys if key != "YOUR_GEMINI_API_KEY" and key.strip()]
        
        if not valid_keys:
            self._log_message("没有有效的API密钥，无法获取模型列表", "warn")
            return None
        
        # 防止并发获取
        if self.is_fetching:
            self._log_message("正在获取模型列表，请稍候...", "debug")
            return None
        
        self.is_fetching = True
        
        try:
            # 使用第一个有效的API密钥
            api_key = valid_keys[0]
            genai.configure(api_key=api_key)
            
            self._log_message("正在从Gemini API获取可用模型列表...", "info")
            
            # 获取模型列表
            models = []
            for model in genai.list_models():
                # 只包含支持generateContent的模型
                if 'generateContent' in model.supported_generation_methods:
                    models.append(model.name)
            
            if models:
                # 过滤和排序模型
                filtered_models = self._filter_and_sort_models(models)
                self._log_message(f"从API获取到 {len(filtered_models)} 个可用模型", "info")
                return filtered_models
            else:
                self._log_message("API返回的模型列表为空", "warn")
                return None
                
        except Exception as e:
            error_msg = f"获取模型列表失败: {e}"
            self.last_fetch_error = error_msg
            self._log_message(error_msg, "error")
            return None
        finally:
            self.is_fetching = False
    
    def _filter_and_sort_models(self, models: List[str]) -> List[str]:
        """
        过滤和排序模型列表
        
        Args:
            models: 原始模型列表
            
        Returns:
            过滤和排序后的模型列表
        """
        # 过滤出Gemini模型
        gemini_models = [model for model in models if 'gemini' in model.lower()]
        
        # 按优先级排序
        priority_order = [
            'gemini-1.5-flash-latest',
            'gemini-1.5-pro-latest',
            'gemini-2.0-flash-lite',
            'gemini-2.0-flash',
            'gemini-1.5-flash',
            'gemini-1.5-pro'
        ]
        
        sorted_models = []
        
        # 首先添加优先级模型
        for priority_model in priority_order:
            for model in gemini_models:
                if priority_model in model:
                    if model not in sorted_models:
                        sorted_models.append(model)
        
        # 然后添加其他模型
        for model in gemini_models:
            if model not in sorted_models:
                sorted_models.append(model)
        
        return sorted_models
    
    def refresh_models_async(self, callback: Optional[callable] = None):
        """
        异步刷新模型列表
        
        Args:
            callback: 完成后的回调函数，参数为(models: List[str], error: Optional[str])
        """
        def _refresh_worker():
            try:
                models = self.get_available_models(force_refresh=True)
                if callback:
                    callback(models, None)
            except Exception as e:
                error_msg = f"异步刷新模型列表失败: {e}"
                self._log_message(error_msg, "error")
                if callback:
                    callback(self.default_models, error_msg)
        
        refresh_thread = threading.Thread(target=_refresh_worker, daemon=True)
        refresh_thread.start()
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        获取模型信息
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型信息字典
        """
        info = {
            "name": model_name,
            "display_name": self._get_model_display_name(model_name),
            "description": self._get_model_description(model_name),
            "is_available": model_name in self.get_available_models()
        }
        return info
    
    def _get_model_display_name(self, model_name: str) -> str:
        """获取模型显示名称"""
        display_names = {
            "gemini-1.5-flash-latest": "Gemini 1.5 Flash (最新)",
            "gemini-1.5-pro-latest": "Gemini 1.5 Pro (最新)",
            "models/gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
            "models/gemini-2.0-flash": "Gemini 2.0 Flash"
        }
        return display_names.get(model_name, model_name)
    
    def _get_model_description(self, model_name: str) -> str:
        """获取模型描述"""
        descriptions = {
            "gemini-1.5-flash-latest": "快速响应，适合大量翻译任务",
            "gemini-1.5-pro-latest": "高质量翻译，适合重要内容",
            "models/gemini-2.0-flash-lite": "轻量版本，速度更快",
            "models/gemini-2.0-flash": "最新版本，平衡速度和质量"
        }
        return descriptions.get(model_name, "Gemini AI模型")
    
    def _log_message(self, message: str, level: str = "info"):
        """记录日志消息"""
        if self.app_ref and hasattr(self.app_ref, 'log_message'):
            self.app_ref.log_message(f"模型管理器: {message}", level)
        else:
            print(f"[{level.upper()}] 模型管理器: {message}")
    
    def clear_cache(self):
        """清除缓存"""
        with self.lock:
            self.cached_models = []
            self.cache_timestamp = 0
            self._log_message("模型缓存已清除", "info")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态"""
        with self.lock:
            return {
                "cached_models_count": len(self.cached_models),
                "cache_valid": self._is_cache_valid(),
                "cache_age": time.time() - self.cache_timestamp if self.cache_timestamp > 0 else 0,
                "is_fetching": self.is_fetching,
                "last_error": self.last_fetch_error
            }

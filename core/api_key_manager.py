"""
API密钥管理器

负责管理多个API密钥，提供负载均衡和故障转移功能
"""

import time
import threading
from typing import Dict, List, Set, Optional, Any
from config.config_manager import ConfigManager


class APIKeyManager:
    """管理多个API密钥，提供负载均衡和故障转移功能"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化API密钥管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.keys: List[str] = []  # 有效的API密钥列表
        self.key_stats: Dict[str, Dict[str, Any]] = {}  # 每个密钥的使用统计
        self.current_index = 0  # 当前使用的密钥索引
        self.failed_keys: Set[str] = set()  # 失败的密钥集合
        self.key_locks: Dict[str, threading.RLock] = {}  # 每个密钥的锁
        self.global_lock = threading.RLock()  # 全局锁
        self.reload_keys()
    
    def reload_keys(self) -> None:
        """从配置中重新加载API密钥"""
        with self.global_lock:
            self.keys = self.config_manager.get_api_keys()
            
            # 初始化新密钥的统计信息和锁
            for key in self.keys:
                if key not in self.key_stats:
                    self.key_stats[key] = {
                        "usage_count": 0,  # 使用次数
                        "success_count": 0,  # 成功次数
                        "failure_count": 0,  # 失败次数
                        "last_used": 0,  # 上次使用时间
                        "token_usage": [],  # 最近的token使用量
                        "avg_tokens": 0,  # 平均token使用量
                    }
                if key not in self.key_locks:
                    self.key_locks[key] = threading.RLock()
            
            # 清理不再存在的密钥的统计信息和锁
            keys_to_remove = [k for k in self.key_stats if k not in self.keys]
            for k in keys_to_remove:
                if k in self.key_stats:
                    del self.key_stats[k]
                if k in self.key_locks:
                    del self.key_locks[k]
            
            # 重置失败密钥集合，给所有密钥一个新的机会
            self.failed_keys = set()
            
            # 重置当前索引
            self.current_index = 0
    
    def get_next_key(self, strategy: Optional[str] = None) -> Optional[str]:
        """
        根据策略获取下一个要使用的API密钥
        
        Args:
            strategy: 密钥选择策略，可选值：round_robin, load_balanced, priority
            
        Returns:
            API密钥，如果没有可用密钥则返回None
        """
        with self.global_lock:
            if not self.keys:
                return None
                
            # 如果所有密钥都失败了，重置失败状态并给它们一个新的机会
            if len(self.failed_keys) >= len(self.keys):
                self.failed_keys = set()
            
            # 过滤掉已知失败的密钥
            available_keys = [k for k in self.keys if k not in self.failed_keys]
            if not available_keys:
                return None
                
            # 如果未指定策略，使用配置中的策略
            if not strategy:
                strategy = self.config_manager.get_setting("key_rotation_strategy", "round_robin")
            
            if strategy == "round_robin":
                # 简单的轮询策略
                key = available_keys[self.current_index % len(available_keys)]
                self.current_index = (self.current_index + 1) % len(available_keys)
                
            elif strategy == "load_balanced":
                # 负载均衡策略：选择使用次数最少的密钥
                key = min(available_keys, key=lambda k: self.key_stats[k]["usage_count"])
                
            elif strategy == "priority":
                # 优先级策略：总是使用列表中的第一个可用密钥
                key = available_keys[0]
                
            else:
                # 默认使用轮询策略
                key = available_keys[self.current_index % len(available_keys)]
                self.current_index = (self.current_index + 1) % len(available_keys)
            
            # 更新密钥使用统计
            with self.key_locks[key]:
                self.key_stats[key]["usage_count"] += 1
                self.key_stats[key]["last_used"] = time.time()
            
            return key
    
    def mark_key_success(self, key: str, token_count: Optional[int] = None) -> None:
        """
        标记密钥使用成功
        
        Args:
            key: API密钥
            token_count: 本次使用的token数量
        """
        if key in self.key_stats:
            with self.key_locks[key]:
                self.key_stats[key]["success_count"] += 1
                
                # 更新token使用统计
                if token_count:
                    # 保留最近10次的token使用量
                    token_history = self.key_stats[key]["token_usage"]
                    token_history.append(token_count)
                    if len(token_history) > 10:
                        token_history = token_history[-10:]
                    self.key_stats[key]["token_usage"] = token_history
                    
                    # 更新平均token使用量
                    self.key_stats[key]["avg_tokens"] = sum(token_history) / len(token_history)
                
                # 如果密钥之前失败过，现在成功了，从失败集合中移除
                with self.global_lock:
                    if key in self.failed_keys:
                        self.failed_keys.remove(key)
    
    def mark_key_failure(self, key: str, error_type: Optional[str] = None) -> None:
        """
        标记密钥使用失败
        
        Args:
            key: API密钥
            error_type: 错误类型
        """
        if key in self.key_stats:
            with self.key_locks[key]:
                self.key_stats[key]["failure_count"] += 1
                
                # 根据错误类型决定是否将密钥标记为失败
                with self.global_lock:
                    if error_type in ["API_KEY_INVALID", "API_KEY_MISSING", "Malformed"]:
                        # 密钥无效，添加到失败集合
                        self.failed_keys.add(key)
                    elif error_type in ["Rate limit exceeded", "429", "quota exceeded"]:
                        # 速率限制错误，暂时添加到失败集合，但可以在一段时间后重试
                        self.failed_keys.add(key)
    
    def get_key_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有密钥的使用统计
        
        Returns:
            密钥统计信息字典
        """
        with self.global_lock:
            return {k: v.copy() for k, v in self.key_stats.items()}
    
    def has_valid_keys(self) -> bool:
        """
        检查是否有有效的API密钥
        
        Returns:
            是否有有效密钥
        """
        with self.global_lock:
            return len(self.keys) > 0 and len(self.keys) > len(self.failed_keys)
    
    def get_all_keys(self) -> List[str]:
        """
        获取所有API密钥
        
        Returns:
            所有API密钥列表
        """
        with self.global_lock:
            return self.keys.copy()

    def reset_failed_keys(self) -> None:
        """重置失败的密钥状态，给它们重新尝试的机会"""
        with self.global_lock:
            self.failed_keys.clear()

    def get_available_keys_count(self) -> int:
        """
        获取可用密钥数量
        
        Returns:
            可用密钥数量
        """
        with self.global_lock:
            return len([k for k in self.keys if k not in self.failed_keys])

    def get_key_performance_summary(self) -> Dict[str, Any]:
        """
        获取密钥性能摘要
        
        Returns:
            性能摘要字典
        """
        with self.global_lock:
            total_usage = sum(stats["usage_count"] for stats in self.key_stats.values())
            total_success = sum(stats["success_count"] for stats in self.key_stats.values())
            total_failure = sum(stats["failure_count"] for stats in self.key_stats.values())
            
            success_rate = (total_success / total_usage * 100) if total_usage > 0 else 0
            
            return {
                "total_keys": len(self.keys),
                "available_keys": self.get_available_keys_count(),
                "failed_keys": len(self.failed_keys),
                "total_usage": total_usage,
                "total_success": total_success,
                "total_failure": total_failure,
                "success_rate": success_rate
            }

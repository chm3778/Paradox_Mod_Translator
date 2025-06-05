"""
并行翻译器

管理多个翻译器实例的并行翻译任务
"""

import queue
import threading
import time
import traceback
from typing import Dict, List, Optional, Any, Callable

from config.config_manager import ConfigManager
from .api_key_manager import APIKeyManager
from .gemini_translator import GeminiTranslator


class ParallelTranslator:
    """并行翻译器，管理多个API密钥的并行调用"""
    
    def __init__(self, app_ref: Any, config_manager: ConfigManager):
        """
        初始化并行翻译器
        
        Args:
            app_ref: 应用程序引用
            config_manager: 配置管理器
        """
        self.app_ref = app_ref
        self.config_manager = config_manager
        self.api_key_manager = APIKeyManager(config_manager)
        self.translators: Dict[str, GeminiTranslator] = {}  # 翻译器字典
        self.translation_queue = queue.Queue()  # 待翻译文本队列
        self.result_queue = queue.Queue()  # 翻译结果队列
        self.pending_reviews: Dict[str, Any] = {}  # 待评审的翻译
        self.workers: List[threading.Thread] = []  # 工作线程列表
        self.stop_flag = threading.Event()  # 停止标志
        self.lock = threading.RLock()  # 全局锁
        self.init_translators()
        
    def init_translators(self) -> None:
        """初始化翻译器实例"""
        with self.lock:
            # 清空现有翻译器
            self.translators.clear()
            self.app_ref.log_message("并行翻译器：正在清理旧的翻译器实例...", "debug")

            # 获取并行工作线程数
            num_workers = self.config_manager.get_setting("max_concurrent_tasks", 3)

            for i in range(num_workers):
                translator_id = f"parallel_translator-{i+1}"
                self.translators[translator_id] = GeminiTranslator(
                    self.app_ref,
                    translator_id=translator_id
                )
                self.app_ref.log_message(f"并行翻译器：已初始化翻译器 {translator_id}", "info")
    
    def start_workers(self, num_workers: Optional[int] = None) -> None:
        """
        启动工作线程
        
        Args:
            num_workers: 工作线程数量，如果为None则使用配置值
        """
        if num_workers is None:
            num_workers = self.config_manager.get_setting("max_concurrent_tasks", 3)

        # 确保num_workers是整数
        num_workers = int(num_workers) if num_workers is not None else 3
        
        with self.lock:
            # 停止现有工作线程
            self.stop_workers()
            
            # 清空标志
            self.stop_flag.clear()
            
            # 创建新的工作线程
            self.workers = []
            for i in range(num_workers):
                worker = threading.Thread(
                    target=self._worker_thread,
                    args=(i,),
                    daemon=True
                )
                self.workers.append(worker)
                worker.start()
                self.app_ref.log_message(f"启动工作线程 {i+1}/{num_workers}", "info")
    
    def stop_workers(self) -> None:
        """停止所有工作线程"""
        with self.lock:
            if not self.workers:
                return
                
            # 设置停止标志
            self.stop_flag.set()
            
            # 等待所有工作线程结束
            for i, worker in enumerate(self.workers):
                if worker.is_alive():
                    self.app_ref.log_message(f"等待工作线程 {i+1} 结束...", "info")
                    worker.join(1.0)  # 等待最多1秒
            
            # 清空工作线程列表
            self.workers = []
            
            # 清空队列
            while not self.translation_queue.empty():
                try:
                    self.translation_queue.get_nowait()
                except queue.Empty:
                    break
    
    def _worker_thread(self, worker_id: int) -> None:
        """
        工作线程函数
        
        Args:
            worker_id: 工作线程ID
        """
        self.app_ref.log_message(f"工作线程 {worker_id} 开始运行", "debug")
        
        # 为每个工作线程获取一个独立的翻译器实例
        translator_instance_id = f"parallel_translator-{worker_id+1}"
        translator = self.translators.get(translator_instance_id)
        if not translator:
            self.app_ref.log_message(
                f"工作线程 {worker_id}: 严重错误 - 未找到翻译器实例 {translator_instance_id}。线程将退出。", 
                "error"
            )
            return

        while not self.stop_flag.is_set():
            task = None
            api_key = None
            try:
                try:
                    task = self.translation_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # 获取API密钥
                api_key = self.api_key_manager.get_next_key()
                if not api_key:
                    self.app_ref.log_message(
                        f"工作线程 {worker_id}: 无可用API密钥，将任务放回队列并等待。", 
                        "error"
                    )
                    self.translation_queue.put(task)
                    time.sleep(5.0) 
                    continue
                
                self.app_ref.log_message(
                    f"工作线程 {worker_id} 使用API密钥 ...{api_key[-4:]} 翻译: {task.get('text', '')[:30]}...", 
                    "debug"
                )
                
                # 应用基础延迟
                base_delay = float(self.config_manager.get_setting("api_call_delay", 3.0))
                self.app_ref.log_message(
                    f"工作线程 {worker_id}: 应用基础延迟 {base_delay:.1f} 秒 (来自配置)", 
                    "debug"
                )
                time.sleep(base_delay)

                # 执行翻译
                translated_text, token_count, error_type = translator.translate(
                    task["text"],
                    task["source_lang"],
                    task["target_lang"],
                    task["game_mod_style"],
                    task["model_name"],
                    api_key_to_use=api_key
                )
                
                # 更新API密钥统计
                if error_type is None and translated_text is not None:
                    self.api_key_manager.mark_key_success(
                        api_key, 
                        token_count if isinstance(token_count, int) else 0
                    )
                else:
                    actual_error_type = error_type if error_type else "translation_failed_or_unchanged"
                    self.api_key_manager.mark_key_failure(api_key, actual_error_type)
                
                # 将结果放入结果队列
                self.result_queue.put({
                    "entry_id": task["entry_id"],
                    "original_text": task["text"],
                    "translated_text": translated_text,
                    "token_count": token_count,
                    "api_error_type": error_type,
                    "original_line_content": task.get("original_line_content"),
                    "source_lang": task["source_lang"]
                })
                
            except Exception as e:
                self.app_ref.log_message(f"工作线程 {worker_id} 发生异常: {e}", "error")
                self.app_ref.log_message(f"异常详情: {traceback.format_exc()}", "debug")
                
                # 如果任务已获取，将其放回队列
                if task:
                    self.translation_queue.put(task)
                
                # 如果API密钥已分配，标记为失败
                if 'api_key' in locals() and api_key:
                    error_type_for_key_manager = str(e)
                    self.api_key_manager.mark_key_failure(api_key, error_type_for_key_manager)
                
                time.sleep(2.0)
        
        self.app_ref.log_message(f"工作线程 {worker_id} 结束运行", "debug")

    def add_translation_task(
        self, 
        entry_id: str, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        game_mod_style: str, 
        model_name: str, 
        original_line_content: Optional[str] = None
    ) -> None:
        """
        添加翻译任务到队列
        
        Args:
            entry_id: 条目ID
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言
            game_mod_style: 游戏/Mod风格
            model_name: 模型名称
            original_line_content: 原始行内容
        """
        task_data = {
            "entry_id": entry_id,
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "game_mod_style": game_mod_style,
            "model_name": model_name,
            "original_line_content": original_line_content
        }
        self.translation_queue.put(task_data)

    def get_translation_result(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        获取翻译结果
        
        Args:
            timeout: 超时时间，如果为None则阻塞等待
            
        Returns:
            翻译结果字典，如果队列为空则返回None
        """
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_queue_size(self) -> int:
        """获取待翻译队列大小"""
        return self.translation_queue.qsize()

    def is_queue_empty(self) -> bool:
        """检查待翻译队列是否为空"""
        return self.translation_queue.empty()

    def is_processing_complete(self) -> bool:
        """检查是否输入队列和结果队列都为空"""
        with self.lock:
            return self.translation_queue.empty() and self.result_queue.empty()

    def add_pending_review(self, entry_id: str, review_data: Any) -> None:
        """
        添加待评审的翻译
        
        Args:
            entry_id: 条目ID
            review_data: 评审数据
        """
        with self.lock:
            self.pending_reviews[entry_id] = review_data

    def get_pending_review(self, entry_id: str) -> Optional[Any]:
        """
        获取待评审的翻译
        
        Args:
            entry_id: 条目ID
            
        Returns:
            评审数据，如果不存在则返回None
        """
        with self.lock:
            return self.pending_reviews.get(entry_id)

    def remove_pending_review(self, entry_id: str) -> None:
        """
        移除待评审的翻译
        
        Args:
            entry_id: 条目ID
        """
        with self.lock:
            if entry_id in self.pending_reviews:
                del self.pending_reviews[entry_id]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取并行翻译器统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            translator_stats = {}
            for translator_id, translator in self.translators.items():
                translator_stats[translator_id] = translator.get_statistics()
            
            return {
                "active_workers": len([w for w in self.workers if w.is_alive()]),
                "total_workers": len(self.workers),
                "queue_size": self.get_queue_size(),
                "pending_reviews": len(self.pending_reviews),
                "api_key_stats": self.api_key_manager.get_key_performance_summary(),
                "translator_stats": translator_stats
            }

    def reset_statistics(self) -> None:
        """重置所有统计信息"""
        with self.lock:
            for translator in self.translators.values():
                translator.reset_statistics()
            self.pending_reviews.clear()

    def handle_review_result(self, key_name: str, review_result: dict) -> None:
        """
        处理评审结果

        Args:
            key_name: 翻译键名
            review_result: 评审结果
        """
        try:
            action = review_result.get("action", "use_ai")
            self.app_ref.log_message(f"并行翻译器收到评审结果: {key_name} -> {action}", "debug")

            # 这里可以添加更多的评审结果处理逻辑
            # 例如：统计评审结果、更新翻译质量指标等

        except Exception as e:
            self.app_ref.log_message(f"处理评审结果时出错: {e}", "error")

    def translate_files(
        self,
        source_files: List[str],
        source_lang: str,
        target_lang: str,
        game_style: str,
        model_name: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        翻译文件列表（高级接口）

        Args:
            source_files: 源文件路径列表
            source_lang: 源语言
            target_lang: 目标语言
            game_style: 游戏风格
            model_name: 模型名称

        Returns:
            是否成功完成翻译
        """
        # 导入翻译工作流程协调器
        from .translation_workflow import TranslationWorkflow

        # 创建工作流程实例
        workflow = TranslationWorkflow(self.app_ref, self.config_manager)
        if progress_callback:
            workflow.set_progress_callback(progress_callback)

        # 执行翻译
        return workflow.execute_translation(
            source_files, source_lang, target_lang, game_style, model_name
        )

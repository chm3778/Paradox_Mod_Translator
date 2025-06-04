"""
翻译工作流程协调器

负责协调整个翻译过程，包括文件处理、任务分发、结果收集等
"""

import os
import threading
from typing import List, Dict, Optional, Callable, Any, Tuple

from config.config_manager import ConfigManager
from parsers.yml_parser import YMLParser
from utils.file_utils import FileProcessor
from .parallel_translator import ParallelTranslator


class TranslationWorkflow:
    """翻译工作流程协调器"""
    
    def __init__(self, app_ref: Any, config_manager: ConfigManager):
        """
        初始化翻译工作流程协调器
        
        Args:
            app_ref: 应用程序引用
            config_manager: 配置管理器
        """
        self.app_ref = app_ref
        self.config_manager = config_manager
        self.yml_parser = YMLParser()
        self.file_processor = FileProcessor(self.yml_parser)
        self.parallel_translator = ParallelTranslator(app_ref, config_manager)
        
        # 工作流程状态
        self.is_running = False
        self.stop_flag = threading.Event()
        self.progress_callback: Optional[Callable[[int, int], None]] = None
        
    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，参数为(当前进度, 总数)
        """
        self.progress_callback = callback
    
    def validate_prerequisites(
        self, 
        source_lang: str, 
        target_lang: str, 
        file_paths: List[str]
    ) -> Tuple[bool, str]:
        """
        验证翻译前置条件
        
        Args:
            source_lang: 源语言
            target_lang: 目标语言
            file_paths: 文件路径列表
            
        Returns:
            (是否通过验证, 消息) 的元组
        """
        api_keys = self.config_manager.get_api_keys()
        return self.file_processor.validate_translation_prerequisites(
            api_keys, source_lang, target_lang, file_paths
        )
    
    def execute_translation(
        self,
        source_files: List[str],
        source_lang: str,
        target_lang: str,
        game_style: str,
        model_name: str
    ) -> bool:
        """
        执行翻译工作流程
        
        Args:
            source_files: 源文件路径列表
            source_lang: 源语言
            target_lang: 目标语言
            game_style: 游戏风格
            model_name: 模型名称
            
        Returns:
            是否成功完成翻译
        """
        if self.is_running:
            self.app_ref.log_message("翻译工作流程已在运行中", "warn")
            return False
        
        self.is_running = True
        self.stop_flag.clear()
        
        try:
            # 过滤源语言文件
            filtered_files = self.file_processor.filter_source_language_files(
                source_files, source_lang
            )
            
            if not filtered_files:
                self.app_ref.log_message("没有找到匹配的源语言文件", "error")
                return False
            
            self.app_ref.log_message(f"开始翻译 {len(filtered_files)} 个文件", "info")

            # 验证和预览目标目录结构
            is_valid, message, dirs_to_create = self.file_processor.validate_target_directory_structure(
                filtered_files, target_lang
            )

            if not is_valid:
                self.app_ref.log_message(f"目录结构验证失败: {message}", "error")
                return False

            if dirs_to_create:
                self.app_ref.log_message(f"将创建 {len(dirs_to_create)} 个目录", "info")
                for dir_path in dirs_to_create:
                    self.app_ref.log_message(f"  - {dir_path}", "debug")
            
            # 启动并行翻译器
            self.parallel_translator.start_workers()
            
            # 添加翻译任务
            total_entries = self._add_translation_tasks(
                filtered_files, source_lang, target_lang, game_style, model_name
            )
            
            if total_entries == 0:
                self.app_ref.log_message("没有找到需要翻译的条目", "warn")
                return False
            
            # 等待翻译完成并收集结果
            translation_results = self._collect_translation_results(total_entries)
            
            # 停止并行翻译器
            self.parallel_translator.stop_workers()
            
            if not translation_results:
                self.app_ref.log_message("没有收集到翻译结果", "error")
                return False
            
            # 生成翻译文件
            success = self._generate_translated_files(
                filtered_files, translation_results, target_lang
            )
            
            self.app_ref.log_message(
                f"翻译工作流程完成：处理了 {len(translation_results)} 个条目", 
                "info"
            )
            
            return success
            
        except Exception as e:
            self.app_ref.log_message(f"翻译工作流程执行失败: {e}", "error")
            return False
        finally:
            self.is_running = False
            self.parallel_translator.stop_workers()
    
    def stop_translation(self):
        """停止翻译工作流程"""
        if self.is_running:
            self.stop_flag.set()
            self.parallel_translator.stop_workers()
            self.app_ref.log_message("翻译工作流程已停止", "info")
    
    def _add_translation_tasks(
        self, 
        file_paths: List[str], 
        source_lang: str, 
        target_lang: str, 
        game_style: str, 
        model_name: str
    ) -> int:
        """添加翻译任务"""
        total_entries = 0
        
        for file_path in file_paths:
            if self.stop_flag.is_set():
                break
                
            try:
                detected_lang, entries = self.yml_parser.load_file(file_path)
                if detected_lang != source_lang:
                    continue
                
                for entry in entries:
                    if entry['value'].strip():  # 只翻译非空值
                        self.parallel_translator.add_translation_task(
                            entry_id=f"{file_path}:{entry['key']}",
                            text=entry['value'],
                            source_lang=source_lang,
                            target_lang=target_lang,
                            game_mod_style=game_style,
                            model_name=model_name,
                            original_line_content=entry.get('original_line_content')
                        )
                        total_entries += 1
                
                self.app_ref.log_message(
                    f"已添加文件 {os.path.basename(file_path)} 的 {len(entries)} 个翻译任务", 
                    "info"
                )
                
            except Exception as e:
                self.app_ref.log_message(f"处理文件 {file_path} 时出错: {e}", "error")
                continue
        
        return total_entries
    
    def _collect_translation_results(self, total_entries: int) -> Dict[str, Dict]:
        """收集翻译结果"""
        translation_results = {}
        processed_entries = 0

        # 获取评审设置
        auto_review_mode = self.app_ref.config_manager.get_setting("auto_review_mode", True)
        delayed_review = self.app_ref.config_manager.get_setting("delayed_review", True)

        while processed_entries < total_entries and not self.stop_flag.is_set():
            result = self.parallel_translator.get_translation_result(timeout=1.0)
            if result:
                processed_entries += 1

                # 检查是否需要评审
                if auto_review_mode and not delayed_review:
                    # 即时评审模式
                    self._handle_immediate_review(result)

                translation_results[result['entry_id']] = result

                # 更新进度
                if self.progress_callback:
                    self.progress_callback(processed_entries, total_entries)

                progress = (processed_entries / total_entries) * 100
                self.app_ref.log_message(
                    f"翻译进度: {processed_entries}/{total_entries} ({progress:.1f}%)",
                    "info"
                )

            # 检查是否被停止
            if self.stop_flag.is_set():
                self.app_ref.log_message("翻译被用户停止", "warn")
                break

        # 处理延迟评审
        if auto_review_mode and delayed_review and translation_results:
            self._handle_delayed_review(translation_results)

        return translation_results

    def _handle_immediate_review(self, result: Dict[str, Any]) -> None:
        """
        处理即时评审

        Args:
            result: 翻译结果
        """
        try:
            # 只对成功的翻译进行评审
            if result.get('api_error_type') is not None:
                return

            entry_id = result['entry_id']
            original_text = result['original_text']
            translated_text = result['translated_text']

            # 提取键名（去掉文件路径前缀）
            key_name = entry_id.split(':')[-1] if ':' in entry_id else entry_id

            # 创建评审回调
            def review_completion_callback(key, review_result):
                self.app_ref.handle_review_completion(key, review_result)
                # 更新翻译结果
                if review_result.get('action') == 'confirm':
                    result['translated_text'] = review_result.get('translation', translated_text)
                elif review_result.get('action') == 'use_original':
                    result['translated_text'] = original_text
                # 'use_ai' 和 'cancel' 保持原翻译结果不变

            # 触发评审
            self.app_ref.review_translation(
                key_name,
                original_text,
                translated_text,
                review_completion_callback
            )

        except Exception as e:
            self.app_ref.log_message(f"即时评审处理失败: {e}", "error")

    def _handle_delayed_review(self, translation_results: Dict[str, Dict]) -> None:
        """
        处理延迟评审

        Args:
            translation_results: 所有翻译结果
        """
        try:
            self.app_ref.log_message("开始延迟评审模式", "info")

            # 筛选需要评审的翻译结果（只评审成功的翻译）
            review_candidates = {
                entry_id: result for entry_id, result in translation_results.items()
                if result.get('api_error_type') is None and result.get('translated_text')
            }

            if not review_candidates:
                self.app_ref.log_message("没有需要评审的翻译结果", "info")
                return

            self.app_ref.log_message(f"找到 {len(review_candidates)} 个需要评审的翻译", "info")

            # 逐个进行评审
            for entry_id, result in review_candidates.items():
                if self.stop_flag.is_set():
                    break

                original_text = result['original_text']
                translated_text = result['translated_text']
                key_name = entry_id.split(':')[-1] if ':' in entry_id else entry_id

                # 创建评审回调
                def review_completion_callback(key, review_result, current_result=result):
                    self.app_ref.handle_review_completion(key, review_result)
                    # 更新翻译结果
                    if review_result.get('action') == 'confirm':
                        current_result['translated_text'] = review_result.get('translation', translated_text)
                    elif review_result.get('action') == 'use_original':
                        current_result['translated_text'] = original_text
                    # 'use_ai' 和 'cancel' 保持原翻译结果不变

                # 触发评审
                self.app_ref.review_translation(
                    key_name,
                    original_text,
                    translated_text,
                    review_completion_callback
                )

                # 等待评审完成（简单的等待机制）
                # 在实际应用中，可能需要更复杂的同步机制
                import time
                time.sleep(0.1)  # 给UI时间处理评审对话框

            self.app_ref.log_message("延迟评审完成", "info")

        except Exception as e:
            self.app_ref.log_message(f"延迟评审处理失败: {e}", "error")

    def _generate_translated_files(
        self, 
        source_files: List[str], 
        translation_results: Dict[str, Dict], 
        target_lang: str
    ) -> bool:
        """生成翻译后的文件"""
        success_count = 0
        
        for file_path in source_files:
            if self.stop_flag.is_set():
                break
                
            try:
                target_file_path = self.file_processor.generate_target_file_path(
                    file_path, target_lang
                )
                
                success = self.file_processor.generate_translated_file(
                    file_path, target_file_path, translation_results, target_lang
                )
                
                if success:
                    success_count += 1
                    self.app_ref.log_message(f"已生成翻译文件: {target_file_path}", "info")
                else:
                    self.app_ref.log_message(f"生成翻译文件失败: {file_path}", "error")
                    
            except Exception as e:
                self.app_ref.log_message(f"生成翻译文件 {file_path} 失败: {e}", "error")
                continue
        
        return success_count > 0

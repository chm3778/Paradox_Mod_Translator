#!/usr/bin/env python3
"""
Paradox Mod Translator - 主程序

一个专门用于翻译Paradox游戏Mod本地化文件的工具
使用Google Gemini API进行智能翻译
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X, Y
import threading
import time
import os

# 导入重构后的模块
from config.constants import CONFIG_FILE
from config.config_manager import ConfigManager
from parsers.yml_parser import YMLParser
from core.api_key_manager import APIKeyManager
from core.parallel_translator import ParallelTranslator
from core.model_manager import ModelManager

from utils.logging_utils import ApplicationLogger
from utils.file_utils import FileProcessor
from utils.validation import extract_placeholders

from gui.review_dialog import ReviewDialog


class ModTranslatorApp:
    """Paradox Mod翻译器主应用程序"""
    
    def __init__(self):
        """初始化应用程序"""
        # 初始化配置管理器
        self.config_manager = ConfigManager(CONFIG_FILE)

        # 初始化日志系统
        self.logger = ApplicationLogger()

        # 初始化解析器
        self.yml_parser = YMLParser()

        # 初始化文件处理器
        self.file_processor = FileProcessor(self.yml_parser)

        # 初始化API密钥管理器
        self.api_key_manager = APIKeyManager(self.config_manager)

        # 初始化模型管理器
        self.model_manager = ModelManager(self.config_manager, self)

        # 初始化并行翻译器
        self.parallel_translator = ParallelTranslator(self, self.config_manager)

        # 创建主窗口（必须在创建tkinter变量之前）
        self._create_main_window()

        # 初始化UI变量（必须在创建主窗口之后）
        self._init_ui_variables()

        # 添加日志回调（在主窗口创建后）
        self.logger.add_log_callback(self._on_log_message)

        # 创建UI
        self._create_ui()

        # 初始化状态
        self._init_state()

        # 加载配置
        self._load_config()

        self.log_message("应用程序初始化完成", "info")

    def _init_ui_variables(self):
        """初始化UI变量"""
        self.localization_root_path = tk.StringVar()
        self.source_language_code = tk.StringVar()
        self.target_language_code = tk.StringVar()
        self.game_mod_style_prompt = tk.StringVar()
        self.selected_model_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        self.api_call_delay_var = tk.DoubleVar()
        self.max_concurrent_tasks_var = tk.IntVar()
        self.auto_review_mode_var = tk.BooleanVar()
        self.delayed_review_var = tk.BooleanVar()
        
        # 翻译状态变量
        self.stop_translation_flag = threading.Event()
        self.translation_in_progress = False
        self.current_progress = 0
        self.overall_total_keys = 0
        
        # 文件相关变量
        self.files_for_translation = []
        self.pending_reviews = {}

        # 评审相关变量
        self.review_results = {}
        self.review_queue = []

    def _create_main_window(self):
        """创建主窗口"""
        self.root = ttkb.Window(themename="cosmo")
        self.root.title("Paradox Mod Translator")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 设置窗口图标（如果有的话）
        try:
            # 这里可以设置应用程序图标
            pass
        except Exception:
            pass
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_ui(self):
        """创建用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=True)
        
        # 创建顶部工具栏
        self._create_toolbar(main_frame)
        
        # 创建主要内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
        
        # 创建左侧面板（设置和文件列表）
        self._create_left_panel(content_frame)
        
        # 创建右侧面板（日志和控制）
        self._create_right_panel(content_frame)

    def _create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=X, pady=(0, 10))
        
        # 主题切换按钮
        self.theme_button = ttkb.Button(
            toolbar, 
            text="🌓 切换主题",
            style="outline.TButton",
            command=self._toggle_theme,
            width=12
        )
        self.theme_button.pack(side=LEFT, padx=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(
            toolbar, 
            text="就绪", 
            font=('Default', 10)
        )
        self.status_label.pack(side=RIGHT)

    def _create_left_panel(self, parent):
        """创建左侧面板"""
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        
        # 创建设置区域
        self._create_settings_area(left_frame)
        
        # 创建文件列表区域
        self._create_file_list_area(left_frame)

    def _create_right_panel(self, parent):
        """创建右侧面板"""
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        
        # 创建控制按钮区域
        self._create_control_buttons(right_frame)
        
        # 创建日志区域
        self._create_log_area(right_frame)

    def _create_settings_area(self, parent):
        """创建设置区域"""
        settings_frame = ttk.LabelFrame(parent, text="⚙️ 翻译设置", padding=(10, 5))
        settings_frame.pack(fill=X, pady=(0, 10))

        # 创建设置选项卡
        self._create_settings_notebook(settings_frame)

    def _create_settings_notebook(self, parent):
        """创建设置选项卡"""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=BOTH, expand=True)

        # 基本设置选项卡
        self._create_basic_settings_tab(notebook)

        # API设置选项卡
        self._create_api_settings_tab(notebook)

        # 高级设置选项卡
        self._create_advanced_settings_tab(notebook)

    def _create_basic_settings_tab(self, notebook):
        """创建基本设置选项卡"""
        basic_frame = ttk.Frame(notebook, padding=(10, 10))
        notebook.add(basic_frame, text="基本设置")

        # 语言设置
        self._create_language_settings(basic_frame)

        # 文件路径设置
        self._create_path_settings(basic_frame)

        # 翻译风格设置
        self._create_style_settings(basic_frame)

    def _create_api_settings_tab(self, notebook):
        """创建API设置选项卡"""
        api_frame = ttk.Frame(notebook, padding=(10, 10))
        notebook.add(api_frame, text="API设置")

        # API密钥管理
        self._create_api_key_management(api_frame)

        # 模型选择
        self._create_model_settings(api_frame)

    def _create_advanced_settings_tab(self, notebook):
        """创建高级设置选项卡"""
        advanced_frame = ttk.Frame(notebook, padding=(10, 10))
        notebook.add(advanced_frame, text="高级设置")

        # 并发设置
        self._create_concurrency_settings(advanced_frame)

        # 评审设置
        self._create_review_settings(advanced_frame)

    def _create_file_list_area(self, parent):
        """创建文件列表区域"""
        files_frame = ttk.LabelFrame(parent, text="📁 待翻译文件", padding=(10, 5))
        files_frame.pack(fill=BOTH, expand=True)
        
        # 文件列表
        self.files_listbox = tk.Listbox(files_frame, height=8)
        self.files_listbox.pack(fill=BOTH, expand=True, pady=(0, 5))

        # 目录结构预览按钮
        preview_frame = ttk.Frame(files_frame)
        preview_frame.pack(fill=X)

        self.preview_structure_button = ttkb.Button(
            preview_frame,
            text="📁 预览目录结构",
            style="outline.TButton",
            command=self._preview_directory_structure,
            width=20
        )
        self.preview_structure_button.pack(side=LEFT, padx=(0, 5))

        self.analyze_structure_button = ttkb.Button(
            preview_frame,
            text="🔍 分析目录",
            style="outline.TButton",
            command=self._analyze_directory_structure,
            width=15
        )
        self.analyze_structure_button.pack(side=LEFT)

    def _create_control_buttons(self, parent):
        """创建控制按钮"""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill=X, pady=(0, 10))
        
        # 开始翻译按钮
        self.translate_button = ttkb.Button(
            buttons_frame, 
            text="▶️ 开始翻译", 
            style="success.TButton",
            command=self._start_translation_process,
            width=15
        )
        self.translate_button.pack(side=LEFT, padx=(0, 10))
        
        # 停止翻译按钮
        self.stop_button = ttkb.Button(
            buttons_frame, 
            text="⏹️ 停止翻译", 
            style="danger.TButton",
            command=self._stop_translation_process,
            width=15,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=LEFT)

    def _create_log_area(self, parent):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(parent, text="📋 运行日志", padding=(10, 5))
        log_frame.pack(fill=BOTH, expand=True)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=20, 
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=BOTH, expand=True)

    def _init_state(self):
        """初始化应用程序状态"""
        self.translation_in_progress = False
        self.stop_translation_flag.clear()

    def _load_config(self):
        """加载配置"""
        try:
            # 加载各种配置项
            self.localization_root_path.set(
                self.config_manager.get_setting("localization_root_path", "")
            )
            self.source_language_code.set(
                self.config_manager.get_setting("source_language", "english")
            )
            self.target_language_code.set(
                self.config_manager.get_setting("target_language", "simp_chinese")
            )
            self.selected_model_var.set(
                self.config_manager.get_setting("selected_model", "gemini-1.5-flash-latest")
            )
            self.api_call_delay_var.set(
                self.config_manager.get_setting("api_call_delay", 3.0)
            )
            self.max_concurrent_tasks_var.set(
                self.config_manager.get_setting("max_concurrent_tasks", 3)
            )
            self.auto_review_mode_var.set(
                self.config_manager.get_setting("auto_review_mode", True)
            )
            self.delayed_review_var.set(
                self.config_manager.get_setting("delayed_review", True)
            )

            # 加载翻译风格
            style = self.config_manager.get_setting("game_mod_style", "General video game localization, maintain tone of original.")
            self.game_mod_style_prompt.set(style)
            if hasattr(self, 'style_text'):
                self.style_text.delete(1.0, tk.END)
                self.style_text.insert(1.0, style)

            # 刷新API密钥列表
            if hasattr(self, 'api_keys_listbox'):
                self._refresh_api_keys_list()

            # 初始化模型状态
            if hasattr(self, 'model_status_label'):
                self._initialize_model_status()

            self.log_message("配置加载完成", "info")
        except Exception as e:
            self.log_message(f"加载配置时发生错误: {e}", "error")

    def _toggle_theme(self):
        """切换主题"""
        current_theme = self.root.style.theme_use()
        new_theme = "darkly" if current_theme == "cosmo" else "cosmo"
        self.root.style.theme_use(new_theme)
        self.log_message(f"主题已切换为: {new_theme}", "info")

    def _start_translation_process(self):
        """开始翻译过程"""
        if self.translation_in_progress:
            self.log_message("翻译正在进行中，请等待完成或停止当前翻译", "warn")
            return

        # 验证翻译前置条件
        source_lang = self.source_language_code.get()
        target_lang = self.target_language_code.get()
        api_keys = self.config_manager.get_api_keys()

        is_valid, message = self.file_processor.validate_translation_prerequisites(
            api_keys, source_lang, target_lang, self.files_for_translation
        )

        if not is_valid:
            messagebox.showerror("错误", message)
            self.log_message(f"翻译失败：{message}", "error")
            return

        self.log_message("开始翻译过程...", "info")
        self.translation_in_progress = True
        self.translate_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # 在后台线程中执行实际翻译
        translation_thread = threading.Thread(
            target=self._execute_translation_workflow,
            daemon=True
        )
        translation_thread.start()

    def _execute_translation_workflow(self):
        """执行翻译工作流程"""
        try:
            # 获取翻译参数
            source_lang = self.source_language_code.get()
            target_lang = self.target_language_code.get()
            game_style = self.style_text.get(1.0, tk.END).strip() or self.game_mod_style_prompt.get()
            model_name = self.selected_model_var.get()

            self.log_message(f"翻译设置: {source_lang} -> {target_lang}, 模型: {model_name}", "info")

            # 使用并行翻译器执行翻译
            success = self.parallel_translator.translate_files(
                self.files_for_translation,
                source_lang,
                target_lang,
                game_style,
                model_name
            )

            # 在UI线程中更新结果
            self.root.after(0, self._on_translation_completed, success)

        except Exception as e:
            error_msg = f"翻译过程中发生错误: {e}"
            self.log_message(error_msg, "error")
            self.root.after(0, self._on_translation_completed, False)

    def _on_translation_completed(self, success):
        """翻译完成回调"""
        if success:
            self.log_message("翻译过程已成功完成", "info")
            messagebox.showinfo("完成", "翻译已完成！请检查输出文件。")
        else:
            self.log_message("翻译过程失败", "error")
            messagebox.showerror("失败", "翻译过程中发生错误，请查看日志了解详情。")

        self._finish_translation_process()

    def _stop_translation_process(self):
        """停止翻译过程"""
        self.log_message("正在停止翻译...", "warn")
        self.stop_translation_flag.set()
        self._finish_translation_process()

    def _finish_translation_process(self):
        """完成翻译过程"""
        self.translation_in_progress = False
        self.stop_translation_flag.clear()
        self.translate_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log_message("翻译过程已完成", "info")

    def _on_log_message(self, message: str, level: str):
        """处理日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level.upper()}: {message}\n"

        # 在UI线程中更新日志
        self.root.after(0, self._update_log_display, formatted_message)

    def _update_log_display(self, message: str):
        """更新日志显示"""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)

    def log_message(self, message: str, level: str = "info"):
        """记录日志消息"""
        self.logger.log_message(message, level)

    def review_translation(self, key_name: str, original_text: str, ai_translation: str, completion_callback):
        """
        触发翻译评审

        Args:
            key_name: 翻译键名
            original_text: 原文
            ai_translation: AI翻译结果
            completion_callback: 完成回调函数
        """
        try:
            # 提取占位符
            original_placeholders = extract_placeholders(original_text)
            translated_placeholders = extract_placeholders(ai_translation)

            # 创建评审对话框
            review_dialog = ReviewDialog(
                parent_app_instance=self,
                root_window=self.root,
                original_text=original_text,
                ai_translation=ai_translation,
                original_placeholders=original_placeholders,
                translated_placeholders=translated_placeholders,
                key_name=key_name,
                completion_callback=completion_callback
            )

            self.log_message(f"已触发评审对话框: {key_name}", "info")

        except Exception as e:
            self.log_message(f"创建评审对话框时出错: {e}", "error")
            # 如果评审对话框创建失败，直接使用AI翻译
            completion_callback(key_name, {"action": "use_ai", "translation": ai_translation})

    def handle_review_completion(self, key_name: str, result: dict):
        """
        处理评审完成结果

        Args:
            key_name: 翻译键名
            result: 评审结果字典
        """
        try:
            action = result.get("action", "use_ai")
            translation = result.get("translation", "")

            # 保存评审结果
            self.review_results[key_name] = result

            # 记录评审结果
            if action == "confirm":
                self.log_message(f"评审确认: {key_name}", "info")
            elif action == "use_ai":
                self.log_message(f"使用AI翻译: {key_name}", "info")
            elif action == "use_original":
                self.log_message(f"使用原文: {key_name}", "info")
            elif action == "cancel":
                self.log_message(f"评审取消: {key_name}", "warn")

            # 通知并行翻译器评审完成
            if hasattr(self.parallel_translator, 'handle_review_result'):
                self.parallel_translator.handle_review_result(key_name, result)

        except Exception as e:
            self.log_message(f"处理评审结果时出错: {e}", "error")

    def _on_closing(self):
        """处理窗口关闭事件"""
        try:
            # 停止所有翻译任务
            if self.translation_in_progress:
                self.stop_translation_flag.set()
                self.parallel_translator.stop_workers()

            # 保存配置
            self.config_manager.save_config()

            self.log_message("应用程序正在关闭...", "info")

            # 关闭窗口
            self.root.destroy()

        except Exception as e:
            print(f"关闭应用程序时发生错误: {e}")
            self.root.destroy()

    def _create_language_settings(self, parent):
        """创建语言设置"""
        lang_frame = ttk.LabelFrame(parent, text="🌍 语言设置", padding=(10, 5))
        lang_frame.pack(fill=X, pady=(0, 10))

        # 源语言设置
        source_frame = ttk.Frame(lang_frame)
        source_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(source_frame, text="源语言:", width=12).pack(side=LEFT)
        self.source_language_combo = ttk.Combobox(
            source_frame,
            textvariable=self.source_language_code,
            values=list(self._get_supported_languages().keys()),
            state="readonly",
            width=20
        )
        self.source_language_combo.pack(side=LEFT, padx=(5, 0))

        # 目标语言设置
        target_frame = ttk.Frame(lang_frame)
        target_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(target_frame, text="目标语言:", width=12).pack(side=LEFT)
        self.target_language_combo = ttk.Combobox(
            target_frame,
            textvariable=self.target_language_code,
            values=list(self._get_supported_languages().keys()),
            state="readonly",
            width=20
        )
        self.target_language_combo.pack(side=LEFT, padx=(5, 0))

        # 绑定事件
        self.source_language_combo.bind('<<ComboboxSelected>>', self._on_language_changed)
        self.target_language_combo.bind('<<ComboboxSelected>>', self._on_language_changed)

    def _create_path_settings(self, parent):
        """创建路径设置"""
        path_frame = ttk.LabelFrame(parent, text="📁 文件路径", padding=(10, 5))
        path_frame.pack(fill=X, pady=(0, 10))

        # 本地化根目录
        root_frame = ttk.Frame(path_frame)
        root_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(root_frame, text="本地化目录:", width=12).pack(side=LEFT)
        self.path_entry = ttk.Entry(root_frame, textvariable=self.localization_root_path)
        self.path_entry.pack(side=LEFT, fill=X, expand=True, padx=(5, 5))

        self.browse_button = ttkb.Button(
            root_frame,
            text="浏览",
            command=self._browse_localization_path,
            width=8
        )
        self.browse_button.pack(side=RIGHT)

    def _create_style_settings(self, parent):
        """创建翻译风格设置"""
        style_frame = ttk.LabelFrame(parent, text="🎨 翻译风格", padding=(10, 5))
        style_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(style_frame, text="游戏/Mod风格提示:").pack(anchor="w", pady=(0, 5))

        self.style_text = tk.Text(
            style_frame,
            height=3,
            wrap=tk.WORD,
            font=('Default', 9)
        )
        self.style_text.pack(fill=X, pady=(0, 5))

        # 预设风格按钮
        preset_frame = ttk.Frame(style_frame)
        preset_frame.pack(fill=X)

        presets = [
            ("通用游戏", "General video game localization, maintain tone of original."),
            ("策略游戏", "Strategy game localization, formal and precise tone."),
            ("角色扮演", "RPG localization, immersive and narrative style."),
            ("历史题材", "Historical game localization, period-appropriate language.")
        ]

        for i, (name, style) in enumerate(presets):
            btn = ttkb.Button(
                preset_frame,
                text=name,
                command=lambda s=style: self._set_style_preset(s),
                style="outline.TButton",
                width=10
            )
            btn.pack(side=LEFT, padx=(0, 5) if i < len(presets)-1 else 0)

    def _create_api_key_management(self, parent):
        """创建API密钥管理"""
        api_frame = ttk.LabelFrame(parent, text="🔑 API密钥管理", padding=(10, 5))
        api_frame.pack(fill=X, pady=(0, 10))

        # API密钥列表
        list_frame = ttk.Frame(api_frame)
        list_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(list_frame, text="已配置的API密钥:").pack(anchor="w", pady=(0, 5))

        # 创建列表框和滚动条
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=X)

        self.api_keys_listbox = tk.Listbox(listbox_frame, height=4)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.api_keys_listbox.yview)
        self.api_keys_listbox.configure(yscrollcommand=scrollbar.set)

        self.api_keys_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")

        # API密钥操作按钮
        buttons_frame = ttk.Frame(api_frame)
        buttons_frame.pack(fill=X, pady=(10, 0))

        self.add_key_button = ttkb.Button(
            buttons_frame,
            text="➕ 添加密钥",
            command=self._add_api_key,
            style="success.TButton",
            width=12
        )
        self.add_key_button.pack(side=LEFT, padx=(0, 5))

        self.edit_key_button = ttkb.Button(
            buttons_frame,
            text="✏️ 编辑密钥",
            command=self._edit_api_key,
            style="info.TButton",
            width=12
        )
        self.edit_key_button.pack(side=LEFT, padx=(0, 5))

        self.remove_key_button = ttkb.Button(
            buttons_frame,
            text="🗑️ 删除密钥",
            command=self._remove_api_key,
            style="danger.TButton",
            width=12
        )
        self.remove_key_button.pack(side=LEFT)

    def _create_model_settings(self, parent):
        """创建模型设置"""
        model_frame = ttk.LabelFrame(parent, text="🤖 AI模型设置", padding=(10, 5))
        model_frame.pack(fill=X, pady=(0, 10))

        # 模型选择
        model_select_frame = ttk.Frame(model_frame)
        model_select_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(model_select_frame, text="选择模型:", width=12).pack(side=LEFT)
        self.model_combo = ttk.Combobox(
            model_select_frame,
            textvariable=self.selected_model_var,
            values=self._get_available_models(),
            state="readonly",
            width=30
        )
        self.model_combo.pack(side=LEFT, padx=(5, 0))
        self.model_combo.bind('<<ComboboxSelected>>', self._on_model_changed)

        # 刷新模型列表按钮
        self.refresh_models_button = ttkb.Button(
            model_select_frame,
            text="🔄",
            style="outline.TButton",
            command=self._refresh_models,
            width=3
        )
        self.refresh_models_button.pack(side=LEFT, padx=(5, 0))

        # 模型状态标签
        self.model_status_label = ttk.Label(
            model_frame,
            text="",
            font=('Default', 8),
            foreground="gray"
        )
        self.model_status_label.pack(anchor="w", pady=(5, 0))

    def _create_concurrency_settings(self, parent):
        """创建并发设置"""
        concurrency_frame = ttk.LabelFrame(parent, text="⚡ 并发设置", padding=(10, 5))
        concurrency_frame.pack(fill=X, pady=(0, 10))

        # 并发任务数
        tasks_frame = ttk.Frame(concurrency_frame)
        tasks_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(tasks_frame, text="并发任务数:", width=15).pack(side=LEFT)
        self.tasks_spinbox = ttk.Spinbox(
            tasks_frame,
            from_=1,
            to=10,
            textvariable=self.max_concurrent_tasks_var,
            command=self._on_concurrency_changed,
            width=10
        )
        self.tasks_spinbox.pack(side=LEFT, padx=(5, 0))

        # API调用延迟
        delay_frame = ttk.Frame(concurrency_frame)
        delay_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(delay_frame, text="API调用延迟(秒):", width=15).pack(side=LEFT)
        self.delay_spinbox = ttk.Spinbox(
            delay_frame,
            from_=0.5,
            to=10.0,
            increment=0.5,
            textvariable=self.api_call_delay_var,
            command=self._on_delay_changed,
            width=10
        )
        self.delay_spinbox.pack(side=LEFT, padx=(5, 0))

    def _create_review_settings(self, parent):
        """创建评审设置"""
        review_frame = ttk.LabelFrame(parent, text="📝 评审设置", padding=(10, 5))
        review_frame.pack(fill=X, pady=(0, 10))

        # 自动评审模式
        self.auto_review_check = ttk.Checkbutton(
            review_frame,
            text="启用自动评审模式",
            variable=self.auto_review_mode_var,
            command=self._on_review_settings_changed
        )
        self.auto_review_check.pack(anchor="w", pady=(0, 5))

        # 延迟评审
        self.delayed_review_check = ttk.Checkbutton(
            review_frame,
            text="启用延迟评审（翻译完成后统一评审）",
            variable=self.delayed_review_var,
            command=self._on_review_settings_changed
        )
        self.delayed_review_check.pack(anchor="w")

    # 辅助方法和事件处理
    def _get_supported_languages(self):
        """获取支持的语言列表"""
        return {
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

    def _get_available_models(self):
        """获取可用的AI模型列表"""
        return self.model_manager.get_available_models()

    def _on_language_changed(self, event=None):
        """语言选择改变事件"""
        _ = event  # 标记参数已使用
        source = self.source_language_code.get()
        target = self.target_language_code.get()

        if source and target:
            self.config_manager.set_setting("source_language", source)
            self.config_manager.set_setting("target_language", target)
            self.log_message(f"语言设置已更新: {source} -> {target}", "info")

    def _browse_localization_path(self):
        """浏览本地化路径"""
        directory = filedialog.askdirectory(
            title="选择本地化文件目录",
            initialdir=self.localization_root_path.get() or os.getcwd()
        )

        if directory:
            self.localization_root_path.set(directory)
            self.config_manager.set_setting("localization_root_path", directory)
            self.log_message(f"本地化目录设置为: {directory}", "info")

            # 自动扫描YML文件
            self._scan_yml_files(directory)

    def _set_style_preset(self, style):
        """设置预设翻译风格"""
        self.style_text.delete(1.0, tk.END)
        self.style_text.insert(1.0, style)
        self.game_mod_style_prompt.set(style)
        self.config_manager.set_setting("game_mod_style", style)
        self.log_message(f"翻译风格已设置为预设", "info")

    def _add_api_key(self):
        """添加API密钥"""
        from tkinter import simpledialog

        new_key = simpledialog.askstring(
            "添加API密钥",
            "请输入新的Google Gemini API密钥:",
            show='*'
        )

        if new_key and new_key.strip():
            new_key = new_key.strip()

            # 验证API密钥格式
            if not new_key.startswith("AIza") or len(new_key) != 39:
                messagebox.showerror(
                    "错误",
                    "API密钥格式不正确！\n正确格式应以'AIza'开头，长度为39个字符。"
                )
                return

            if self.config_manager.add_api_key(new_key):
                self._refresh_api_keys_list()
                self.api_key_manager.reload_keys()
                self.log_message("API密钥添加成功", "info")

                # 自动刷新模型列表
                self.log_message("正在刷新可用模型列表...", "info")
                self._refresh_models()
            else:
                messagebox.showwarning("警告", "API密钥已存在或添加失败")

    def _edit_api_key(self):
        """编辑API密钥"""
        selection = self.api_keys_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要编辑的API密钥")
            return

        index = selection[0]
        keys = self.config_manager.get_api_keys()
        if index >= len(keys):
            return

        old_key = keys[index]

        from tkinter import simpledialog
        new_key = simpledialog.askstring(
            "编辑API密钥",
            "请输入新的API密钥:",
            initialvalue=old_key,
            show='*'
        )

        if new_key and new_key.strip() and new_key != old_key:
            new_key = new_key.strip()

            # 验证API密钥格式
            if not new_key.startswith("AIza") or len(new_key) != 39:
                messagebox.showerror(
                    "错误",
                    "API密钥格式不正确！\n正确格式应以'AIza'开头，长度为39个字符。"
                )
                return

            if self.config_manager.update_api_key(old_key, new_key):
                self._refresh_api_keys_list()
                self.api_key_manager.reload_keys()
                self.log_message("API密钥更新成功", "info")
            else:
                messagebox.showerror("错误", "API密钥更新失败")

    def _remove_api_key(self):
        """删除API密钥"""
        selection = self.api_keys_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的API密钥")
            return

        if messagebox.askyesno("确认删除", "确定要删除选中的API密钥吗？"):
            index = selection[0]
            keys = self.config_manager.get_api_keys()
            if index < len(keys):
                key_to_remove = keys[index]
                if self.config_manager.remove_api_key(key_to_remove):
                    self._refresh_api_keys_list()
                    self.api_key_manager.reload_keys()
                    self.log_message("API密钥删除成功", "info")
                else:
                    messagebox.showerror("错误", "API密钥删除失败")

    def _refresh_api_keys_list(self):
        """刷新API密钥列表显示"""
        self.api_keys_listbox.delete(0, tk.END)

        keys = self.config_manager.get_api_keys()
        for key in keys:
            # 只显示密钥的前4位和后4位
            display_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else key
            self.api_keys_listbox.insert(tk.END, display_key)

    def _scan_yml_files(self, directory):
        """扫描目录中的YML文件"""
        yml_files = self.file_processor.scan_yml_files(directory)

        # 更新文件列表
        self.files_for_translation = yml_files
        self._refresh_file_list()

        self.log_message(f"扫描完成，找到 {len(yml_files)} 个YML文件", "info")

    def _refresh_file_list(self):
        """刷新文件列表显示"""
        self.files_listbox.delete(0, tk.END)

        for file_path in self.files_for_translation:
            # 获取文件语言信息
            lang_code, entry_count = self.file_processor.get_file_language_info(file_path)
            filename = os.path.basename(file_path)

            # 显示文件名和语言信息
            if lang_code:
                display_text = f"{filename} [{lang_code}, {entry_count} 条目]"
            else:
                display_text = f"{filename} [未知语言]"

            self.files_listbox.insert(tk.END, display_text)

    def _on_model_changed(self, event=None):
        """模型选择改变事件"""
        _ = event  # 标记参数已使用
        model = self.selected_model_var.get()
        if model:
            self.config_manager.set_setting("selected_model", model)
            self.log_message(f"AI模型设置为: {model}", "info")

    def _refresh_models(self):
        """刷新模型列表"""
        self.refresh_models_button.config(state=tk.DISABLED, text="⏳")
        self.log_message("正在刷新模型列表...", "info")

        def on_refresh_complete(models, error):
            """刷新完成回调"""
            def update_ui():
                self.refresh_models_button.config(state=tk.NORMAL, text="🔄")

                if error:
                    self.log_message(f"刷新模型列表失败: {error}", "error")
                    messagebox.showerror("错误", f"刷新模型列表失败:\n{error}")
                else:
                    # 更新下拉列表
                    current_selection = self.selected_model_var.get()
                    self.model_combo['values'] = models

                    # 保持当前选择（如果仍然可用）
                    if current_selection in models:
                        self.selected_model_var.set(current_selection)
                    elif models:
                        self.selected_model_var.set(models[0])

                    self.log_message(f"模型列表已更新，共 {len(models)} 个模型", "info")

                    # 更新状态标签
                    cache_status = self.model_manager.get_cache_status()
                    if cache_status['cache_valid']:
                        status_text = f"已缓存 {len(models)} 个模型 (来自API)"
                    else:
                        status_text = f"使用默认模型列表 ({len(models)} 个)"
                    self.model_status_label.config(text=status_text)

            # 在UI线程中更新界面
            self.root.after(0, update_ui)

        # 异步刷新模型列表
        self.model_manager.refresh_models_async(on_refresh_complete)

    def _initialize_model_status(self):
        """初始化模型状态显示"""
        try:
            models = self.model_manager.get_available_models()
            cache_status = self.model_manager.get_cache_status()

            if cache_status['cache_valid']:
                status_text = f"已缓存 {len(models)} 个模型 (来自API)"
            else:
                status_text = f"使用默认模型列表 ({len(models)} 个)"

            self.model_status_label.config(text=status_text)
            self.log_message(f"模型状态: {status_text}", "debug")
        except Exception as e:
            self.log_message(f"初始化模型状态失败: {e}", "error")

    def _preview_directory_structure(self):
        """预览目录结构"""
        if not self.files_for_translation:
            messagebox.showwarning("警告", "请先选择要翻译的文件")
            return

        source_lang = self.source_language_code.get()
        target_lang = self.target_language_code.get()

        if not source_lang or not target_lang:
            messagebox.showwarning("警告", "请先设置源语言和目标语言")
            return

        # 过滤源语言文件
        source_files = self.file_processor.filter_source_language_files(
            self.files_for_translation, source_lang
        )

        if not source_files:
            messagebox.showwarning("警告", f"没有找到源语言({source_lang})的文件")
            return

        # 获取预览结构
        preview_pairs = self.file_processor.preview_translation_structure(
            source_files, target_lang
        )

        # 创建预览窗口
        self._show_structure_preview_window(preview_pairs, target_lang)

    def _analyze_directory_structure(self):
        """分析目录结构"""
        root_path = self.localization_root_path.get()
        if not root_path or not os.path.exists(root_path):
            messagebox.showwarning("警告", "请先设置有效的本地化目录")
            return

        # 分析目录结构
        language_files = self.file_processor.analyze_directory_structure(root_path)

        if not language_files:
            messagebox.showinfo("信息", "在指定目录中没有找到YML文件")
            return

        # 创建分析结果窗口
        self._show_structure_analysis_window(language_files)

    def _show_structure_preview_window(self, preview_pairs, target_lang):
        """显示目录结构预览窗口"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"目录结构预览 - {target_lang}")
        preview_window.geometry("800x600")
        preview_window.transient(self.root)
        preview_window.grab_set()

        # 创建主框架
        main_frame = ttk.Frame(preview_window, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text=f"翻译后文件将保存到以下位置 (目标语言: {target_lang})",
            font=('Default', 12, 'bold')
        )
        title_label.pack(pady=(0, 10))

        # 创建树形视图
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        tree = ttk.Treeview(tree_frame, columns=('target',), show='tree headings')
        tree.heading('#0', text='源文件')
        tree.heading('target', text='目标文件')
        tree.column('#0', width=400)
        tree.column('target', width=400)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 填充数据
        for source_file, target_file in preview_pairs:
            source_rel = os.path.relpath(source_file, self.localization_root_path.get())
            target_rel = os.path.relpath(target_file, self.localization_root_path.get())
            tree.insert('', 'end', text=source_rel, values=(target_rel,))

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X)

        ttk.Button(
            button_frame,
            text="关闭",
            command=preview_window.destroy
        ).pack(side=RIGHT)

    def _show_structure_analysis_window(self, language_files):
        """显示目录结构分析窗口"""
        analysis_window = tk.Toplevel(self.root)
        analysis_window.title("目录结构分析")
        analysis_window.geometry("600x500")
        analysis_window.transient(self.root)
        analysis_window.grab_set()

        # 创建主框架
        main_frame = ttk.Frame(analysis_window, padding=10)
        main_frame.pack(fill=BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="本地化目录结构分析",
            font=('Default', 12, 'bold')
        )
        title_label.pack(pady=(0, 10))

        # 创建文本框显示分析结果
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        analysis_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Consolas', 10)
        )
        analysis_text.pack(fill=BOTH, expand=True)

        # 填充分析结果
        analysis_text.insert(tk.END, f"发现 {len(language_files)} 种语言的文件:\n\n")

        for lang, files in language_files.items():
            analysis_text.insert(tk.END, f"📁 {lang} ({len(files)} 个文件):\n")
            for file_path in files[:5]:  # 只显示前5个文件
                rel_path = os.path.relpath(file_path, self.localization_root_path.get())
                analysis_text.insert(tk.END, f"  - {rel_path}\n")

            if len(files) > 5:
                analysis_text.insert(tk.END, f"  ... 还有 {len(files) - 5} 个文件\n")

            analysis_text.insert(tk.END, "\n")

        analysis_text.config(state=tk.DISABLED)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=X)

        ttk.Button(
            button_frame,
            text="关闭",
            command=analysis_window.destroy
        ).pack(side=RIGHT)

    def _on_concurrency_changed(self):
        """并发设置改变事件"""
        tasks = self.max_concurrent_tasks_var.get()
        self.config_manager.set_setting("max_concurrent_tasks", tasks)
        self.log_message(f"并发任务数设置为: {tasks}", "info")

    def _on_delay_changed(self):
        """延迟设置改变事件"""
        delay = self.api_call_delay_var.get()
        self.config_manager.set_setting("api_call_delay", delay)
        self.log_message(f"API调用延迟设置为: {delay}秒", "info")

    def _on_review_settings_changed(self):
        """评审设置改变事件"""
        auto_review = self.auto_review_mode_var.get()
        delayed_review = self.delayed_review_var.get()

        self.config_manager.set_setting("auto_review_mode", auto_review)
        self.config_manager.set_setting("delayed_review", delayed_review)

        self.log_message(f"评审设置已更新 - 自动评审: {auto_review}, 延迟评审: {delayed_review}", "info")

    def run(self):
        """运行应用程序"""
        self.log_message("启动Paradox Mod Translator", "info")
        self.root.mainloop()


def main():
    """主函数"""
    try:
        app = ModTranslatorApp()
        app.run()
    except Exception as e:
        print(f"启动应用程序时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

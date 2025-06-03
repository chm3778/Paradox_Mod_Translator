#!/usr/bin/env python3
"""
Paradox Mod Translator - 重构版本

一个专门用于翻译Paradox游戏Mod本地化文件的工具
使用Google Gemini API进行智能翻译
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, X
import threading
import time
import os

# 导入重构后的模块
from config.constants import CONFIG_FILE
from config.config_manager import ConfigManager
from parsers.yml_parser import YMLParser
from core.api_key_manager import APIKeyManager
from core.parallel_translator import ParallelTranslator
from utils.logging_utils import ApplicationLogger


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

        # 初始化API密钥管理器
        self.api_key_manager = APIKeyManager(self.config_manager)

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

    def _create_main_window(self):
        """创建主窗口"""
        self.root = ttkb.Window(themename="cosmo")
        self.root.title("Paradox Mod Translator - 重构版")
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
        self.files_listbox = tk.Listbox(files_frame, height=10)
        self.files_listbox.pack(fill=BOTH, expand=True)

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
        
        self.log_message("开始翻译过程...", "info")
        self.translation_in_progress = True
        self.translate_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 这里会实现实际的翻译逻辑
        # 为了简化，暂时只是模拟
        self.root.after(3000, self._finish_translation_process)

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

        # 按钮区域
        button_frame = ttk.Frame(api_frame)
        button_frame.pack(fill=X, pady=(5, 0))

        self.add_key_button = ttkb.Button(
            button_frame,
            text="➕ 添加",
            command=self._add_api_key,
            style="success.TButton",
            width=10
        )
        self.add_key_button.pack(side=LEFT, padx=(0, 5))

        self.edit_key_button = ttkb.Button(
            button_frame,
            text="✏️ 编辑",
            command=self._edit_api_key,
            style="info.TButton",
            width=10
        )
        self.edit_key_button.pack(side=LEFT, padx=(0, 5))

        self.remove_key_button = ttkb.Button(
            button_frame,
            text="🗑️ 删除",
            command=self._remove_api_key,
            style="danger.TButton",
            width=10
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

    def _create_concurrency_settings(self, parent):
        """创建并发设置"""
        concurrency_frame = ttk.LabelFrame(parent, text="⚡ 并发设置", padding=(10, 5))
        concurrency_frame.pack(fill=X, pady=(0, 10))

        # 并发任务数
        tasks_frame = ttk.Frame(concurrency_frame)
        tasks_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(tasks_frame, text="并发任务数:", width=12).pack(side=LEFT)
        self.tasks_spinbox = ttk.Spinbox(
            tasks_frame,
            from_=1,
            to=10,
            textvariable=self.max_concurrent_tasks_var,
            width=10,
            command=self._on_concurrency_changed
        )
        self.tasks_spinbox.pack(side=LEFT, padx=(5, 0))

        # API调用延迟
        delay_frame = ttk.Frame(concurrency_frame)
        delay_frame.pack(fill=X, pady=(0, 5))

        ttk.Label(delay_frame, text="API延迟(秒):", width=12).pack(side=LEFT)
        self.delay_spinbox = ttk.Spinbox(
            delay_frame,
            from_=0.5,
            to=30.0,
            increment=0.5,
            textvariable=self.api_call_delay_var,
            width=10,
            command=self._on_delay_changed
        )
        self.delay_spinbox.pack(side=LEFT, padx=(5, 0))

    def _create_review_settings(self, parent):
        """创建评审设置"""
        review_frame = ttk.LabelFrame(parent, text="📝 评审设置", padding=(10, 5))
        review_frame.pack(fill=X, pady=(0, 10))

        # 自动评审模式
        auto_frame = ttk.Frame(review_frame)
        auto_frame.pack(fill=X, pady=(0, 5))

        self.auto_review_check = ttk.Checkbutton(
            auto_frame,
            text="启用自动评审模式",
            variable=self.auto_review_mode_var,
            command=self._on_review_settings_changed
        )
        self.auto_review_check.pack(side=LEFT)

        # 延迟评审
        delayed_frame = ttk.Frame(review_frame)
        delayed_frame.pack(fill=X, pady=(0, 5))

        self.delayed_review_check = ttk.Checkbutton(
            delayed_frame,
            text="启用延迟评审（翻译完成后统一评审）",
            variable=self.delayed_review_var,
            command=self._on_review_settings_changed
        )
        self.delayed_review_check.pack(side=LEFT)

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
        return [
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro-latest",
            "models/gemini-2.0-flash-lite",
            "models/gemini-2.0-flash"
        ]

    def _on_language_changed(self, event=None):
        """语言选择改变事件"""
        source_lang = self.source_language_code.get()
        target_lang = self.target_language_code.get()

        if source_lang:
            self.config_manager.set_setting("source_language", source_lang)
            self.log_message(f"源语言设置为: {source_lang}", "info")

        if target_lang:
            self.config_manager.set_setting("target_language", target_lang)
            self.log_message(f"目标语言设置为: {target_lang}", "info")

    def _browse_localization_path(self):
        """浏览本地化目录"""
        directory = filedialog.askdirectory(
            title="选择本地化文件目录",
            initialdir=self.localization_root_path.get() or "."
        )

        if directory:
            self.localization_root_path.set(directory)
            self.config_manager.set_setting("localization_root_path", directory)
            self.log_message(f"本地化目录设置为: {directory}", "info")

            # 自动扫描YML文件
            self._scan_yml_files(directory)

    def _set_style_preset(self, style_text):
        """设置预设翻译风格"""
        self.style_text.delete(1.0, tk.END)
        self.style_text.insert(1.0, style_text)
        self.game_mod_style_prompt.set(style_text)
        self.config_manager.set_setting("game_mod_style", style_text)
        self.log_message("翻译风格已更新", "info")

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

        index = selection[0]
        keys = self.config_manager.get_api_keys()
        if index >= len(keys):
            return

        key_to_remove = keys[index]

        # 确认删除
        if messagebox.askyesno(
            "确认删除",
            f"确定要删除API密钥 ...{key_to_remove[-4:]} 吗？"
        ):
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
        import os
        yml_files = []

        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.yml', '.yaml')):
                        yml_files.append(os.path.join(root, file))

            # 更新文件列表
            self.files_for_translation = yml_files
            self._refresh_file_list()

            self.log_message(f"扫描完成，找到 {len(yml_files)} 个YML文件", "info")

        except Exception as e:
            self.log_message(f"扫描文件时发生错误: {e}", "error")

    def _refresh_file_list(self):
        """刷新文件列表显示"""
        self.files_listbox.delete(0, tk.END)

        for file_path in self.files_for_translation:
            # 只显示文件名
            filename = os.path.basename(file_path)
            self.files_listbox.insert(tk.END, filename)

    def _on_model_changed(self, event=None):
        """模型选择改变事件"""
        model = self.selected_model_var.get()
        if model:
            self.config_manager.set_setting("selected_model", model)
            self.log_message(f"AI模型设置为: {model}", "info")

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

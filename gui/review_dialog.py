"""
翻译评审对话框

提供翻译结果的人工评审界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, LEFT, RIGHT, W, X
from typing import Set, Optional, Callable, Any


class ReviewDialog(tk.Toplevel):
    """翻译评审对话框"""
    
    def __init__(
        self, 
        parent_app_instance: Any, 
        root_window: tk.Tk, 
        original_text: str, 
        ai_translation: str, 
        original_placeholders: Set[str], 
        translated_placeholders: Set[str], 
        key_name: str, 
        completion_callback: Optional[Callable] = None
    ):
        """
        初始化评审对话框
        
        Args:
            parent_app_instance: 父应用程序实例
            root_window: 根窗口
            original_text: 原文
            ai_translation: AI翻译结果
            original_placeholders: 原文占位符集合
            translated_placeholders: 翻译占位符集合
            key_name: 键名
            completion_callback: 完成回调函数
        """
        super().__init__(root_window)
        
        # 在完全构建UI之前隐藏窗口
        self.withdraw()
        
        # 设置窗口属性
        self.transient(root_window)
        self.grab_set()
        self.app = parent_app_instance 
        self.original_text_arg = original_text 
        self.result: Optional[str] = None 
        self.key_name_arg = key_name
        self.completion_callback = completion_callback

        # 调整窗口属性
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.app.log_message(f"ReviewDialog initializing for key: {key_name}", "debug")
        self.title(f"评审翻译: {key_name}")
        
        # 设置图标图像(如果有)
        try:
            if hasattr(self.app.root, 'iconphoto'):
                self.iconphoto(False, self.app.root.iconphoto)
        except Exception:
            pass
            
        # 使用与主界面相同的样式
        self.style = root_window.style if hasattr(root_window, 'style') else None
        if self.style:
            self.style.configure('ReviewDialog.TLabel', font=('Default', 10, 'bold'))
            self.style.configure('ReviewDialog.TButton', font=('Default', 10))
        
        # 创建UI
        self._create_ui(original_text, ai_translation, original_placeholders, translated_placeholders, key_name)
        
        # 设置窗口位置和大小
        self._setup_window_geometry()
        
        # 显示窗口
        self._show_window()

    def _create_ui(
        self, 
        original_text: str, 
        ai_translation: str, 
        original_placeholders: Set[str], 
        translated_placeholders: Set[str], 
        key_name: str
    ) -> None:
        """创建用户界面"""
        # 创建清晰分明的卡片式布局
        main_container = ttk.Frame(self, padding=15)
        main_container.pack(expand=True, fill=tk.BOTH)
        
        # 允许窗口大小调整
        self.resizable(True, True)
        self.minsize(700, 600)
        
        # 顶部标题区域
        self._create_header(main_container, key_name)
        
        # 原文卡片
        self._create_original_text_card(main_container, original_text)
        
        # AI翻译卡片
        self._create_ai_translation_card(main_container, ai_translation)
        
        # 编辑区卡片
        self._create_edit_card(main_container, ai_translation)
        
        # 占位符分析区
        self._create_placeholder_analysis_card(main_container, original_placeholders, translated_placeholders)
        
        # 底部按钮区域
        self._create_button_area(main_container)

    def _create_header(self, parent: ttk.Frame, key_name: str) -> None:
        """创建头部区域"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            header_frame, 
            text="📝 翻译评审", 
            font=('Default', 14, 'bold')
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame, 
            text=f"Key: {key_name}", 
            font=('Default', 10)
        ).pack(side=tk.RIGHT)

    def _create_original_text_card(self, parent: ttk.Frame, original_text: str) -> None:
        """创建原文卡片"""
        original_card = ttk.Frame(parent, relief="solid", borderwidth=1)
        original_card.pack(fill=tk.X, pady=(0, 15), padx=2)
        
        original_header = ttk.Frame(original_card, padding=(10, 5))
        original_header.pack(fill=tk.X)
        
        ttk.Label(
            original_header, 
            text="📝 原文 (Original Text)", 
            font=('Default', 11, 'bold'),
            foreground="#333333"
        ).pack(anchor=W)
        
        original_content = ttk.Frame(original_card, padding=(10, 5, 10, 10))
        original_content.pack(fill=tk.X)
        
        original_text_widget = scrolledtext.ScrolledText(
            original_content, 
            height=6, 
            wrap=tk.WORD, 
            relief="flat",
            font=('Default', 10)
        )
        original_text_widget.insert(tk.END, original_text)
        original_text_widget.configure(state='disabled')
        original_text_widget.pack(fill=X)

    def _create_ai_translation_card(self, parent: ttk.Frame, ai_translation: str) -> None:
        """创建AI翻译卡片"""
        ai_card = ttk.Frame(parent, relief="solid", borderwidth=1)
        ai_card.pack(fill=X, pady=(0, 15), padx=2)
        
        ai_header = ttk.Frame(ai_card, padding=(10, 5))
        ai_header.pack(fill=X)
        
        ttk.Label(
            ai_header, 
            text="🤖 AI 翻译 (可能存在占位符问题)", 
            font=('Default', 11, 'bold'),
            foreground="#0066cc"
        ).pack(anchor=W)
        
        ai_content = ttk.Frame(ai_card, padding=(10, 5, 10, 10))
        ai_content.pack(fill=X)
        
        ai_translation_widget = scrolledtext.ScrolledText(
            ai_content, 
            height=6, 
            wrap=tk.WORD, 
            relief="flat",
            font=('Default', 10)
        )
        ai_translation_widget.insert(tk.END, ai_translation if ai_translation else "AI translation was empty.")
        ai_translation_widget.configure(state='disabled')
        ai_translation_widget.pack(fill=X)

    def _create_edit_card(self, parent: ttk.Frame, ai_translation: str) -> None:
        """创建编辑区卡片"""
        edit_card = ttk.Frame(parent, relief="solid", borderwidth=1)
        edit_card.pack(fill=BOTH, expand=True, pady=(0, 15), padx=2)
        
        edit_header = ttk.Frame(edit_card, padding=(10, 5))
        edit_header.pack(fill=X)
        
        ttk.Label(
            edit_header, 
            text="✏️ 您的编辑 (可在此修改翻译)", 
            font=('Default', 11, 'bold'),
            foreground="#009900"
        ).pack(anchor=W)
        
        edit_content = ttk.Frame(edit_card, padding=(10, 5, 10, 10))
        edit_content.pack(fill=BOTH, expand=True)
        
        self.edited_text_widget = scrolledtext.ScrolledText(
            edit_content, 
            height=8, 
            wrap=tk.WORD, 
            relief="flat",
            font=('Default', 10)
        )
        self.edited_text_widget.insert(tk.END, ai_translation if ai_translation else "")
        self.edited_text_widget.pack(fill=BOTH, expand=True)

    def _create_placeholder_analysis_card(
        self,
        parent: ttk.Frame,
        original_placeholders: Set[str],
        translated_placeholders: Set[str]
    ) -> None:
        """创建占位符分析卡片"""
        ph_card = ttk.Frame(parent, relief="solid", borderwidth=1)
        ph_card.pack(fill=X, pady=(0, 15), padx=2)

        # 设置标题文本和颜色
        ph_title = "📊 占位符分析"
        ph_color = "#333333"

        # 检查占位符问题
        missing_in_ai = original_placeholders - translated_placeholders
        added_in_ai = translated_placeholders - original_placeholders
        if missing_in_ai or added_in_ai:
            ph_title = "⚠️ 检测到占位符问题!"
            ph_color = "#cc6600"

        ph_header = ttk.Frame(ph_card, padding=(10, 5))
        ph_header.pack(fill=X)

        ttk.Label(
            ph_header,
            text=ph_title,
            font=('Default', 11, 'bold'),
            foreground=ph_color
        ).pack(anchor=W)

        ph_content = ttk.Frame(ph_card, padding=(10, 5, 10, 10))
        ph_content.pack(fill=X)

        ph_columns = ttk.Frame(ph_content)
        ph_columns.pack(fill=X)
        ph_columns.columnconfigure(0, weight=1)
        ph_columns.columnconfigure(1, weight=1)

        # 原文占位符区域
        self._create_placeholder_section(
            ph_columns,
            "原文占位符:",
            original_placeholders,
            0, 0,
            (0, 5)
        )

        # AI翻译占位符区域
        self._create_placeholder_section(
            ph_columns,
            "AI翻译占位符:",
            translated_placeholders,
            0, 1,
            (5, 0)
        )

        # 占位符问题详细信息
        if missing_in_ai or added_in_ai:
            self._create_placeholder_diff_info(ph_content, missing_in_ai, added_in_ai)

    def _create_placeholder_section(
        self,
        parent: ttk.Frame,
        title: str,
        placeholders: Set[str],
        row: int,
        column: int,
        padx: tuple
    ) -> None:
        """创建占位符显示区域"""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=column, sticky="nsew", padx=padx)

        ttk.Label(
            frame,
            text=title,
            font=('Default', 9, 'bold')
        ).pack(anchor=W, pady=(0, 3))

        scrolled_text = scrolledtext.ScrolledText(
            frame,
            height=4,
            wrap=tk.WORD,
            relief="flat",
            borderwidth=1,
            font=('Consolas', 9)
        )
        scrolled_text.insert(tk.END, "\n".join(sorted(list(placeholders))) if placeholders else "无")
        scrolled_text.configure(state='disabled')
        scrolled_text.pack(fill=X)

    def _create_placeholder_diff_info(
        self,
        parent: ttk.Frame,
        missing_in_ai: Set[str],
        added_in_ai: Set[str]
    ) -> None:
        """创建占位符差异信息"""
        diff_frame = ttk.Frame(parent)
        diff_frame.pack(fill=X, pady=(5, 0))

        diff_report = []
        if missing_in_ai:
            diff_report.append(f"⚠️ AI翻译中缺失: {', '.join(sorted(list(missing_in_ai)))}")
        if added_in_ai:
            diff_report.append(f"⚠️ AI翻译中多出: {', '.join(sorted(list(added_in_ai)))}")

        diff_label = ttk.Label(
            diff_frame,
            text="详细信息: " + "; ".join(diff_report),
            foreground="#cc0000",
            wraplength=750,
            font=('Default', 9)
        )
        diff_label.pack(anchor=W)

    def _create_button_area(self, parent: ttk.Frame) -> None:
        """创建按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=X, pady=(0, 5))

        # 帮助提示
        ttk.Label(
            button_frame,
            text="提示: 编辑文本后点击'确认并继续'，或直接使用原文/AI翻译",
            font=('Default', 8),
            foreground="#666666"
        ).pack(side=LEFT)

        # 按钮区域
        button_panel = ttk.Frame(button_frame)
        button_panel.pack(side=RIGHT)

        # 创建按钮
        self._create_buttons(button_panel)

        # 绑定键盘快捷键
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Return>", lambda e: self._on_confirm())

        # 添加按钮工具提示
        self._add_tooltips()

    def _create_buttons(self, parent: ttk.Frame) -> None:
        """创建按钮"""
        self.cancel_button = ttkb.Button(
            parent,
            text="取消",
            command=self._on_cancel,
            bootstyle="secondary",
            width=10,
            cursor="hand2"
        )
        self.cancel_button.pack(side=LEFT, padx=5)

        self.use_original_button = ttkb.Button(
            parent,
            text="使用原文",
            command=self._on_use_original,
            bootstyle="warning",
            width=10,
            cursor="hand2"
        )
        self.use_original_button.pack(side=LEFT, padx=5)

        self.skip_button = ttkb.Button(
            parent,
            text="使用AI翻译",
            command=self._on_skip_with_ai_text,
            bootstyle="info",
            width=12,
            cursor="hand2"
        )
        self.skip_button.pack(side=LEFT, padx=5)

        self.confirm_button = ttkb.Button(
            parent,
            text="确认并继续",
            command=self._on_confirm,
            bootstyle="success",
            width=12,
            cursor="hand2",
            default="active"
        )
        self.confirm_button.pack(side=LEFT, padx=5)

    def _add_tooltips(self) -> None:
        """添加按钮工具提示"""
        try:
            from ttkbootstrap.tooltip import ToolTip
            ToolTip(self.confirm_button, text="保存您的编辑并继续下一个翻译", delay=500)
            ToolTip(self.skip_button, text="直接使用AI翻译结果", delay=500)
            ToolTip(self.use_original_button, text="保留原文不翻译", delay=500)
            ToolTip(self.cancel_button, text="取消评审", delay=500)
        except (ImportError, AttributeError):
            pass

    def _setup_window_geometry(self) -> None:
        """设置窗口几何属性"""
        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 设置更合理的初始大小（根据屏幕大小调整）
        dialog_width = min(1024, int(screen_width * 0.75))
        dialog_height = min(800, int(screen_height * 0.75))

        # 设置窗口大小
        self.geometry(f"{dialog_width}x{dialog_height}")

        # 更新窗口，确保所有UI元素都准备好了
        self.update_idletasks()

        # 居中显示窗口
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 确保窗口在屏幕内
        self.ensure_on_screen()

    def ensure_on_screen(self) -> None:
        """确保窗口完全在屏幕内"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # 获取窗口当前位置和尺寸
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        x = self.winfo_x()
        y = self.winfo_y()

        # 检查并调整位置
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x + window_width > screen_width:
            x = max(0, screen_width - window_width)
        if y + window_height > screen_height:
            y = max(0, screen_height - window_height)

        # 如果窗口太大，调整大小
        if window_width > screen_width:
            window_width = screen_width - 50
            x = 25
        if window_height > screen_height:
            window_height = screen_height - 50
            y = 25

        # 应用最终位置和大小
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _show_window(self) -> None:
        """显示窗口"""
        # 在显示窗口之前再次更新以确保所有计算完成
        self.update_idletasks()

        # 显示窗口
        self.deiconify()
        self.lift()
        self.focus_force()
        self.edited_text_widget.focus_set()
        self.app.log_message(f"ReviewDialog for key '{self.key_name_arg}' displayed.", "debug")

    def _on_confirm(self) -> None:
        """确认按钮回调"""
        self.result = self.edited_text_widget.get("1.0", tk.END).strip()
        self.app.log_message(f"ReviewDialog: Confirmed text for key '{self.key_name_arg}'", "debug")
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result)
        self.destroy()

    def _on_use_original(self) -> None:
        """使用原文按钮回调"""
        self.result = self.original_text_arg
        self.app.log_message(f"ReviewDialog: Using original text for key '{self.key_name_arg}'", "debug")
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result)
        self.destroy()

    def _on_skip_with_ai_text(self) -> None:
        """使用AI翻译按钮回调"""
        self.result = self.edited_text_widget.get("1.0", tk.END).strip()
        self.app.log_message(f"ReviewDialog: Using AI text (current edit box) for key '{self.key_name_arg}'", "debug")
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result)
        self.destroy()

    def _on_cancel(self) -> None:
        """取消按钮回调"""
        self.result = None
        self.app.log_message(f"ReviewDialog: Cancelled for key '{self.key_name_arg}'", "debug")
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result)
        self.destroy()

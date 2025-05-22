import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import BOTH, BOTTOM, CENTER, DISABLED, E, HORIZONTAL, LEFT, RIGHT, TOP, W, X, Y
import os
import re
import threading
import time 
import queue 
import json
from google.api_core.exceptions import ResourceExhausted
from collections import deque

# 全局API锁
GEMINI_API_LOCK = threading.RLock()

# 每分钟令牌数(TPM)定义
MODEL_TPM = {
    "models/gemini-2.0-flash-lite": 1000000,
    "models/gemini-2.0-flash": 1000000,
}

# 每分钟请求数(RPM)定义
MODEL_RPM = {
    "models/gemini-2.0-flash-lite": 30,
    "models/gemini-2.0-flash": 15,
}

# Attempt to import Gemini library
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None # Placeholder if library not found

# --- Configuration ---
CONFIG_FILE = "translator_config.json"
DEFAULT_API_KEY_PLACEHOLDER = "YOUR_GEMINI_API_KEY" 

# --- ConfigManager Class ---
class ConfigManager:
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path
        self.defaults = {
            "source_language": "english",
            "target_language": "simp_chinese",
            "game_mod_style": "General video game localization, maintain tone of original.",
            "selected_model": "gemini-1.5-flash-latest", # Updated default
            "localization_root_path": "",
            "api_keys": [DEFAULT_API_KEY_PLACEHOLDER],  # 改为API密钥列表
            "api_call_delay": 3.0, # 默认API调用间隔时间(秒)
            "max_concurrent_tasks": 3,  # 默认并行任务数
            "auto_review_mode": True,  # 默认自动评审模式
            "delayed_review": True,  # 默认延迟评审模式
            "key_rotation_strategy": "round_robin"  # 默认密钥轮换策略: round_robin, load_balanced, priority
        }
        self.config = self.load_config()
        
        # 兼容性处理：将旧版单API密钥配置转换为新版多密钥配置
        self._migrate_legacy_api_key()

    def load_config(self):
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Ensure all default keys are present
                for key, default_value in self.defaults.items():
                    if key not in loaded_config:
                        loaded_config[key] = default_value
                return loaded_config
        except FileNotFoundError:
            print(f"Config file not found at {self.config_file_path}. Creating with defaults.")
            return self.defaults.copy() # Return a copy
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {self.config_file_path}. Using defaults.")
            return self.defaults.copy()
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return self.defaults.copy()

    def save_config(self):
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            # print(f"Config saved to {self.config_file_path}") # Optional: for debugging
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_setting(self, key, default_override=None):
        if default_override is not None:
            return self.config.get(key, default_override)
        return self.config.get(key, self.defaults.get(key))    
    
    def set_setting(self, key, value):
        self.config[key] = value
        self.save_config() # 即时保存设置，确保在异常关闭时不丢失修改
        
    def get_api_keys(self):
        """获取所有配置的API密钥"""
        keys = self.get_setting("api_keys", [DEFAULT_API_KEY_PLACEHOLDER])
        # 过滤掉空密钥和占位符密钥
        valid_keys = [k for k in keys if k and k != DEFAULT_API_KEY_PLACEHOLDER]
        return valid_keys
    
    def add_api_key(self, new_key):
        """添加新的API密钥"""
        if not new_key or new_key == DEFAULT_API_KEY_PLACEHOLDER:
            return False
            
        keys = self.get_setting("api_keys", [])
        if not isinstance(keys, list):
            keys = [keys] if keys else []
            
        # 避免重复添加
        if new_key not in keys:
            keys.append(new_key)
            self.set_setting("api_keys", keys)
            return True
        return False
    
    def remove_api_key(self, key_to_remove):
        """移除指定的API密钥"""
        keys = self.get_setting("api_keys", [])
        if not isinstance(keys, list):
            keys = [keys] if keys else []
            
        if key_to_remove in keys:
            keys.remove(key_to_remove)
            # 如果移除后列表为空，添加一个占位符
            if not keys:
                keys = [DEFAULT_API_KEY_PLACEHOLDER]
            self.set_setting("api_keys", keys)
            return True
        return False
    
    def update_api_key(self, old_key, new_key):
        """更新API密钥"""
        if not new_key or new_key == DEFAULT_API_KEY_PLACEHOLDER:
            return False
            
        keys = self.get_setting("api_keys", [])
        if not isinstance(keys, list):
            keys = [keys] if keys else []
            
        if old_key in keys:
            index = keys.index(old_key)
            keys[index] = new_key
            self.set_setting("api_keys", keys)
            return True
        return False

    def _migrate_legacy_api_key(self):
        """将旧版单API密钥配置转换为新版多密钥配置"""
        if "api_key" in self.config and "api_keys" not in self.config:
            # 如果存在旧版api_key但不存在新版api_keys，则进行迁移
            legacy_key = self.config.pop("api_key")
            if legacy_key and legacy_key != DEFAULT_API_KEY_PLACEHOLDER:
                self.config["api_keys"] = [legacy_key]
            else:
                self.config["api_keys"] = [DEFAULT_API_KEY_PLACEHOLDER]
            self.save_config()
            print("已将旧版API密钥配置迁移到新版多密钥配置")
        
        # 确保api_keys始终是一个列表
        if "api_keys" in self.config and not isinstance(self.config["api_keys"], list):
            self.config["api_keys"] = [self.config["api_keys"]]
            self.save_config()
    

# --- YML Parsing Logic (Unchanged from previous version) ---
class YMLParser:
    ENTRY_REGEX = re.compile(r'^\s*([a-zA-Z0-9_.-]+)\s*:\s*(?:\d+\s*)?"((?:\\.|[^"\\])*)"\s*$', re.UNICODE)
    LANGUAGE_HEADER_REGEX = re.compile(r"^\s*l_([a-zA-Z_]+)\s*:\s*$", re.UNICODE)
    PLACEHOLDER_REGEXES = [
        re.compile(r'(\$.*?\$)'),       # 变量占位符，如$variable$
        re.compile(r'(\[.*?\])'),       # 方括号占位符，如[player.GetName]
        re.compile(r'(@\w+!)'),         # 图标占位符，如@icon!
        re.compile(r'(#\w+(?:;\w+)*.*?#!|\S*#!)'), # 格式化标记，如#bold#文本#!
    ]

    @staticmethod
    def extract_placeholders(text):
        placeholders = set()
        for regex in YMLParser.PLACEHOLDER_REGEXES:
            found = regex.findall(text)
            for item in found:
                placeholders.add(item[0] if isinstance(item, tuple) else item)
        return placeholders

    @staticmethod
    def load_file(filepath):
        entries = []
        language_code = None
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            if not lines:
                return None, []
            header_match = YMLParser.LANGUAGE_HEADER_REGEX.match(lines[0])
            if header_match:
                language_code = header_match.group(1)
            else:
                basename = os.path.basename(filepath)
                match_filename_lang = re.search(r'_l_([a-zA-Z_]+)\.yml$', basename)
                if match_filename_lang:
                    language_code = match_filename_lang.group(1)
                else:
                    return None, []
            for i, line_content in enumerate(lines):
                if i == 0 and header_match:
                    continue
                match = YMLParser.ENTRY_REGEX.match(line_content)
                if match:
                    key, value = match.group(1), match.group(2)
                    processed_value = value.replace('\\"', '"').replace('\\n', '\n')
                    entries.append({'key': key, 'value': processed_value, 
                                    'original_line_content': line_content.rstrip('\n\r'), 'line_number': i + 1})
            return language_code, entries
        except Exception as e:
            print(f"YMLParser: Error loading file {filepath}: {e}")
            return None, []

    @staticmethod
    def save_file(filepath, language_code, translated_entries, original_source_lang_code):
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write(f"l_{language_code}:\n")
                current_keys = set()
                for entry in translated_entries:
                    if entry['key'] in current_keys:
                        continue
                    current_keys.add(entry['key'])
                    value_to_write = entry['translated_value'].replace('"', '\\"').replace('\n', '\\n')
                    original_line_match = YMLParser.ENTRY_REGEX.match(entry['original_line_content'])
                    if original_line_match:
                        original_key_part = entry['original_line_content'].split('"')[0]
                        key_part_match = re.match(r'\s*([a-zA-Z0-9_.-]+)\s*:\s*(\d*)\s*', original_key_part)
                        if key_part_match and key_part_match.group(2):
                            f.write(f" {key_part_match.group(1)}:{key_part_match.group(2)} \"{value_to_write}\"\n")
                        else:
                            f.write(f" {entry['key']}: \"{value_to_write}\"\n")
                    else:
                        f.write(f" {entry['key']}: \"{value_to_write}\"\n")
        except Exception as e:
            print(f"YMLParser: Error saving file {filepath}: {e}")


# --- API Key Manager ---
class APIKeyManager:
    """管理多个API密钥，提供负载均衡和故障转移功能"""
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.keys = []  # 有效的API密钥列表
        self.key_stats = {}  # 每个密钥的使用统计
        self.current_index = 0  # 当前使用的密钥索引
        self.failed_keys = set()  # 失败的密钥集合
        self.key_locks = {}  # 每个密钥的锁，防止并发访问冲突
        self.global_lock = threading.RLock()  # 全局锁，用于保护共享资源
        self.reload_keys()
    
    def reload_keys(self):
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
    
    def get_next_key(self, strategy=None):
        """根据策略获取下一个要使用的API密钥"""
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
    
    def mark_key_success(self, key, token_count=None):
        """标记密钥使用成功"""
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
    
    def mark_key_failure(self, key, error_type=None):
        """标记密钥使用失败"""
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
    
    def get_key_stats(self):
        """获取所有密钥的使用统计"""
        with self.global_lock:
            return {k: v.copy() for k, v in self.key_stats.items()}
    
    def has_valid_keys(self):
        """检查是否有有效的API密钥"""
        with self.global_lock:
            return len(self.keys) > 0 and len(self.keys) > len(self.failed_keys)
    
    def get_all_keys(self):
        """获取所有API密钥"""
        with self.global_lock:
            return self.keys.copy()

# --- Translator Logic (Actual Gemini API) ---
class GeminiTranslator:
    def __init__(self, app_ref, api_key_provider_func, translator_id="default_translator"): # 添加 translator_id
        self.app_ref = app_ref
        self.api_key_provider_func = api_key_provider_func # Function to get current API key # 这个参数可能不再需要，因为密钥会直接传递
        self.current_api_key = None # Will be set by _configure_gemini
        # 记录最近10次 token_count (滑动窗口)
        self.token_window = deque(maxlen=10)
        self.failed_translations = []
        self.translator_id = translator_id # 赋值 translator_id
        # Configuration is deferred until API key is confirmed available or first translation attempt
        # self._configure_gemini() # Don't call immediately, wait for UI to be ready for logging

    def _configure_gemini(self, api_key_to_use): # 接受 api_key_to_use
        """Configures the Gemini API with the provided key. Returns True on success."""
        if not GEMINI_AVAILABLE:
            self.app_ref.log_message(f"翻译器 {self.translator_id}: Gemini library (google-generativeai) is not installed. Translation will be simulated.", "error")
            return False
        
        # api_key_from_gui = self.api_key_provider_func() # 不再从 GUI 获取，直接使用传入的密钥

        if not api_key_to_use or api_key_to_use == DEFAULT_API_KEY_PLACEHOLDER:
            self.app_ref.log_message(f"翻译器 {self.translator_id}: Gemini API Key is not set or is a placeholder. Please set it in config.", "error")
            self.current_api_key = None # Ensure current_api_key is None if config fails
            return False
        try:
            with GEMINI_API_LOCK: # 使用全局锁保护配置
                genai.configure(api_key=api_key_to_use)
            self.current_api_key = api_key_to_use # Store the successfully configured key
            self.app_ref.log_message(f"翻译器 {self.translator_id}: Gemini API configured successfully with key ending in ...{api_key_to_use[-4:]}.", "info")
            return True
        except Exception as e:
            self.app_ref.log_message(f"翻译器 {self.translator_id}: Failed to configure Gemini API: {e}", "error")
            self.current_api_key = None # Ensure current_api_key is None if config fails
            return False

    def _build_prompt(self, text_to_translate, source_lang_name, target_lang_name, game_mod_style):
        style_info = f"游戏/Mod风格提示: {game_mod_style}\n" if game_mod_style else ""
        
        use_chinese_specific_prompt = (target_lang_name.lower() == "simp_chinese" and source_lang_name.lower() == "english") or \
                                      (source_lang_name.lower() == "simp_chinese" and target_lang_name.lower() == "english") # Simplified for example

        if use_chinese_specific_prompt:
            prompt = f"""角色定位:
你是一位专业的双语翻译专家，精通 {source_lang_name} 与 {target_lang_name} 互译。你特别擅长根据原文的风格进行翻译，并完整保留所有特殊占位符。
{style_info}
任务:
请对以下提供的"原文"({source_lang_name})文本执行三步翻译法，将其翻译为{target_lang_name}。

原文 ({source_lang_name}):
{text_to_translate}

翻译流程与输出格式要求:
请严格按照以下步骤和格式提供完整的翻译结果。不要添加任何额外的说明、确认或对话性文字。

第一步：直译 ({target_lang_name})
[此处输出对上述"原文"的完整、准确的{target_lang_name}直译，严格保留所有格式和特殊占位符，如 [...]、$variable$、@icon!、#formatting#! 等。]

第二步：直译中的问题与改进建议
[此处输出针对第一步直译内容的具体问题分析和改进建议。]

第三步：意译 ({target_lang_name}) - 最终交付成果
$$
[此处输出基于直译和改进建议优化后的最终{target_lang_name}意译。此部分必须严格使用$$符号包裹，并且是整个输出中唯一被$$包裹的部分。确保所有原文的特殊占位符在此意译版本中被精确无误地保留。]
$$
"""
        else: # Generic prompt for other language pairs
            prompt = f"""As a professional bilingual translation expert, proficient in {source_lang_name} and {target_lang_name}, your task is to translate the following text.
Game/Mod Style: {game_mod_style if game_mod_style else "General"}
You MUST preserve all placeholders like [...], $...$, @...! and #...! exactly as they appear in the original text.

Original Text ({source_lang_name}):
{text_to_translate}

Provide ONLY the final translated text in {target_lang_name}, wrapped strictly in double dollar signs ($$). Do not include any other explanatory text, conversational phrases, or the original text again.
Example: $$Translated text here, with all original [placeholders] and $variables$ preserved.$$
"""
        return prompt
    def _call_actual_api(self, prompt_text, model_name, api_key_for_this_call): # 接受 api_key_for_this_call
        """Calls the actual Gemini API."""
        if not GEMINI_AVAILABLE:
            # 返回符合格式要求的模拟响应，使其可以被正确解析
            simulated_text = f"$${prompt_text[:100]}... [模拟翻译结果]$$"
            self.app_ref.log_message(f"翻译器 {self.translator_id}: 使用模拟模式进行翻译（API库不可用）", "warn")
            return simulated_text, 0 # 返回模拟的token_count

        # Ensure Gemini is configured. If current_api_key doesn't match what's in the GUI,
        # or if current_api_key is None (meaning it was never successfully configured or failed), reconfigure.
        # gui_api_key = self.api_key_provider_func() # 不再需要
        with GEMINI_API_LOCK: # 使用全局锁保护 API 调用前的配置和调用本身
            if self.current_api_key is None or self.current_api_key != api_key_for_this_call:
                self.app_ref.log_message(f"翻译器 {self.translator_id}: API key mismatch or not configured, attempting to reconfigure Gemini for key ...{api_key_for_this_call[-4:]}.", "debug")
                if not self._configure_gemini(api_key_for_this_call): # Attempt to reconfigure with the specific key
                    self.app_ref.log_message(f"翻译器 {self.translator_id}: Gemini API not configured with key ...{api_key_for_this_call[-4:]}. Cannot translate.", "error")
                    return None, "CONFIG_FAILURE" # 返回错误类型

            try:
                self.app_ref.log_message(f"翻译器 {self.translator_id}: Calling Gemini API with model: {model_name} using key ...{api_key_for_this_call[-4:]}...", "info")
                
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt_text, request_options={'timeout': 120}) 
                
                if not response.parts:
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        block_reason_msg = f"Content blocked by API. Reason: {response.prompt_feedback.block_reason}."
                        if response.prompt_feedback.safety_ratings:
                            block_reason_msg += f" Safety Ratings: {response.prompt_feedback.safety_ratings}"
                        self.app_ref.log_message(block_reason_msg, "error")
                        return None, "API_CALL_FAILED_NO_TEXT"
                    self.app_ref.log_message("Gemini API returned an empty response or no text part.", "warn")
                    return None, "API_CALL_FAILED_NO_TEXT"

                # 获取token使用信息 - 根据Gemini API响应结构提取
                token_count = None
                usage_metadata = getattr(response, 'usage_metadata', None)
                
                if usage_metadata:
                    # 新版Gemini API使用usage_metadata
                    token_count = getattr(usage_metadata, 'total_token_count', None)
                    prompt_tokens = getattr(usage_metadata, 'prompt_token_count', None)
                    candidates_tokens = getattr(usage_metadata, 'candidates_token_count', None)
                    self.app_ref.log_message(
                        f"Token使用详情 - 总计: {token_count}, 提示: {prompt_tokens}, 响应: {candidates_tokens}",
                        "debug"
                    )
                else:
                    # 尝试旧版方式获取
                    token_count = getattr(response, 'token_count', None)
                    if token_count is None:
                        self.app_ref.log_message("无法从API响应中获取token使用信息", "warn")
                
                return response.text, token_count
            except Exception as e:
                self.app_ref.log_message(f"翻译器 {self.translator_id}: Gemini API调用错误: {e}", "error")
                if "API_KEY_INVALID" in str(e) or "API_KEY_MISSING" in str(e) or "Malformed" in str(e): # Added "Malformed" for common key issues
                    self.app_ref.log_message(f"翻译器 {self.translator_id}: 请检查您的Gemini API Key设置，可能无效或格式错误。", "error")
                    # 返回错误类型，以便APIKeyManager可以标记此密钥为失败
                    return None, "API_KEY_INVALID"
                elif "Rate limit exceeded" in str(e) or "429" in str(e) or "quota exceeded" in str(e):
                    # 返回错误类型，以便APIKeyManager可以标记此密钥为速率限制
                    return None, "Rate limit exceeded"
                return None, str(e)

    def extract_final_translation(self, api_response_text):
        if api_response_text is None:
            return None
        # More robust regex to capture content within $$...$$, allowing for newlines inside.
        match = re.search(r"\$\$\s*(.*?)\s*\$\$", api_response_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Log extended information if extraction fails
        self.app_ref.log_message(f"翻译器 {self.translator_id}: 无法从响应中提取最终翻译 (使用 $$...$$).", "warn")
        self.app_ref.log_message(f"翻译器 {self.translator_id}: 完整的API响应文本如下:", "debug")
        self.app_ref.log_message(f"-------------------- API Response Start --------------------", "debug")
        # Log in chunks to avoid overly long single log messages if the response is huge
        for i in range(0, len(api_response_text), 500):
            self.app_ref.log_message(api_response_text[i:i+500], "debug")
        self.app_ref.log_message(f"-------------------- API Response End ----------------------", "debug")
        return None # Return None if extraction fails

    def translate(self, text_to_translate, source_lang_name, target_lang_name, game_mod_style, model_name, api_key_to_use): # 接受 api_key_to_use, 移除动态延迟逻辑
        if not text_to_translate.strip():
            self.app_ref.log_message(f"翻译器 {self.translator_id}: 输入文本为空，直接返回空翻译。", "info")
            return "", 0, None # 返回空翻译, 0 token_count, 无错误

        prompt = self._build_prompt(text_to_translate, source_lang_name, target_lang_name, game_mod_style)
        self.app_ref.log_message(f"翻译器 {self.translator_id}: 翻译中 (使用密钥 ...{api_key_to_use[-4:]}): '{text_to_translate[:50]}...'", "debug")
        
        # 动态速率限制逻辑已移除，将由调用者（如ParallelTranslator）处理
        
        # 调用实际API并获取 token_count，添加重试机制
        max_retries = 3
        backoff_times = [2, 4, 8] # 指数退避时间
        last_error_type = "UNKNOWN_ERROR"

        for attempt in range(1, max_retries + 1):
            # result = self._call_actual_api(prompt, model_name) # 旧的调用方式
            raw_text, token_count_or_error = self._call_actual_api(prompt, model_name, api_key_to_use)

            if raw_text is not None: # API调用成功（可能返回空文本，但不是None）
                final_translation = self.extract_final_translation(raw_text)
                # 更新滑动窗口中的token计数并记录使用情况
                if isinstance(token_count_or_error, int) and token_count_or_error >= 0:
                    self.token_window.append(token_count_or_error)
                    self.app_ref.log_message(
                        f"翻译器 {self.translator_id}: API调用token使用量: {token_count_or_error} tokens，文本长度: {len(text_to_translate)} 字符",
                        "info"
                    )
                    # 滑动窗口状态日志 （可选，如果需要频繁监控）
                    # avg_tokens = sum(self.token_window) / len(self.token_window)
                    # self.app_ref.log_message(
                    #     f"翻译器 {self.translator_id}: 滑动窗口更新: 平均token={avg_tokens:.1f} (最近{len(self.token_window)}/{self.token_window.maxlen}次调用)",
                    #     "debug"
                    # )
                else:
                    self.app_ref.log_message(f"翻译器 {self.translator_id}: 警告: 无法获取本次API调用的token使用量或返回错误标识。", "warn")
                
                return final_translation or text_to_translate, token_count_or_error, None # 成功，返回None作为错误类型
            
            # API调用失败，raw_text is None
            last_error_type = token_count_or_error if isinstance(token_count_or_error, str) else "API_CALL_FAILED_UNKNOWN"
            self.app_ref.log_message(f"翻译器 {self.translator_id}: API调用尝试 {attempt}/{max_retries} 失败。错误: {last_error_type}", "warn")

            if last_error_type in ["API_KEY_INVALID", "API_KEY_MISSING", "Malformed", "CONFIG_FAILURE"]:
                self.app_ref.log_message(f"翻译器 {self.translator_id}: 致命错误 ({last_error_type})，不进行重试。", "error")
                break # 不重试此类错误

            if attempt < max_retries:
                delay = backoff_times[attempt - 1]
                self.app_ref.log_message(f"翻译器 {self.translator_id}: 将在 {delay} 秒后重试...", "warn")
                time.sleep(delay)
            else:
                self.app_ref.log_message(f"翻译器 {self.translator_id}: 所有 {max_retries} 次重试均失败。", "error")

        # 所有重试失败后或遇到致命错误
        self.failed_translations.append((text_to_translate, last_error_type))
        return text_to_translate, 0, last_error_type # 返回原文，0 token，和最后的错误类型
        
    def _auto_adjust_api_delay(self, increase_by=1):
        """在遇到API速率限制时自动增加API调用延迟的最小值"""
        current_delay = float(self.app_ref.config_manager.get_setting("api_call_delay", 3.0))
        new_delay = min(current_delay + increase_by, 10.0)  # 最大不超过10秒
        
        if new_delay > current_delay:
            self.app_ref.config_manager.set_setting("api_call_delay", new_delay)
            self.app_ref.config_manager.save_config()
            
            # 如果GUI存在，更新GUI显示
            if hasattr(self.app_ref, "api_call_delay_var"):
                self.app_ref.api_call_delay_var.set(f"{new_delay:.1f}")
                
            self.app_ref.log_message(f"已自动增加基础延迟至{new_delay:.1f}秒以避免速率限制", "info")
            return True
        return False

    def _handle_translation_error(self, error_msg):
        """处理翻译过程中的异常，确保UI状态恢复"""
        self.log_message(f"发生错误: {error_msg}", "error")
        # 恢复UI状态
        self._safe_button_state(self.translate_button, tk.NORMAL)
        self._safe_button_state(self.stop_button, tk.DISABLED)
        # 更新状态栏
        self._update_ui(self.status_label.config, text=f"错误: {error_msg[:50]}...")
        # 设置停止标志
        self.stop_translation_flag.set()
        # 确保并行翻译器工作线程停止
        if hasattr(self, 'parallel_translator'):
            self.parallel_translator.stop_workers()

# --- Parallel Translator ---
class ParallelTranslator:
    """并行翻译器，管理多个API密钥的并行调用"""
    def __init__(self, app_ref, config_manager):
        self.app_ref = app_ref
        self.config_manager = config_manager
        self.api_key_manager = APIKeyManager(config_manager)
        self.translators = {}  # 翻译器字典，键为translator_id
        self.translation_queue = queue.Queue()  # 待翻译文本队列
        self.result_queue = queue.Queue()  # 翻译结果队列
        self.pending_reviews = {}  # 待评审的翻译，键为entry_id
        self.workers = []  # 工作线程列表
        self.stop_flag = threading.Event()  # 停止标志
        self.lock = threading.RLock()  # 全局锁
        self.init_translators()
        
    def init_translators(self):
        """初始化翻译器"""
        with self.lock:
            # 清空现有翻译器
            self.translators.clear()
            self.app_ref.log_message("并行翻译器：正在清理旧的翻译器实例...", "debug")

            # 获取并行工作线程数，也即需要的翻译器实例数
            # 注意：这里不再基于API密钥数量创建翻译器，而是基于工作线程数
            # 每个工作线程将按需使用API密钥管理器获取密钥
            num_workers = self.config_manager.get_setting("max_concurrent_tasks", 3) # 使用max_concurrent_tasks作为工作线程数

            for i in range(num_workers):
                translator_id = f"parallel_translator-{i+1}"
                # api_key_provider_func 不再需要，因为密钥将通过 translate 方法传递
                self.translators[translator_id] = GeminiTranslator(
                    self.app_ref,
                    api_key_provider_func=None, # 设置为 None 或移除
                    translator_id=translator_id
                )
                self.app_ref.log_message(f"并行翻译器：已初始化翻译器 {translator_id}", "info")
    
    def start_workers(self, num_workers=None):
        """启动工作线程"""
        if num_workers is None:
            num_workers = self.config_manager.get_setting("parallel_workers", 3)
        
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
    
    def stop_workers(self):
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
    
    def _worker_thread(self, worker_id):
        """工作线程函数"""
        self.app_ref.log_message(f"工作线程 {worker_id} 开始运行", "debug")
        
        # 为每个工作线程获取一个独立的翻译器实例
        translator_instance_id = f"parallel_translator-{worker_id+1}"
        translator = self.translators.get(translator_instance_id)
        if not translator:
            self.app_ref.log_message(f"工作线程 {worker_id}: 严重错误 - 未找到翻译器实例 {translator_instance_id}。线程将退出。", "error")
            return

        while not self.stop_flag.is_set():
            try:
                task = None # Initialize task to None for error handling in except block
                try:
                    task = self.translation_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                api_key = self.api_key_manager.get_next_key()
                if not api_key:
                    self.app_ref.log_message(f"工作线程 {worker_id}: 无可用API密钥，将任务放回队列并等待。", "error")
                    self.translation_queue.put(task)
                    time.sleep(5.0) 
                    continue
                
                self.app_ref.log_message(f"工作线程 {worker_id} 使用API密钥 ...{api_key[-4:]} 翻译: {task.get('text', '')[:30]}...", "debug")
                
                base_delay = float(self.config_manager.get_setting("api_call_delay", 3.0))
                self.app_ref.log_message(f"工作线程 {worker_id}: 应用基础延迟 {base_delay:.1f} 秒 (来自配置)", "debug")
                time.sleep(base_delay)

                translated_text, token_count, error_type = translator.translate(
                    task["text"],
                    task["source_lang"],
                    task["target_lang"],
                    task["game_mod_style"],
                    task["model_name"],
                    api_key_to_use=api_key
                )
                
                if error_type is None and translated_text is not None:
                    self.api_key_manager.mark_key_success(api_key, token_count if isinstance(token_count, int) else 0)
                else:
                    actual_error_type = error_type if error_type else "translation_failed_or_unchanged"
                    self.api_key_manager.mark_key_failure(api_key, actual_error_type)
                
                self.result_queue.put({
                    "entry_id": task["entry_id"],
                    "original_text": task["text"],
                    "translated_text": translated_text,
                    "token_count": token_count,
                    "api_error_type": error_type, # Pass along the error type
                    "original_line_content": task.get("original_line_content"), # Pass through original_line_content
                    "source_lang": task["source_lang"] # Pass through source_lang for context if needed by main app
                })
                
            except Exception as e:
                self.app_ref.log_message(f"工作线程 {worker_id} 发生异常: {e}", "error")
                import traceback
                self.app_ref.log_message(f"异常详情: {traceback.format_exc()}", "debug")
                
                if task: # Check if task was retrieved before exception
                    self.translation_queue.put(task) # Put task back if exception occurred after getting it
                
                if 'api_key' in locals() and api_key: # Check if api_key was assigned
                    error_type_for_key_manager = str(e) # Generic error type
                    self.api_key_manager.mark_key_failure(api_key, error_type_for_key_manager)
                
                time.sleep(2.0)
        
        self.app_ref.log_message(f"工作线程 {worker_id} 结束运行", "debug")

    def add_translation_task(self, entry_id, text, source_lang, target_lang, game_mod_style, model_name, original_line_content=None):
        """添加翻译任务到队列，包含 original_line_content"""
        task_data = {
            "entry_id": entry_id,
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "game_mod_style": game_mod_style,
            "model_name": model_name,
            "original_line_content": original_line_content # Include it here
        }
        self.translation_queue.put(task_data)

    def get_translation_result(self, timeout=None):
        """获取翻译结果，如果队列为空则阻塞"""
        try:
            return self.result_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_queue_size(self):
        """获取待翻译队列大小"""
        return self.translation_queue.qsize()

    def is_queue_empty(self):
        """检查待翻译队列是否为空"""
        return self.translation_queue.empty()

    def is_processing_complete(self):
        """检查是否输入队列和结果队列都为空。"""
        with self.lock:
            # True if no tasks waiting to be picked up by workers, and no results waiting to be picked by main app.
            return self.translation_queue.empty() and self.result_queue.empty()

    def add_pending_review(self, entry_id, review_data):
        """添加待评审的翻译"""
        with self.lock:
            self.pending_reviews[entry_id] = review_data

    def get_pending_review(self, entry_id):
        """获取待评审的翻译"""
        with self.lock:
            return self.pending_reviews.get(entry_id)

    def remove_pending_review(self, entry_id):
        """移除待评审的翻译"""
        with self.lock:
            if entry_id in self.pending_reviews:
                del self.pending_reviews[entry_id]

class ReviewDialog(tk.Toplevel):
    def __init__(self, parent_app_instance, root_window, original_text, ai_translation, original_placeholders, translated_placeholders, key_name, completion_callback=None): # Modified parameters
        super().__init__(root_window)
        
        # 在完全构建UI之前隐藏窗口
        self.withdraw()
        
        # 设置窗口属性
        self.transient(root_window)
        self.grab_set()
        self.app = parent_app_instance 
        self.original_text_arg = original_text 
        self.result = None 
        # self.result_queue = result_queue  # 存储结果队列的引用 - REMOVED
        self.key_name_arg = key_name # Store key_name for callback
        self.completion_callback = completion_callback # Store callback

        # 调整窗口属性
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)  # 点击关闭按钮调用取消方法
        self.app.log_message(f"ReviewDialog initializing for key: {key_name}", "debug")
        self.title(f"评审翻译: {key_name}")  # Simplified title
        
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
          # 创建清晰分明的卡片式布局
        main_container = ttk.Frame(self, padding=15)
        main_container.pack(expand=True, fill=tk.BOTH)
        
        # 允许窗口大小调整
        self.resizable(True, True)
        self.minsize(700, 600)  # 设置最小窗口大小
        
        # 顶部标题区域
        header_frame = ttk.Frame(main_container)
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
        
        # 原文卡片
        original_card = ttk.Frame(main_container, relief="solid", borderwidth=1)
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
        
        # AI翻译卡片
        ai_card = ttk.Frame(main_container, relief="solid", borderwidth=1)
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
        
        # 编辑区卡片
        edit_card = ttk.Frame(main_container, relief="solid", borderwidth=1)
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
        
        # 占位符分析区
        ph_card = ttk.Frame(main_container, relief="solid", borderwidth=1)
        ph_card.pack(fill=X, pady=(0, 15), padx=2)
        
        # 设置标题文本和颜色
        ph_title = "📊 占位符分析"
        ph_color = "#333333"
          # 更精确地检查占位符问题，并使用更突出的标题提醒用户
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
        orig_ph_frame = ttk.Frame(ph_columns)
        orig_ph_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        ttk.Label(
            orig_ph_frame, 
            text="原文占位符:",
            font=('Default', 9, 'bold')
        ).pack(anchor=W, pady=(0, 3))
        
        orig_ph_scrolled = scrolledtext.ScrolledText(
            orig_ph_frame, 
            height=4, 
            wrap=tk.WORD, 
            relief="flat", 
            borderwidth=1,
            font=('Consolas', 9)
        )
        orig_ph_scrolled.insert(tk.END, "\n".join(sorted(list(original_placeholders))) if original_placeholders else "无")
        orig_ph_scrolled.configure(state='disabled')
        orig_ph_scrolled.pack(fill=X)
        
        # AI翻译占位符区域
        ai_ph_frame = ttk.Frame(ph_columns)
        ai_ph_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        ttk.Label(
            ai_ph_frame, 
            text="AI翻译占位符:",
            font=('Default', 9, 'bold')
        ).pack(anchor=W, pady=(0, 3))
        
        ai_ph_scrolled = scrolledtext.ScrolledText(
            ai_ph_frame, 
            height=4, 
            wrap=tk.WORD, 
            relief="flat", 
            borderwidth=1,
            font=('Consolas', 9)
        )
        ai_ph_scrolled.insert(tk.END, "\n".join(sorted(list(translated_placeholders))) if translated_placeholders else "无")
        ai_ph_scrolled.configure(state='disabled')
        ai_ph_scrolled.pack(fill=X)
        
        # 占位符问题详细信息
        if missing_in_ai or added_in_ai:
            diff_frame = ttk.Frame(ph_content)
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
        
        # 底部按钮区域
        button_frame = ttk.Frame(main_container)
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
        
        self.cancel_button = ttkb.Button(
            button_panel, 
            text="取消", 
            command=self._on_cancel, 
            bootstyle="secondary",
            width=10,
            cursor="hand2"
        )
        self.cancel_button.pack(side=LEFT, padx=5)
        
        self.use_original_button = ttkb.Button(
            button_panel, 
            text="使用原文", 
            command=self._on_use_original, 
            bootstyle="warning",
            width=10,
            cursor="hand2"
        )
        self.use_original_button.pack(side=LEFT, padx=5)
        
        self.skip_button = ttkb.Button(
            button_panel, 
            text="使用AI翻译", 
            command=self._on_skip_with_ai_text, 
            bootstyle="info",
            width=12,
            cursor="hand2"
        )
        self.skip_button.pack(side=LEFT, padx=5)
        
        self.confirm_button = ttkb.Button(
            button_panel, 
            text="确认并继续", 
            command=self._on_confirm, 
            bootstyle="success",
            width=12,
            cursor="hand2",
            default="active"  # 设为默认按钮，可通过回车激活
        )
        self.confirm_button.pack(side=LEFT, padx=5)
        
        # 绑定键盘快捷键
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.bind("<Return>", lambda e: self._on_confirm())
        
        # 添加按钮工具提示
        try:
            from ttkbootstrap.tooltip import ToolTip
            ToolTip(self.confirm_button, text="保存您的编辑并继续下一个翻译", delay=500)
            ToolTip(self.skip_button, text="直接使用AI翻译结果", delay=500)
            ToolTip(self.use_original_button, text="保留原文不翻译", delay=500)
            ToolTip(self.cancel_button, text="取消评审", delay=500)
        except (ImportError, AttributeError):
            pass
          # 在绑定键盘快捷键和添加工具提示后，设置窗口大小
        
        # 获取屏幕尺寸
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 设置更合理的初始大小（根据屏幕大小调整）
        # 使用屏幕尺寸的百分比而不是固定值，确保在不同分辨率下看起来合适
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
        current_geometry = self.geometry().split('+')
        window_width = int(current_geometry[0].split('x')[0])
        window_height = int(current_geometry[0].split('x')[1])
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))
        
        # 应用最终位置
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 调用ensure_on_screen方法确保窗口位置和大小适合屏幕
        self.ensure_on_screen()
        
        # 在显示窗口之前再次更新以确保所有计算完成
        self.update_idletasks()
          # 最后显示窗口
        self.deiconify()
        self.lift()
        self.focus_force()
        self.edited_text_widget.focus_set()
        self.app.log_message(f"ReviewDialog for key '{key_name}' displayed.", "debug")
        # 不在此处使用wait_window，改由调用者处理结果

    def ensure_on_screen(self):
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
        
    def _on_confirm(self):
        self.result = self.edited_text_widget.get("1.0", tk.END).strip()
        self.app.log_message(f"ReviewDialog: Confirmed text for key '{self.key_name_arg}'", "debug") # Use stored key_name_arg
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result)
        # if self.result_queue: # REMOVED
        #     self.result_queue.put(self.result) # REMOVED
        self.destroy()
        
    def _on_use_original(self):
        self.result = self.original_text_arg 
        self.app.log_message(f"ReviewDialog: Using original text for key '{self.key_name_arg}'", "debug") # Use stored key_name_arg
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result)
        # if self.result_queue: # REMOVED
        #     self.result_queue.put(self.result) # REMOVED
        self.destroy()
        
    def _on_skip_with_ai_text(self):
        self.result = self.edited_text_widget.get("1.0", tk.END).strip()
        self.app.log_message(f"ReviewDialog: Using AI text (current edit box) for key '{self.key_name_arg}'", "debug") # Use stored key_name_arg
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result)
        # if self.result_queue: # REMOVED
        #     self.result_queue.put(self.result) # REMOVED
        self.destroy()
        
    def _on_cancel(self):
        self.result = None 
        self.app.log_message(f"ReviewDialog: Cancelled for key '{self.key_name_arg}'", "debug") # Use stored key_name_arg
        if self.completion_callback:
            self.completion_callback(self.key_name_arg, self.result) # Notify callback even on cancel
        # if self.result_queue: # REMOVED
        #     self.result_queue.put(self.result) # REMOVED
        self.destroy()

class DebouncedButton:
    """按钮防抖装饰器类"""
    def __init__(self, debounce_time=1000):
        self.debounce_time = debounce_time  # 毫秒
        self.last_call_time = 0
        
    def __call__(self, func):
        def wrapped(instance, *args, **kwargs):
            current_time = time.time() * 1000  # 转换为毫秒
            if current_time - self.last_call_time > self.debounce_time:
                self.last_call_time = current_time
                return func(instance, *args, **kwargs)
            else:
                instance.log_message(f"操作过于频繁，请稍后再试 ({(self.debounce_time/1000):.1f}秒)", "warn")
                return None
        return wrapped

# --- GUI Application ---
class ModTranslatorApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Paradox Mod Translator（由gemini强力驱动）")
        self.root.geometry("1200x800")  # Slightly larger initial window
        
        # Apply modern UI style
        if hasattr(ttkb, "Style"):
            self.style = ttkb.Style()
            self.style.configure("TLabelframe.Label", font=("Default", 10, "bold"))
            self.style.configure("Custom.TButton", font=("Default", 10))
            # Custom progress bar style
            self.style.configure("success.Horizontal.TProgressbar", 
                                 background='#28a745', troughcolor='#f0f0f0')
                
        self.config_manager = ConfigManager(CONFIG_FILE)
        # Initialize UI variables
        self.localization_root_path = tk.StringVar(value=self.config_manager.get_setting("localization_root_path"))
        self.source_language_code = tk.StringVar(value=self.config_manager.get_setting("source_language"))
        self.target_language_code = tk.StringVar(value=self.config_manager.get_setting("target_language"))
        self.game_mod_style_prompt = tk.StringVar(value=self.config_manager.get_setting("game_mod_style"))
        self.selected_model_var = tk.StringVar(value=self.config_manager.get_setting("selected_model"))
        self.api_key_var = tk.StringVar(value=self.config_manager.get_setting("api_key")) # This is the single API key from old config
        self.api_call_delay_var = tk.StringVar(value=f"{self.config_manager.get_setting('api_call_delay'):.1f}")

        # self.translation_queue = queue.Queue() # REMOVED - Will use ParallelTranslator's queues
        self.stop_translation_flag = threading.Event()
        self.yml_parser = YMLParser()
        
        # Parallel translator and state
        self.parallel_translator = ParallelTranslator(self, self.config_manager)
        self.file_translation_progress = {} # Stores {filepath_rel: {"total_entries": N, "processed_entries": 0, "translated_entries_data": [], "has_errors": False, "original_lang_code": "...", "source_file_entries": []}}
        self.overall_total_keys = 0
        self.overall_processed_keys = 0
        self.items_to_review_later = [] # ADDED: Stores items flagged for deferred review
        self.current_reviewing_item_details = None # ADDED: Holds details of the item currently being reviewed
        self.total_items_for_review_phase = 0    # ADDED: For review phase progress
        self.processed_items_in_review_phase = 0 # ADDED: For review phase progress

        # Setup UI
        self._setup_ui()
        
        # Populate language dropdowns and load models
        self._populate_language_dropdowns()
        self._load_gemini_models()
        
        # Set API delay related attributes
        self.last_delay_change_time = time.time() - 3600  # Initialized to 1 hour ago, to ensure first change triggers prompt
        
        # In brief delay display API call delay prompt after application start
        # Note: Only prompt if current delay differs from default
        api_delay = self.config_manager.get_setting("api_call_delay", 3)
        config_defaults = self.config_manager.defaults
        if api_delay != config_defaults.get("api_call_delay", 3):
            self.root.after(2000, lambda: self.log_message(
                f"API调用延迟已自定义设置为 {api_delay} 秒。您可以在设置中的'⏱️ API调用延迟'选项进行调整。", "info"
            ))
        else:
            self.root.after(2000, lambda: self.log_message(
                "新功能提示: 可在设置中调整'⏱️ API调用延迟'选项，以避免API速率限制错误。", "info"
            ))

        # Bind variable change events
        self.localization_root_path.trace_add("write", lambda *args: self.config_manager.set_setting("localization_root_path", self.localization_root_path.get()))
        self.source_language_code.trace_add("write", lambda *args: self._save_language_setting("source_language", self.source_language_code.get()))
        self.target_language_code.trace_add("write", lambda *args: self.config_manager.set_setting("target_language", self.target_language_code.get()))
        self.game_mod_style_prompt.trace_add("write", lambda *args: self.config_manager.set_setting("game_mod_style", self.game_mod_style_prompt.get()))
        self.selected_model_var.trace_add("write", lambda *args: self.config_manager.set_setting("selected_model", self.selected_model_var.get()))
        self.api_key_var.trace_add("write", lambda *args: self._handle_api_key_change())

        # Bind closing event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Setup theme switching
        self._setup_theme_switching()

    def _setup_ui(self):
        """设置主界面UI布局和组件"""
        # Create main frame, using modern padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(expand=True, fill=BOTH)
        
        # Create side-by-side layout, approximately 5:7
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=BOTH, expand=True)
        
        # Left panel (settings and file list)
        left_panel = ttk.Frame(paned_window)
        paned_window.add(left_panel, weight=5)
        
        # Right panel (controls and logs)
        right_panel = ttk.Frame(paned_window)
        paned_window.add(right_panel, weight=7)
        
        # ===== Status bar =====
        self.status_bar = ttk.Frame(self.root, relief="sunken", padding=(10, 2))
        self.status_bar.pack(side=BOTTOM, fill=X)
        
        self.status_label = ttk.Label(self.status_bar, text="就绪", anchor=tk.W)
        self.status_label.pack(side=LEFT)
        
        self.version_label = ttk.Label(self.status_bar, text="v1.0", anchor=tk.E)
        self.version_label.pack(side=RIGHT)
        
        # ===== Toolbar =====
        toolbar = ttk.Frame(self.root, padding=2)
        toolbar.pack(side=TOP, fill=X)
        
        # Theme switch button
        self.theme_button = ttkb.Button(
            toolbar, 
            text="🌓 切换主题",
            bootstyle="outline",
            command=self._toggle_theme,
            width=12
        )
        self.theme_button.pack(side=RIGHT, padx=5, pady=2)
        
        # === Left panel content ===
        # Settings area (top left)
        settings_frame = ttk.Labelframe(
            left_panel, 
            text=" ⚙️ 设置 (Settings) ", 
            padding="12"
        )
        settings_frame.pack(fill=X, pady=(0, 10), ipady=5)
        
        # Localization root directory line
        loc_frame = ttk.Frame(settings_frame)
        loc_frame.pack(fill=X, pady=(5, 10))
        
        ttk.Label(
            loc_frame, 
            text="📁 本地化根目录:",
            width=16,
            font=("Default", 9)
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Entry(
            loc_frame, 
            textvariable=self.localization_root_path
        ).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        browse_btn = ttkb.Button(
            loc_frame, 
            text="浏览...", 
            width=8, 
            command=self._select_localization_folder, 
            bootstyle="info-outline", 
            cursor="hand2"
        )
        browse_btn.pack(side=LEFT)
        
        # Language selection frame
        lang_frame = ttk.Frame(settings_frame)
        lang_frame.pack(fill=X, pady=(0, 10))
        
        lang_frame.columnconfigure(0, weight=0)  # Label column
        lang_frame.columnconfigure(1, weight=1)  # Source language combo box column
        lang_frame.columnconfigure(2, weight=0)  # Target language label column
        lang_frame.columnconfigure(3, weight=1)  # Target language combo box column
        
        ttk.Label(
            lang_frame, 
            text="🔤 源语言:",
            font=("Default", 9)
        ).grid(row=0, column=0, padx=(0, 5), sticky=W)
        
        self.source_lang_combo = ttk.Combobox(
            lang_frame, 
            textvariable=self.source_language_code, 
            state="readonly", 
            width=15
        )
        self.source_lang_combo.grid(row=0, column=1, sticky=W+E, padx=(0, 15))
        self.source_lang_combo.bind("<<ComboboxSelected>>", self._source_language_changed_ui)
        
        ttk.Label(
            lang_frame, 
            text="🈁 目标语言:",
            font=("Default", 9)
        ).grid(row=0, column=2, padx=(0, 5), sticky=W)
        
        self.target_lang_combo = ttk.Combobox(
            lang_frame, 
            textvariable=self.target_language_code, 
            width=15
        )
        self.target_lang_combo['values'] = ["simp_chinese", "english", "french", "german", "spanish", 
                                           "russian", "japanese", "korean", "polish"]
        self.target_lang_combo.grid(row=0, column=3, sticky=W+E)
        
        # Style prompt line
        style_frame = ttk.Frame(settings_frame)
        style_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(
            style_frame, 
            text="🎮 游戏/Mod风格:",
            font=("Default", 9)
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Entry(
            style_frame, 
            textvariable=self.game_mod_style_prompt
        ).pack(side=LEFT, fill=X, expand=True)
        
        # Model selection and API area
        api_model_frame = ttk.Frame(settings_frame)
        api_model_frame.pack(fill=X, pady=(0, 5))
        api_model_frame.columnconfigure(1, weight=1)
        
        # Model selection line
        ttk.Label(
            api_model_frame, 
            text="🤖 Gemini 模型:",
            font=("Default", 9)
        ).grid(row=0, column=0, padx=(0, 5), pady=(0, 10), sticky=W)
        
        self.model_combo = ttk.Combobox(
            api_model_frame, 
            textvariable=self.selected_model_var, 
            state="readonly"
        )
        self.model_combo.grid(row=0, column=1, columnspan=2, pady=(0, 10), sticky=W+E)
        
        # API key line
        ttk.Label(
            api_model_frame, 
            text="🔑 API 密钥:",
            font=("Default", 9)
        ).grid(row=1, column=0, padx=(0, 5), sticky=W)
        
        self.api_key_entry = ttk.Entry(
            api_model_frame, 
            textvariable=self.api_key_var, 
            show="•"
        )
        self.api_key_entry.grid(row=1, column=1, sticky=W+E, padx=(0, 5))
        apply_key_btn = ttkb.Button(
            api_model_frame, 
            text="应用密钥", 
            width=10, 
            command=self._apply_key_and_reload_models, 
            bootstyle="info-outline", 
            cursor="hand2"
        )
        apply_key_btn.grid(row=1, column=2, sticky=E)
        
        # API call delay setting line
        ttk.Label(
            api_model_frame, 
            text="⏱️ API调用延迟(秒):",
            font=("Default", 9)
        ).grid(row=2, column=0, padx=(0, 5), pady=(10, 0), sticky=W)
        
        delay_frame = ttk.Frame(api_model_frame)
        delay_frame.grid(row=2, column=1, sticky=W, pady=(10, 0))
        
        delay_spinbox = ttk.Spinbox(
            delay_frame,
            from_=1,
            to=10,
            increment=1,
            width=5,
            textvariable=self.api_call_delay_var
        )
        delay_spinbox.pack(side=tk.LEFT)
        # Real-time dynamic delay display
        self.dynamic_delay_var = tk.StringVar(value="0.0")
        ttk.Label(delay_frame, text=" 实时动态延迟:").pack(side=tk.LEFT)
        dynamic_delay_label = ttk.Label(delay_frame, textvariable=self.dynamic_delay_var)
        dynamic_delay_label.pack(side=tk.LEFT)
        
        # Add tooltips for dynamic delay label
        try:
            from ttkbootstrap.tooltip import ToolTip
            ToolTip(dynamic_delay_label, text="基于TPM、RPM和平均token使用量动态计算的实际API调用延迟", delay=500)
        except (ImportError, AttributeError):
            pass
        
        # Add information
        ttk.Label(
            delay_frame, 
            text=" (提高数值可避免频率限制错误)",
            font=("Default", 8),
            foreground="#666666"
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Listen for API call delay change
        self.api_call_delay_var.trace_add("write", lambda *args: self._update_api_delay_setting())
        
        # File list area (bottom left)
        files_frame = ttk.Labelframe(
            left_panel, 
            text=" 📋 待翻译文件 ", 
            padding="12"
        )
        files_frame.pack(fill=BOTH, expand=True)
        
        # File operations toolbar
        files_toolbar = ttk.Frame(files_frame)
        files_toolbar.pack(fill=X, pady=(0, 8))
        
        refresh_btn = ttkb.Button(
            files_toolbar,
            text="🔄 刷新文件列表",
            command=self._load_files_for_translation,
            bootstyle="secondary-outline",
            cursor="hand2"
        )
        refresh_btn.pack(side=LEFT)
        
        # Statistics label
        self.files_count_label = ttk.Label(
            files_toolbar,
            text="共 0 个文件",
            font=("Default", 9)
        )
        self.files_count_label.pack(side=RIGHT)
        
        # File tree view and scrollbar
        tree_frame = ttk.Frame(files_frame)
        tree_frame.pack(fill=BOTH, expand=True)
        
        # File tree view
        self.files_tree = ttk.Treeview(
            tree_frame, 
            columns=("filepath", "status"), 
            show="headings", 
            height=10,
            selectmode="browse"
        )
        self.files_tree.heading("filepath", text="📄 文件路径")
        self.files_tree.heading("status", text="🔄 状态")
        self.files_tree.column("filepath", width=350)
        self.files_tree.column("status", width=120, anchor=CENTER)
        
        # Set alternating row colors
        self.files_tree.tag_configure('oddrow', background='#f9f9f9')
        self.files_tree.tag_configure('evenrow', background='#ffffff')
        
        # Status label colors
        self.files_tree.tag_configure('pending', foreground='#666666')
        self.files_tree.tag_configure('processing', foreground='#0066cc')
        self.files_tree.tag_configure('done', foreground='#009900')
        self.files_tree.tag_configure('error', foreground='#cc0000')
        
        # Scrollbars
        tree_scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.files_tree.yview)
        tree_scrollbar_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=tree_scrollbar_y.set, xscrollcommand=tree_scrollbar_x.set)
        
        # Scrollbar layout
        tree_scrollbar_y.pack(side=RIGHT, fill=Y)
        tree_scrollbar_x.pack(side=BOTTOM, fill=X)
        self.files_tree.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Right-click menu
        self.tree_context_menu = tk.Menu(self.files_tree, tearoff=0)
        self.tree_context_menu.add_command(label="查看文件内容", command=self._view_file_content)
        self.tree_context_menu.add_command(label="打开文件位置", command=self._open_file_location)
        self.files_tree.bind("<Button-3>", self._show_tree_context_menu)
        
        # === Right panel content ===
        # Controls area (top right)
        controls_frame = ttk.Labelframe(
            right_panel, 
            text=" ⚡ 操作控制 ", 
            padding="12"
        )
        controls_frame.pack(fill=X, pady=(0, 10))
        
        # Card layout for controls
        control_card = ttk.Frame(controls_frame, relief="solid", borderwidth=1)
        control_card.pack(fill=X, pady=5, padx=5)
        
        # Translation buttons area
        buttons_frame = ttk.Frame(control_card, padding=10)
        buttons_frame.pack(fill=X)
        
        # Start button
        self.translate_button = ttkb.Button(
            buttons_frame, 
            text="▶️ 开始翻译", 
            bootstyle="success",
            command=self._start_translation_process,
            width=15,
            cursor="hand2"
        )
        self.translate_button.pack(side=LEFT, padx=(0, 10))
        
        # Stop button        
        self.stop_button = ttkb.Button(
            buttons_frame, 
            text="⏹️ 停止翻译", 
            bootstyle="danger",
            command=self._stop_translation_process,
            width=15,
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.stop_button.pack(side=LEFT)
        
        # Translation options card
        options_card = ttk.Frame(controls_frame, relief="solid", borderwidth=1)
        options_card.pack(fill=X, pady=5, padx=5)
        
        options_header = ttk.Frame(options_card, padding=(10, 5))
        options_header.pack(fill=X)
        
        ttk.Label(
            options_header, 
            text="📊 翻译进度", 
            font=("Default", 10, "bold")
        ).pack(side=LEFT)
        
        # Progress display card
        progress_frame = ttk.Frame(options_card, padding=10)
        progress_frame.pack(fill=X)
        
        progress_container = ttk.Frame(progress_frame)
        progress_container.pack(fill=X)
        
        self.progress_bar = ttk.Progressbar(
            progress_container, 
            orient=HORIZONTAL, 
            mode='determinate',
            style="success.Horizontal.TProgressbar",
            length=200
        )
        self.progress_bar.pack(fill=X, side=LEFT, expand=True)
        
        self.progress_percent = ttk.Label(
            progress_container,
            text="0%",
            width=5
        )
        self.progress_percent.pack(side=LEFT, padx=(5, 0))
        
        # Advanced options (collapsible)
        advanced_frame = ttk.Labelframe(
            controls_frame,
            text=" 🛠️ 高级选项 ",
            padding=10
        )
        advanced_frame.pack(fill=X, pady=5, padx=5)
          # Batch processing options
        batch_frame = ttk.Frame(advanced_frame)
        batch_frame.pack(fill=X, pady=(0, 5))
        self.auto_approve_var = tk.BooleanVar(value=True)  # Default to True
        auto_approve_cb = ttk.Checkbutton(
            batch_frame,
            text="自动接受无占位符问题的翻译（✓勾选：仅审核有占位符问题的翻译；□不勾选：手动审核所有翻译）",
            variable=self.auto_approve_var
        )
        auto_approve_cb.pack(side=LEFT)
        
        # Log area (bottom right)
        log_frame = ttk.Labelframe(
            right_panel, 
            text=" 📝 日志 ", 
            padding="12"
        )
        log_frame.pack(fill=BOTH, expand=True)
        
        # Log toolbar
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=X, pady=(0, 5))
        
        clear_log_btn = ttkb.Button(
            log_toolbar,
            text="🧹 清除日志",
            command=self._clear_log,
            bootstyle="secondary-outline",
            cursor="hand2"
        )
        clear_log_btn.pack(side=LEFT)
        
        # Log level selection
        ttk.Label(log_toolbar, text="日志级别:").pack(side=RIGHT, padx=(0, 5))
        
        self.log_level_var = tk.StringVar(value="info")
        log_level_combo = ttk.Combobox(
            log_toolbar,
            textvariable=self.log_level_var,
            values=["debug", "info", "warn", "error"],
            state="readonly",
            width=8
        )
        log_level_combo.pack(side=RIGHT)
        
        # Log text area
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_text_frame, 
            wrap=tk.WORD, 
            state='disabled',
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=BOTH, expand=True)
        
        # Log color tags
        self.log_text.tag_config("info", foreground="#0066cc")
        self.log_text.tag_config("error", foreground="#cc0000")
        self.log_text.tag_config("warn", foreground="#cc6600")
        self.log_text.tag_config("success", foreground="#009900")
        self.log_text.tag_config("debug", foreground="#666666")
        
        # Add tooltips
        self._add_tooltips()
        
    def _setup_theme_switching(self):
        """设置主题切换功能"""
        self.current_theme = "light"
        
    def _toggle_theme(self):
        """切换深色/浅色主题"""
        try:
            if self.current_theme == "light":
                self.style.theme_use("darkly")
                self.current_theme = "dark"
                self.theme_button.config(text="🌞 浅色模式")
            else:
                self.style.theme_use("cosmo")
                self.current_theme = "light"
                self.theme_button.config(text="🌙 深色模式")
            
            self.log_message(f"已切换到{self.current_theme}主题", "info")
        except Exception as e:
            self.log_message(f"切换主题失败: {e}", "error")
            
    def _clear_log(self):
        """清除日志内容"""
        self.log_text.configure(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state='disabled')
        self.log_message("日志已清除", "info")
    
    def _add_tooltips(self):
        """为关键控件添加工具提示"""
        try:
            from ttkbootstrap.tooltip import ToolTip
            
            ToolTip(self.translate_button, text="开始对所有队列中的文件进行翻译", delay=500)
            ToolTip(self.stop_button, text="停止当前翻译进程", delay=500)
            ToolTip(self.api_key_entry, text="输入您的Gemini API密钥", delay=500)
            ToolTip(self.source_lang_combo, text="选择源语言文件夹", delay=500)
            ToolTip(self.target_lang_combo, text="选择要翻译成的目标语言", delay=500)
            ToolTip(self.model_combo, text="选择要使用的Gemini AI模型", delay=500)
            ToolTip(self.theme_button, text="在深色和浅色模式之间切换", delay=500)
            ToolTip(self.progress_bar, text="当前翻译任务的进度", delay=500)
            
        except (ImportError, AttributeError):
            # 如果ttkbootstrap.tooltip不可用，跳过工具提示
            self.log_message("工具提示功能不可用，需要完整的ttkbootstrap库", "debug")
    
    def _view_file_content(self):
        """查看选中文件的内容"""
        selected = self.files_tree.selection()
        if not selected:
            return
            
        item_values = self.files_tree.item(selected[0], 'values')
        if not item_values:
            return
            
        relative_path = item_values[0]
        full_path = os.path.join(
            self.localization_root_path.get(),
            self.source_language_code.get(),
            relative_path
        )
        
        try:
            with open(full_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            # 创建文件查看对话框
            viewer = tk.Toplevel(self.root)
            viewer.title(f"文件内容: {relative_path}")
            viewer.geometry("800x600")
            
            text_area = scrolledtext.ScrolledText(viewer, wrap=tk.WORD)
            text_area.pack(fill=BOTH, expand=True, padx=10, pady=10)
            text_area.insert(tk.END, content)
            text_area.configure(state='disabled')
            
        except Exception as e:
            self.log_message(f"无法查看文件内容: {e}", "error")
            
    def _open_file_location(self):
        """在文件管理器中打开选中文件的位置"""
        selected = self.files_tree.selection()
        if not selected:
            return
            
        item_values = self.files_tree.item(selected[0], 'values')
        if not item_values:
            return
            
        relative_path = item_values[0]
        full_path = os.path.join(
            self.localization_root_path.get(),
            self.source_language_code.get(),
            relative_path
        )
        
        directory = os.path.dirname(full_path)
        
        try:
            # 根据操作系统打开文件位置
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                os.startfile(directory)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", directory])
            else:  # Linux
                subprocess.call(["xdg-open", directory])
                
        except Exception as e:
            self.log_message(f"无法打开文件位置: {e}", "error")
            
    def _show_tree_context_menu(self, event):
        """显示文件树的右键菜单"""
        item = self.files_tree.identify_row(event.y)
        if not item:
            return
            
        # 选中点击的项
        self.files_tree.selection_set(item)
        self.tree_context_menu.post(event.x_root, event.y_root)
        
    def _update_progress(self, value):
        """更新进度条和百分比标签"""
        self.progress_bar['value'] = value
        if hasattr(self, 'progress_percent'):
            self.progress_percent.config(text=f"{int(value)}%")

    # 保留原始代码中的功能方法
    def _select_localization_folder(self):
        path = filedialog.askdirectory(title="选择 Mod 本地化根目录")
        if path:
            self.localization_root_path.set(path)  # This will trigger save via trace
            self.log_message(f"本地化根目录已选择: {path}", "info")
            self._populate_language_dropdowns()

    def _source_language_changed_ui(self, event=None):
        """Called when the source language selection changes in UI."""
        # The trace on source_language_code already handles saving and reloading files.
        # This is mostly for logging or any additional UI-specific actions.
        self.log_message(f"源语言在UI中更改为: {self.source_language_code.get()}", "debug")
        self._load_files_for_translation()  # Ensure files are reloaded based on UI change

    def _save_language_setting(self, key, value):
        """Saves language setting and reloads files if source language changed."""
        self.config_manager.set_setting(key, value)
        if key == "source_language":
            self._load_files_for_translation()

    def _on_closing(self):
        self.config_manager.save_config()
        self.log_message("Configuration saved. Exiting application.", "info")
        self.stop_translation_flag.set() # Signal any running processes to stop
        if self.parallel_translator:
            self.parallel_translator.stop_workers() # Attempt to clean up workers
        self.root.destroy()

    def _handle_api_key_change(self):
        new_key = self.api_key_var.get()
        self.config_manager.set_setting("api_key", new_key)
        self.log_message("API Key changed in settings. Re-configuring Gemini.", "info")
        if self.translator._configure_gemini():  # Attempt to reconfigure with new key
            self._load_gemini_models()  # Reload models if API key is valid now

    def _apply_key_and_reload_models(self):
        """Explicitly applies API key and reloads models."""
        self.log_message("Attempting to apply API key and reload models...", "info")
        self._handle_api_key_change()  # This will reconfigure and reload models

    def _load_gemini_models(self):
        """Loads available Gemini models into the combobox."""
        if not GEMINI_AVAILABLE:
            self.log_message("Gemini library not available. Cannot fetch models.", "error")
            self.model_combo['values'] = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"]  # Fallback defaults
            return

        api_key = self.api_key_var.get()
        if not api_key or api_key == DEFAULT_API_KEY_PLACEHOLDER:
            self.log_message("API Key not set. Using default model list. Please set API Key to fetch live models.", "warn")
            self.model_combo['values'] = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"]
            return

        # CORRECTED Condition: Check internal state of translator for successful configuration
        # The current_api_key of the main translator instance might not represent whether a key can actually list models
        # _load_gemini_models should try to use the provided key to configure and list models
        
        # Lock access to genai.configure and genai.list_models
        with GEMINI_API_LOCK:
            try:
                # Try using the key from the current GUI to configure genai, just for listing models
                current_gui_key = self.api_key_var.get()
                if not current_gui_key or current_gui_key == DEFAULT_API_KEY_PLACEHOLDER:
                     self.log_message("API Key not set for model listing. Using default model list.", "warn")
                     self.model_combo['values'] = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"]
                     return
                
                # Ensure no reference to self.translator here for configuring genai for model listing
                # genai.configure will be called directly with current_gui_key
                genai.configure(api_key=current_gui_key) # Configure directly for model listing
                self.log_message(f"Fetching available Gemini models using key ending ...{current_gui_key[-4:]}...", "info")
                models = genai.list_models()
                # Filter for models that support 'generateContent' and are likely text generation models
                suitable_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods and "gemini" in m.name]
                
                if suitable_models:
                    self.model_combo['values'] = sorted(list(set(suitable_models)))
                    current_selected = self.selected_model_var.get()
                    if current_selected in suitable_models:
                        self.selected_model_var.set(current_selected)
                    elif suitable_models: # 修正：确保 suitable_models 非空
                        self.selected_model_var.set(suitable_models[0])
                    self.log_message(f"Loaded {len(suitable_models)} Gemini models.", "info")
                else:
                    self.log_message("No suitable Gemini models found via API. Using default list.", "warn")
                    self.model_combo['values'] = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"]
            except Exception as e:
                # Check if current_gui_key was defined before trying to use it in the log message
                key_to_log = current_gui_key[-4:] if 'current_gui_key' in locals() and current_gui_key and len(current_gui_key) >=4 else 'N/A'
                self.log_message(f"Error fetching Gemini models (key: ...{key_to_log}): {e}. Using default list.", "error")
                self.model_combo['values'] = ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest", "gemini-1.0-pro"]  # Fallback

    def _populate_language_dropdowns(self):
        loc_path = self.localization_root_path.get()
        if not loc_path or not os.path.isdir(loc_path):
            self.source_lang_combo['values'] = []
            # self.source_language_code.set("") # Don't reset if just path is invalid, keep config value
            self._load_files_for_translation()
            return
        try:
            subfolders = [d for d in os.listdir(loc_path) if os.path.isdir(os.path.join(loc_path, d))]
            valid_langs = []
            for folder_name in subfolders:
                lang_code_from_folder = self._get_lang_code_from_folder_content(os.path.join(loc_path, folder_name))
                if lang_code_from_folder:
                    valid_langs.append(lang_code_from_folder)
                elif folder_name.lower() in ["english", "french", "german", "spanish", "russian", "japanese", "korean", "polish", "simp_chinese", "braz_por"]:
                    valid_langs.append(folder_name)
            if not valid_langs:
                self.log_message("未找到可识别的 l_<lang>: 头的语言子目录。将列出所有子目录。", "warn")
                valid_langs = subfolders
            unique_valid_langs = sorted(list(set(valid_langs)))
            
            current_config_source_lang = self.config_manager.get_setting("source_language")
            self.source_lang_combo['values'] = unique_valid_langs
            if unique_valid_langs:
                if current_config_source_lang in unique_valid_langs:
                    self.source_language_code.set(current_config_source_lang)
                elif 'english' in unique_valid_langs:
                    self.source_language_code.set('english')
                else:
                    self.source_language_code.set(unique_valid_langs[0])
            # else: self.source_language_code.set("") # Keep config if no folders found
            self._load_files_for_translation()
        except Exception as e:
            self.log_message(f"读取语言文件夹错误: {e}", "error")
            self.source_lang_combo['values'] = []
            self._load_files_for_translation()

    def _get_lang_code_from_folder_content(self, folder_path):
        try:
            for item in os.listdir(folder_path):
                if item.endswith((".yml", ".yaml")):
                    filepath = os.path.join(folder_path, item)
                    if not os.path.isfile(filepath):
                        continue
                    try:
                        with open(filepath, 'r', encoding='utf-8-sig') as f:
                            first_line = f.readline()
                            match = YMLParser.LANGUAGE_HEADER_REGEX.match(first_line)
                            if match:
                                return match.group(1)
                    except Exception as e_file:
                        self.log_message(f"无法读取 {filepath} 以确定语言代码: {e_file}", "debug")
                        continue
        except Exception as e_dir:
            self.log_message(f"无法列出目录 {folder_path} 以确定语言代码: {e_dir}", "debug")
            return None
        return None

    def _load_files_for_translation(self):
        """加载待翻译文件列表"""
        # 清空现有文件列表
        self.files_tree.delete(*self.files_tree.get_children()) 
        root_loc_path = self.localization_root_path.get()
        source_lang_val = self.source_language_code.get() 
        
        if not root_loc_path or not source_lang_val:
            if hasattr(self, 'files_count_label'):
                self.files_count_label.config(text="共 0 个文件")
            return
            
        source_lang_path = os.path.join(root_loc_path, source_lang_val)
        if not os.path.isdir(source_lang_path):
            self.log_message(f"源语言文件夹未找到: {source_lang_path}", "error")
            if hasattr(self, 'files_count_label'):
                self.files_count_label.config(text="共 0 个文件")
            return
            
        self.log_message(f"正在从以下位置加载文件: {source_lang_path}", "info")
        found_files_count = 0
        
        for dirpath, _, filenames in os.walk(source_lang_path):
            for filename in filenames:
                if filename.endswith((".yml", ".yaml")) and f"_l_{source_lang_val}.yml" in filename:
                    full_path = os.path.join(dirpath, filename)
                    relative_path = os.path.relpath(full_path, source_lang_path)
                    
                    # 为行设置交替颜色和状态标签
                    row_tags = ('evenrow', 'oddrow')[found_files_count % 2]
                    self.files_tree.insert("", tk.END, values=(relative_path, "待处理"), tags=(row_tags, 'pending'))
                    
                    found_files_count += 1
                    
        # 更新文件计数标签
        if hasattr(self, 'files_count_label'):
            self.files_count_label.config(text=f"共 {found_files_count} 个文件")
            
        if found_files_count == 0:
            self.log_message(f"在 {source_lang_path} 或其子目录中未找到 '*_l_{source_lang_val}.yml' 文件。", "warn")
        else:
            self.log_message(f"找到 {found_files_count} 个待翻译文件。", "info")

    @DebouncedButton(debounce_time=2000)  # 2秒防抖
    def _start_translation_process(self):
        self.config_manager.save_config()  # Save current settings before starting a potentially long process
        self.log_message("_start_translation_process called", "debug")

        # Log initial state
        self.log_message(f"Root path: {self.localization_root_path.get()}", "debug")
        self.log_message(f"Source lang: {self.source_language_code.get()}", "debug")
        self.log_message(f"Target lang: {self.target_language_code.get()}", "debug")
        api_key_present = self.api_key_var.get() and self.api_key_var.get() != DEFAULT_API_KEY_PLACEHOLDER
        self.log_message(f"API key set: {api_key_present}", "debug")

        if not self.localization_root_path.get() or \
           not self.source_language_code.get() or \
           not self.target_language_code.get():
            self.log_message("Missing path or language settings.", "warn")
            messagebox.showerror("信息缺失", "请选择本地化根目录、源语言和目标语言。")
            return
        if not api_key_present: # Use the pre-calculated boolean
            self.log_message("API Key is missing.", "warn")
            messagebox.showerror("API密钥缺失", "请输入您的 Gemini API 密钥。")
            self.api_key_entry.focus_set()
            return

        tree_children = self.files_tree.get_children()
        self.log_message(f"Files in tree: {len(tree_children)} items.", "debug")
        if not tree_children:
            self.log_message("No files loaded in the tree view.", "warn")
            messagebox.showinfo("无文件", "未加载翻译文件。请检查文件夹和源语言设置。")
            return

        self.stop_translation_flag.clear()
        self.translate_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self._update_progress(0)
        self.log_message("开始翻译流程... (UI updated)", "info")
        
        self.files_to_process = [self.files_tree.item(item_id, 'values')[0] for item_id in tree_children]
        self.log_message(f"Files to process (initial list from tree): {self.files_to_process}", "debug")

        if not self.files_to_process:
            self.log_message("files_to_process list is empty after populating from tree.", "warn")
            messagebox.showinfo("无文件", "文件列表中没有文件可供翻译。")
            self.translate_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return

        self._calculate_totals_for_translation() 
        self.log_message(f"After _calculate_totals_for_translation, overall_total_keys: {self.overall_total_keys}", "debug")

        if self.overall_total_keys == 0:
            self.log_message("No translatable entries found (overall_total_keys is 0).", "info")
            messagebox.showinfo("无条目", "选中的文件中没有找到可翻译的条目。")
            self.translate_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            return

        # Update tree items to "排队中"
        self.log_message("Updating tree items to '排队中' status.", "debug")
        for item_id in self.files_tree.get_children():
            filepath_rel = self.files_tree.item(item_id, 'values')[0]
            current_tags = self.files_tree.item(item_id, 'tags')
            stripe_tag = current_tags[0] if current_tags and current_tags[0] in ('evenrow', 'oddrow') else 'evenrow'
            self.files_tree.item(item_id, values=(filepath_rel, "排队中"), tags=(stripe_tag, 'pending'))

        self.log_message("Reloading API keys for ParallelTranslator.", "debug")
        self.parallel_translator.api_key_manager.reload_keys()
        self.log_message("Initializing translators for ParallelTranslator.", "debug")
        self.parallel_translator.init_translators() 
        num_workers = self.config_manager.get_setting("max_concurrent_tasks", 3)
        self.log_message(f"Starting ParallelTranslator workers (num_workers: {num_workers}).", "debug")
        self.parallel_translator.start_workers(num_workers)
        self.log_message("ParallelTranslator workers started.", "debug")

        submitted_tasks_count = 0
        self.log_message(f"向并行翻译器提交 {self.overall_total_keys} 个条目...", "info")
        for filepath_rel, file_prog_data in self.file_translation_progress.items():
            if self.stop_translation_flag.is_set(): 
                self.log_message("Stop flag set during task submission loop for files.", "warn")
                break
            source_lang_for_file = file_prog_data["original_lang_code"]
            
            for entry_data in file_prog_data["source_file_entries"]:
                if self.stop_translation_flag.is_set(): 
                    self.log_message("Stop flag set during task submission loop for entries.", "warn")
                    break
                entry_id = f"{filepath_rel}::{entry_data['key']}"
                task = {
                    "entry_id": entry_id,
                    "text": entry_data['value'],
                    "source_lang": source_lang_for_file,
                    "target_lang": self.target_language_code.get(),
                    "game_mod_style": self.game_mod_style_prompt.get(),
                    "model_name": self.selected_model_var.get(),
                    "original_line_content": entry_data['original_line_content']
                }
                self.parallel_translator.add_translation_task(**task)
                submitted_tasks_count += 1
            if self.stop_translation_flag.is_set(): break
        
        self.log_message(f"Actual tasks submitted to ParallelTranslator: {submitted_tasks_count}", "info")

        if self.stop_translation_flag.is_set():
            self.log_message("翻译启动过程中用户选择停止。 清理并结束。", "warn")
            self._on_all_tasks_finished() # Clean up as if it was stopped
            return

        self.log_message("所有任务已提交，开始检查结果队列。", "info")
        self.root.after(100, self._check_queue)

    def _stop_translation_process(self):
        if not self.stop_translation_flag.is_set(): # Prevent multiple calls issues
            self.log_message("正在停止翻译流程...", "warn")
            self.stop_translation_flag.set()
            self.parallel_translator.stop_workers() # Signal workers to stop and attempt to join them
            # Further cleanup and UI updates will be handled by _check_queue or _on_all_tasks_finished
            # when the stop flag is detected.
            self.status_label.config(text="正在停止翻译...")
        else:
            self.log_message("停止命令已在处理中。", "debug")

    def _check_queue(self):
        if self.stop_translation_flag.is_set():
            self.log_message("检查队列：检测到停止标志，将调用 _on_all_tasks_finished 进行清理。", "debug")
            self._on_all_tasks_finished() # Centralized stop handling
            return

        try:
            result_data = self.parallel_translator.get_translation_result(timeout=0.1) # Short timeout
            
            if result_data:
                entry_id = result_data.get("entry_id")
                original_text = result_data.get("original_text")
                ai_translated_text = result_data.get("translated_text") # This is the direct AI output
                api_error_type = result_data.get("api_error_type") # From GeminiTranslator
                
                if not entry_id or original_text is None or ai_translated_text is None:
                    self.log_message(f"检查队列：收到不完整的结果数据: {result_data}", "error")
                    # Consider how to count this towards progress if entry_id is known
                else:
                    self.log_message(f"检查队列：收到结果 for {entry_id[:50]}...", "debug")
                    filepath_rel, key_for_dialog = entry_id.split("::", 1)

                    original_placeholders = self.yml_parser.extract_placeholders(original_text)
                    translated_placeholders = self.yml_parser.extract_placeholders(ai_translated_text)
                    
                    missing_phs = original_placeholders - translated_placeholders
                    added_phs = translated_placeholders - original_placeholders
                    has_placeholder_issues = bool(missing_phs or added_phs)

                    should_review = (has_placeholder_issues or api_error_type) or not self.auto_approve_var.get()
                    
                    if should_review:
                        self.log_message(f"条目 '{entry_id}' 被标记为需要稍后评审。占位符问题: {has_placeholder_issues}, API错误: {api_error_type}, 自动批准: {self.auto_approve_var.get()}", "info")
                        review_task_data = {
                            "entry_id": entry_id,
                            "original_text": original_text,
                            "ai_translation": ai_translated_text,
                            "original_line_content": result_data.get("original_line_content"),
                            "source_lang": result_data.get("source_lang"),
                            "original_placeholders": original_placeholders,
                            "ai_translated_placeholders": translated_placeholders,
                            "raw_result_data": result_data # Store the full result for context if needed later
                        }
                        self.items_to_review_later.append(review_task_data)
                        # 即使需要评审，也先用AI的翻译处理进度和内部数据，后续评审会覆盖
                        self._finalize_entry_processing(result_data, ai_translated_text) 
                    else: # 不需要评审，直接最终处理
                        self._finalize_entry_processing(result_data, ai_translated_text)
            
        except queue.Empty:
            # This is normal if timeout is used and queue is empty; loop will continue based on conditions below
            pass 
        except Exception as e:
            self.log_message(f"检查队列时发生意外错误: {e}", "error")
            import traceback
            self.log_message(traceback.format_exc(), "debug")
            # Potentially stop or signal error state, for now, will try to continue polling or stop via flag

        # 检查API调用和初步处理阶段是否完成
        if self.overall_processed_keys >= self.overall_total_keys:
            if self.parallel_translator.is_processing_complete(): # 确保ParallelTranslator的所有内部队列和工作线程也完成了
                self.log_message("检查队列：所有条目已完成初步API处理且并行翻译器空闲。", "info")
                self._start_deferred_review_process() # <--- 新的下一阶段调用
                return # 停止 _check_queue 轮询, 评审流程将接管或结束流程
            else:
                # 所有条目的结果已从PT队列中取出并初步处理，但PT本身可能仍在关闭其工作线程或其队列状态尚未最终更新。
                self.log_message(f"检查队列：条目计数完成 ({self.overall_processed_keys}/{self.overall_total_keys}), 但 PT 队列 ({self.parallel_translator.get_queue_size()}) 或工作线程未完全空闲。继续等待PT完成...", "debug")
                self.root.after(100, self._check_queue) # 继续轮询等待PT完全空闲
                return
        else:
            # API调用/初步处理阶段尚未完成，继续轮询
            self.root.after(100, self._check_queue)
            return

    def log_message(self, message, level="info"):
        """记录日志消息"""
        if not hasattr(self, 'log_text') or not self.log_text:
            # 如果日志控件尚未创建
            print(f"[{time.strftime('%H:%M:%S')}] [{level.upper()}] {message}") # 添加时间戳以便调试
            return
              # 根据日志级别过滤
        log_levels = {
            "debug": 0,
            "info": 1,
            "success": 1.5,  # 将success级别设为info和warn之间
            "warn": 2,
            "error": 3
        }
        
        current_level = log_levels.get(self.log_level_var.get() if hasattr(self, 'log_level_var') else "info",  1)
        message_level = log_levels.get(level, 1)
        
        if message_level >= current_level:
            timestamp = time.strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] [{level.upper()}] {message}\n"
            
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, formatted_message, level)
            self.log_text.configure(state='disabled')
            self.log_text.see(tk.END)
            
            # 更新状态栏最新消息
            if hasattr(self, 'status_label'):
                self.status_label.config(text=message[:50] + ("..." if len(message) > 50 else ""))
            
        # 总是在控制台输出调试和错误信息
        if level == "debug" or level == "error":
            print(f"[{level.upper()}] {message}")

    def _update_api_delay_setting(self):
        """
        更新API调用延迟设置，当用户更改延迟值时触发。
        保存到配置并适当时显示提示信息。
        """
        try:
            # 获取并验证新的延迟值
            new_value = self.api_call_delay_var.get()
            try:
                new_delay = float(new_value)
            except (ValueError, TypeError):
                self.log_message(f"无效的延迟值: {new_value}", "error")
                new_delay = float(self.config_manager.get_setting("api_call_delay", 3.0))
            
            # 确保延迟值在合理范围内
            if new_delay < 1.0:
                new_delay = 1.0
            elif new_delay > 10.0:
                new_delay = 10.0
            self.api_call_delay_var.set(f"{new_delay:.1f}")
                
            # 将新值保存到配置
            previous_delay = float(self.config_manager.get_setting("api_call_delay", 3.0))
            if previous_delay != new_delay:
                self.config_manager.set_setting("api_call_delay", new_delay)
                self.log_message(f"API调用延迟已更新为 {new_delay:.1f} 秒", "info")
                
                    
        except (ValueError, TypeError) as e:
            self.log_message(f"设置API调用延迟时出错: {e}", "error")
            # 恢复为默认值或之前的值
            default_delay = 3.0
            self.api_call_delay_var.set(f"{default_delay:.1f}")
            self.config_manager.set_setting("api_call_delay", default_delay)
            
    def _calculate_totals_for_translation(self):
        self.log_message("Calculating total entries for translation...", "info")
        self.file_translation_progress.clear()
        self.overall_total_keys = 0
        self.overall_processed_keys = 0
        
        source_root = os.path.join(self.localization_root_path.get(), self.source_language_code.get())
        if not self.files_to_process: # files_to_process should be populated before calling this
             self.log_message("No files selected or found for translation.", "warn")
             return

        for relative_filepath in self.files_to_process:
            source_filepath = os.path.join(source_root, relative_filepath)
            original_lang_code, entries = self.yml_parser.load_file(source_filepath)
            if not entries and not original_lang_code : # Allow empty files if they have a language header
                self.log_message(f"Skipping empty or unreadable file: {relative_filepath}", "warn")
                self.file_translation_progress[relative_filepath] = {
                    "total_entries": 0, 
                    "processed_entries": 0, 
                    "translated_entries_data": [], 
                    "has_errors": False, # Or True if load error
                    "original_lang_code": original_lang_code or self.source_language_code.get(),
                    "source_file_entries": [] # Store original entries for context if needed
                }
                continue

            self.file_translation_progress[relative_filepath] = {
                "total_entries": len(entries),
                "processed_entries": 0,
                "translated_entries_data": [],
                "has_errors": False,
                "original_lang_code": original_lang_code or self.source_language_code.get(), # Use file's lang code if present
                "source_file_entries": entries # Store original entries
            }
            self.overall_total_keys += len(entries)
        self.log_message(f"Total entries to translate across all files: {self.overall_total_keys}", "info")

    def _handle_review_completion(self, entry_key_from_dialog, reviewed_text):
        # This method is now effectively REPLACED by _handle_deferred_review_completion
        # The old logic from the previous step might be here if not fully cleaned by auto-apply.
        # We will ensure it's either gone or benign, and the new flow uses _handle_deferred_review_completion.
        self.log_message(f"DEPRECATED _handle_review_completion called for {entry_key_from_dialog}. This should not happen in deferred flow.", "warn")
        # Fallback or error handling if this is ever called unexpectedly.
        # For safety, try to process next if items_to_review_later is somehow being used by old logic (it shouldn't)
        if self.items_to_review_later: 
            self._process_next_deferred_review()

    def _finalize_entry_processing(self, entry_data_from_parallel_q, final_translation_text):
        # entry_data_from_parallel_q is expected to be a dict like:
        # {"entry_id": "filepath_rel::key", "original_text": ..., "ai_translated_text": ..., 
        #  "token_count": ..., "api_error_type": ..., "original_line_content": ..., "source_lang": ...}

        entry_id = entry_data_from_parallel_q.get("entry_id")
        if not entry_id or "::" not in entry_id:
            self.log_message(f"Invalid entry_id in _finalize_entry_processing: {entry_id}", "error")
            return

        filepath_rel, key = entry_id.split("::", 1)
        
        if filepath_rel not in self.file_translation_progress:
            self.log_message(f"File {filepath_rel} not found in progress tracking.", "error")
            # This case should ideally not happen if _calculate_totals_for_translation was run correctly
            return

        file_prog = self.file_translation_progress[filepath_rel]

        if entry_data_from_parallel_q.get("api_error_type"):
            file_prog["has_errors"] = True
            self.log_message(f"Error noted for {key} in {filepath_rel}: {entry_data_from_parallel_q.get('api_error_type')}", "warn")
            # If API error, final_translation_text is likely the original text or some fallback
            
        # Find the original_line_content for this key from the stored source_file_entries
        # This is crucial because entry_data_from_parallel_q might not have it directly if it was an API error before even loading.
        # However, add_translation_task should include it.
        original_line_content = entry_data_from_parallel_q.get('original_line_content')
        if not original_line_content:
            # Fallback: try to find it in the initially loaded entries for the file
            source_entries = file_prog.get("source_file_entries", [])
            found_entry = next((e for e in source_entries if e['key'] == key), None)
            if found_entry:
                original_line_content = found_entry['original_line_content']
            else:
                self.log_message(f"Could not find original_line_content for key '{key}' in {filepath_rel}", "error")
                original_line_content = f" {key}: \"ERROR_ORIGINAL_LINE_NOT_FOUND\"" # Placeholder

        file_prog["translated_entries_data"].append({
            'key': key,
            'translated_value': final_translation_text if final_translation_text is not None else entry_data_from_parallel_q.get("original_text",""), # Ensure not None
            'original_line_content': original_line_content
        })
        
        # Only increment processed_entries if it hasn't been processed before (safeguard)
        # This simple increment might be problematic if an entry is re-processed.
        # A more robust way would be to track processed keys in a set per file.
        # For now, assume linear processing.
        if file_prog["processed_entries"] < file_prog["total_entries"]:
             file_prog["processed_entries"] += 1
             self.overall_processed_keys += 1
        else:
            self.log_message(f"Warning: file {filepath_rel} entry {key} seems to be processed more than once or total_entries is mismatched.", "warn")


        self._update_progress((self.overall_processed_keys / self.overall_total_keys) * 100 if self.overall_total_keys > 0 else 0)
        self.log_message(f"Processed: {self.overall_processed_keys}/{self.overall_total_keys} keys. File {filepath_rel}: {file_prog['processed_entries']}/{file_prog['total_entries']}", "debug")

        # 文件完成其所有条目的初步处理后，不再立即保存
        # if file_prog["processed_entries"] == file_prog["total_entries"]:
            # self._save_translated_file(filepath_rel) # REMOVED: Saving is deferred
        
        # 移除此处的 overall_processed_keys >= self.overall_total_keys 检查，
        # 因为 _check_queue 现在负责转换到下一个阶段 (_start_deferred_review_process) 或结束 (_on_all_tasks_finished)

    def _save_translated_file(self, filepath_rel):
        self.log_message(f"Attempting to save translated file: {filepath_rel}", "info")
        if filepath_rel not in self.file_translation_progress:
            self.log_message(f"Cannot save file {filepath_rel}, no progress data found.", "error")
            return

        file_prog = self.file_translation_progress[filepath_rel]
        target_lang = self.target_language_code.get()
        source_lang_for_file = file_prog["original_lang_code"] # Use the detected/stored source lang for this file

        target_root = os.path.join(self.localization_root_path.get(), target_lang)
        os.makedirs(target_root, exist_ok=True)

        base, ext = os.path.splitext(filepath_rel)
        # Ensure correct replacement for filenames like "myevents_l_english.yml" -> "myevents_l_simp_chinese.yml"
        target_filename_base = base.replace(f"_l_{source_lang_for_file}", f"_l_{target_lang}")
        if f"_l_{source_lang_for_file}" not in base : # If the original filename didn't follow the pattern, append target lang
             name_part, _ = os.path.splitext(base) # Get name without extension
             target_filename_base = f"{name_part}_l_{target_lang}"


        target_relative_filepath = target_filename_base + ext
        target_filepath = os.path.join(target_root, target_relative_filepath)
        os.makedirs(os.path.dirname(target_filepath), exist_ok=True)
        
        try:
            self.yml_parser.save_file(
                target_filepath, 
                target_lang, 
                file_prog["translated_entries_data"], 
                source_lang_for_file 
            )
            status_msg = "已翻译" if not file_prog["has_errors"] else "已翻译 (有问题)"
            status_tag = "done" if not file_prog["has_errors"] else "error"
            log_level = "success" if not file_prog["has_errors"] else "warn"
            self.log_message(f"File saved: {target_filepath}", log_level)
        except Exception as e:
            status_msg = "保存失败"
            status_tag = "error"
            self.log_message(f"Error saving file {target_filepath}: {e}", "error")
            file_prog["has_errors"] = True # Ensure error is marked

        # Update tree view
        for item_id in self.files_tree.get_children():
            if self.files_tree.item(item_id, 'values')[0] == filepath_rel:
                current_tags = self.files_tree.item(item_id, 'tags')
                stripe_tag = current_tags[0] if current_tags and current_tags[0] in ('evenrow', 'oddrow') else 'evenrow' # Default if no tag
                self.files_tree.item(item_id, values=(filepath_rel, status_msg), tags=(stripe_tag, status_tag))
                break
    
    def _on_all_tasks_finished(self):
        if self.stop_translation_flag.is_set():
            self.log_message("翻译流程被用户停止。", "warn")
        else:
            self.log_message("所有翻译任务处理完成。", "success")
        
        self.translate_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self._update_progress(100 if not self.stop_translation_flag.is_set() else self.progress_bar['value'])
        
        # Ensure workers are stopped if they are running and not flagged to stop by user
        if not self.stop_translation_flag.is_set(): # If naturally finished
            self.parallel_translator.stop_workers() 
            
        self.stop_translation_flag.clear()
        self.items_to_review_later.clear()
        self.current_reviewing_item_details = None
        self.total_items_for_review_phase = 0
        self.processed_items_in_review_phase = 0
        # self.file_translation_progress can be kept for inspection or cleared. Let's keep it for now.
        # self.overall_total_keys = 0
        # self.overall_processed_keys = 0

    def _start_deferred_review_process(self):
        self.log_message("开始稍后评审流程...", "info")
        if not self.items_to_review_later:
            self.log_message("没有需要稍后评审的条目。进行保存。", "info")
            self._save_all_files_final()
            # self._on_all_tasks_finished() # _save_all_files_final will call this or lead to it
            return
        
        self.log_message(f"找到 {len(self.items_to_review_later)} 个条目进行稍后评审。", "info")
        self._update_progress(0) # 重置评审阶段的进度条
        self.total_items_for_review_phase = len(self.items_to_review_later)
        self.processed_items_in_review_phase = 0
        self.status_label.config(text=f"评审中 {self.processed_items_in_review_phase}/{self.total_items_for_review_phase} 项...")
        self._process_next_deferred_review()

    def _process_next_deferred_review(self):
        if self.stop_translation_flag.is_set():
            self.log_message("评审过程中检测到停止标志。", "warn")
            self._on_all_tasks_finished() # Cleanup
            return

        if not self.items_to_review_later:
            self.log_message("所有稍后评审已完成。", "info")
            self._save_all_files_final()
            # self._on_all_tasks_finished() will be called after save typically
            return

        self.current_reviewing_item_details = self.items_to_review_later.pop(0) # 获取列表中的第一个条目
        entry_id = self.current_reviewing_item_details["entry_id"]
        self.log_message(f"正在评审 (稍后): {entry_id}", "info")
        
        # 更新状态栏，显示当前评审进度
        self.status_label.config(text=f"评审: {entry_id[:30]}... ({self.processed_items_in_review_phase + 1}/{self.total_items_for_review_phase})")

        ReviewDialog(self, self.root,
                       self.current_reviewing_item_details["original_text"],
                       self.current_reviewing_item_details["ai_translation"],
                       self.current_reviewing_item_details["original_placeholders"],
                       self.current_reviewing_item_details["ai_translated_placeholders"],
                       entry_id, # key_name_arg for dialog
                       self._handle_deferred_review_completion) # Use the new callback

    def _handle_deferred_review_completion(self, entry_id_from_dialog, reviewed_text_from_dialog):
        if self.stop_translation_flag.is_set():
            self.log_message("评审回调中检测到停止标志。", "warn")
            # self._on_all_tasks_finished() will be called eventually by stop logic
            return

        if not self.current_reviewing_item_details or self.current_reviewing_item_details["entry_id"] != entry_id_from_dialog:
            self.log_message(f"错误: 评审完成回调中的条目ID不匹配。预期 {self.current_reviewing_item_details['entry_id'] if self.current_reviewing_item_details else '无'}, 收到 {entry_id_from_dialog}", "error")
            # 尝试继续处理下一个，以避免卡死
            self.root.after(10, self._process_next_deferred_review)
            return

        final_text_to_use = reviewed_text_from_dialog
        if reviewed_text_from_dialog is None: # 对话框被取消
            final_text_to_use = self.current_reviewing_item_details["ai_translation"] # 使用之前存储的AI翻译
            self.log_message(f"条目 {entry_id_from_dialog} 的评审被取消，使用已存储的AI翻译。", "info")

        filepath_rel, key = entry_id_from_dialog.split("::", 1)

        if filepath_rel in self.file_translation_progress:
            file_prog = self.file_translation_progress[filepath_rel]
            entry_found_and_updated = False
            for entry_dict in file_prog["translated_entries_data"]:
                if entry_dict['key'] == key:
                    entry_dict['translated_value'] = final_text_to_use
                    entry_found_and_updated = True
                    self.log_message(f"已使用评审后的翻译更新 '{key}' (位于 '{filepath_rel}'): '{str(final_text_to_use)[:30]}...'", "debug")
                    break
            if not entry_found_and_updated:
                self.log_message(f"错误: 在评审更新期间，无法在 '{filepath_rel}' 的 translated_entries_data 中找到键 '{key}'。这不应发生。", "error")
        else:
            self.log_message(f"错误: 在评审更新期间，无法在 file_translation_progress 中找到文件路径 '{filepath_rel}'。", "error")

        self.processed_items_in_review_phase += 1
        progress_percentage = (self.processed_items_in_review_phase / self.total_items_for_review_phase) * 100 if self.total_items_for_review_phase > 0 else 100
        self._update_progress(progress_percentage)
        self.status_label.config(text=f"评审完成 {self.processed_items_in_review_phase}/{self.total_items_for_review_phase} 项...")

        self.current_reviewing_item_details = None # 清理当前评审的条目
        self.root.after(10, self._process_next_deferred_review) # 处理下一个评审条目

    def _save_all_files_final(self):
        if self.stop_translation_flag.is_set():
            self.log_message("最终保存前检测到停止请求。", "warn")
            self._on_all_tasks_finished() # Go to cleanup
            return

        self.log_message("评审阶段后开始保存所有已翻译文件...", "info")
        self.status_label.config(text="正在保存所有文件...")
        
        # 使用一个新的进度条阶段，或者可以重置主进度条
        # For simplicity, let's assume _update_progress can be reused if we consider saving as another phase.
        # However, _save_translated_file already updates tree view. No separate progress bar for this sub-step for now.

        all_files_processed_in_save = list(self.file_translation_progress.keys())
        total_files_to_save = len(all_files_processed_in_save)
        saved_files_count = 0

        for filepath_rel in all_files_processed_in_save:
            if self.stop_translation_flag.is_set():
                self.log_message("最终保存过程中被停止。中止进一步的保存。", "warn")
                break
            self._save_translated_file(filepath_rel) # 此方法已更新树视图状态
            saved_files_count += 1
        
        self.log_message(f"完成保存 {saved_files_count}/{total_files_to_save} 个文件。", "info")
        self._on_all_tasks_finished() # 所有工作完成，包括保存

    def _update_ui(self, func, *args, **kwargs):
        """确保UI更新在主线程中执行"""
        if threading.current_thread() is threading.main_thread():
            func(*args, **kwargs)
        else:
            self.root.after(0, lambda: func(*args, **kwargs))
        
    def _safe_button_state(self, button, state):
        """线程安全地更新按钮状态"""
        self._update_ui(button.config, state=state)
    
    def _safe_progress_update(self, value):
        """线程安全地更新进度条"""
        def update():
            if hasattr(self, 'progress_bar'):
                self.progress_bar['value'] = value
            if hasattr(self, 'progress_percent'):
                self.progress_percent.config(text=f"{int(value)}%")
        self._update_ui(update)

    def _setup_api_key_ui(self):
        """设置API密钥管理UI"""
        # 替换原有的API密钥输入框
        api_key_frame = ttk.LabelFrame(self.settings_frame, text="🔑 API密钥管理", padding=(10, 5))
        api_key_frame.pack(fill=X, pady=(5, 10), padx=5)
        
        # 密钥列表框架
        key_list_frame = ttk.Frame(api_key_frame)
        key_list_frame.pack(fill=X, pady=5)
        
        # 密钥列表
        self.key_listbox = tk.Listbox(key_list_frame, height=3, selectmode=tk.SINGLE)
        self.key_listbox.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        key_scrollbar = ttk.Scrollbar(key_list_frame, orient=tk.VERTICAL, command=self.key_listbox.yview)
        key_scrollbar.pack(side=RIGHT, fill=Y)
        self.key_listbox.config(yscrollcommand=key_scrollbar.set)
        
        # 加载密钥到列表框
        self._reload_api_key_listbox()
        
        # 密钥操作按钮框架
        key_buttons_frame = ttk.Frame(api_key_frame)
        key_buttons_frame.pack(fill=X, pady=5)
        
        # 添加密钥按钮
        add_key_btn = ttkb.Button(
            key_buttons_frame, 
            text="添加密钥", 
            command=self._add_api_key,
            bootstyle="success-outline",
            width=10
        )
        add_key_btn.pack(side=LEFT, padx=(0, 5))
        
        # 删除密钥按钮
        remove_key_btn = ttkb.Button(
            key_buttons_frame, 
            text="删除密钥", 
            command=self._remove_api_key,
            bootstyle="danger-outline",
            width=10
        )
        remove_key_btn.pack(side=LEFT, padx=5)
        
        # 编辑密钥按钮
        edit_key_btn = ttkb.Button(
            key_buttons_frame, 
            text="编辑密钥", 
            command=self._edit_api_key,
            bootstyle="info-outline",
            width=10
        )
        edit_key_btn.pack(side=LEFT, padx=5)

    def _reload_api_key_listbox(self):
        """重新加载API密钥到列表框"""
        if hasattr(self, 'key_listbox'):
            self.key_listbox.delete(0, tk.END)
            api_keys = self.config_manager.get_api_keys()
            for i, key in enumerate(api_keys):
                # 显示密钥的前4位和后4位，中间用...代替
                masked_key = key[:4] + "..." + key[-4:] if len(key) > 8 else key
                self.key_listbox.insert(tk.END, masked_key)
            # 如果没有密钥，添加提示
            if not api_keys:
                self.key_listbox.insert(tk.END, "请添加API密钥")

    def _add_api_key(self):
        """添加新的API密钥"""
        new_key = simpledialog.askstring("添加API密钥", "请输入新的Gemini API密钥:", show="•")
        if new_key:
            success = self.config_manager.add_api_key(new_key)
            if success:
                self.log_message(f"已添加新API密钥 (末尾为: ...{new_key[-4:]})", "success")
                self._reload_api_key_listbox()
                # 重载并行翻译器的API密钥
                if hasattr(self, 'parallel_translator') and hasattr(self.parallel_translator, 'api_key_manager'):
                    self.parallel_translator.api_key_manager.reload_keys()
            else:
                self.log_message("无法添加API密钥，可能已存在或格式无效", "error")

    def _remove_api_key(self):
        """删除选中的API密钥"""
        selected_idx = self.key_listbox.curselection()
        if not selected_idx:
            self.log_message("请先选择要删除的API密钥", "warn")
            return
        
        api_keys = self.config_manager.get_api_keys()
        if 0 <= selected_idx[0] < len(api_keys):
            key_to_remove = api_keys[selected_idx[0]]
            confirm = messagebox.askyesno("确认删除", f"确定要删除所选API密钥 (...{key_to_remove[-4:]}) 吗?")
            if confirm:
                success = self.config_manager.remove_api_key(key_to_remove)
                if success:
                    self.log_message(f"已删除API密钥 (末尾为: ...{key_to_remove[-4:]})", "info")
                    self._reload_api_key_listbox()
                    # 重载并行翻译器的API密钥
                    if hasattr(self, 'parallel_translator') and hasattr(self.parallel_translator, 'api_key_manager'):
                        self.parallel_translator.api_key_manager.reload_keys()
                else:
                    self.log_message("删除API密钥失败", "error")

    def _edit_api_key(self):
        """编辑选中的API密钥"""
        selected_idx = self.key_listbox.curselection()
        if not selected_idx:
            self.log_message("请先选择要编辑的API密钥", "warn")
            return
        
        api_keys = self.config_manager.get_api_keys()
        if 0 <= selected_idx[0] < len(api_keys):
            old_key = api_keys[selected_idx[0]]
            new_key = simpledialog.askstring("编辑API密钥", 
                                             f"请输入新的API密钥来替换当前密钥 (...{old_key[-4:]}):", 
                                             show="•")
            if new_key:
                success = self.config_manager.update_api_key(old_key, new_key)
                if success:
                    self.log_message(f"已更新API密钥 (旧密钥末尾: ...{old_key[-4:]} -> 新密钥末尾: ...{new_key[-4:]})", "success")
                    self._reload_api_key_listbox()
                    # 重载并行翻译器的API密钥
                    if hasattr(self, 'parallel_translator') and hasattr(self.parallel_translator, 'api_key_manager'):
                        self.parallel_translator.api_key_manager.reload_keys()
                else:
                    self.log_message("更新API密钥失败", "error")

    def _update_dynamic_delay_display(self):
        """更新动态延迟显示"""
        if not hasattr(self, 'parallel_translator') or not hasattr(self.parallel_translator, 'api_key_manager'):
            return
            
        base_delay = float(self.config_manager.get_setting("api_call_delay", 3.0))
        
        # 获取API密钥统计信息
        key_stats = self.parallel_translator.api_key_manager.get_key_stats()
        if not key_stats:
            self.dynamic_delay_var.set(f"{base_delay:.1f}")
            return
        
        # 计算动态延迟
        # 获取所有密钥的平均token使用量
        total_avg_tokens = 0
        valid_keys_count = 0
        for key, stats in key_stats.items():
            if stats.get("avg_tokens", 0) > 0:
                total_avg_tokens += stats.get("avg_tokens", 0)
                valid_keys_count += 1
        
        avg_tokens = total_avg_tokens / max(valid_keys_count, 1)
        
        # 获取当前选择的模型
        selected_model = self.selected_model_var.get()
        
        # 根据模型的TPM和RPM限制计算动态延迟
        model_tpm = MODEL_TPM.get(selected_model, 1000000)  # 默认值
        model_rpm = MODEL_RPM.get(selected_model, 30)  # 默认值
        
        # 计算基于TPM的延迟
        tpm_delay = (avg_tokens / model_tpm) * 60 if avg_tokens > 0 else 0
        
        # 计算基于RPM的延迟
        rpm_delay = 60 / model_rpm
        
        # 取较大的延迟作为基准，并添加一些缓冲
        calculated_delay = max(tpm_delay, rpm_delay) * 1.2  # 20%缓冲
        
        # 确保不低于基本延迟
        final_delay = max(base_delay, calculated_delay)
        
        # 更新显示
        self.dynamic_delay_var.set(f"{final_delay:.1f}")
        
        # 定期更新
        self.root.after(5000, self._update_dynamic_delay_display)

# --- Main Execution ---
if __name__ == "__main__":
    try:
        root = ttkb.Window(themename="cosmo")
    except Exception:
        root = tk.Tk() 
        messagebox.showwarning("TTKBootstrap 缺失", "TTKBootstrap 库未找到或主题加载失败。将使用标准 Tk 外观。")
    app = ModTranslatorApp(root)
    
    root.mainloop()

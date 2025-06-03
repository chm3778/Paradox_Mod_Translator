"""
Gemini翻译器

负责与Google Gemini API交互进行文本翻译
"""

import re
import time
from collections import deque
from typing import Optional, Tuple, List, Any

from config.constants import GEMINI_API_LOCK, DEFAULT_API_KEY_PLACEHOLDER, MAX_RETRIES, BACKOFF_TIMES

# 尝试导入Gemini库
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class GeminiTranslator:
    """Gemini API翻译器"""
    
    def __init__(self, app_ref: Any, translator_id: str = "default_translator"):
        """
        初始化Gemini翻译器
        
        Args:
            app_ref: 应用程序引用，用于日志记录
            translator_id: 翻译器ID
        """
        self.app_ref = app_ref
        self.translator_id = translator_id
        self.current_api_key: Optional[str] = None
        # 记录最近10次 token_count (滑动窗口)
        self.token_window = deque(maxlen=10)
        self.failed_translations: List[Tuple[str, str]] = []

    def _configure_gemini(self, api_key_to_use: str) -> bool:
        """
        配置Gemini API
        
        Args:
            api_key_to_use: 要使用的API密钥
            
        Returns:
            是否配置成功
        """
        if not GEMINI_AVAILABLE:
            self.app_ref.log_message(
                f"翻译器 {self.translator_id}: Gemini库未安装，将使用模拟模式", 
                "error"
            )
            return False
        
        if not api_key_to_use or api_key_to_use == DEFAULT_API_KEY_PLACEHOLDER:
            self.app_ref.log_message(
                f"翻译器 {self.translator_id}: API密钥未设置或为占位符", 
                "error"
            )
            self.current_api_key = None
            return False
            
        try:
            with GEMINI_API_LOCK:
                genai.configure(api_key=api_key_to_use)
            self.current_api_key = api_key_to_use
            self.app_ref.log_message(
                f"翻译器 {self.translator_id}: Gemini API配置成功，密钥: ...{api_key_to_use[-4:]}", 
                "info"
            )
            return True
        except Exception as e:
            self.app_ref.log_message(
                f"翻译器 {self.translator_id}: Gemini API配置失败: {e}", 
                "error"
            )
            self.current_api_key = None
            return False

    def _build_prompt(
        self, 
        text_to_translate: str, 
        source_lang_name: str, 
        target_lang_name: str, 
        game_mod_style: str
    ) -> str:
        """
        构建翻译提示词
        
        Args:
            text_to_translate: 要翻译的文本
            source_lang_name: 源语言名称
            target_lang_name: 目标语言名称
            game_mod_style: 游戏/Mod风格提示
            
        Returns:
            构建好的提示词
        """
        style_info = f"游戏/Mod风格提示: {game_mod_style}\n" if game_mod_style else ""
        
        use_chinese_specific_prompt = (
            (target_lang_name.lower() == "simp_chinese" and source_lang_name.lower() == "english") or
            (source_lang_name.lower() == "simp_chinese" and target_lang_name.lower() == "english")
        )

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
        else:
            prompt = f"""As a professional bilingual translation expert, proficient in {source_lang_name} and {target_lang_name}, your task is to translate the following text.
Game/Mod Style: {game_mod_style if game_mod_style else "General"}
You MUST preserve all placeholders like [...], $...$, @...! and #...! exactly as they appear in the original text.

Original Text ({source_lang_name}):
{text_to_translate}

Provide ONLY the final translated text in {target_lang_name}, wrapped strictly in double dollar signs ($$). Do not include any other explanatory text, conversational phrases, or the original text again.
Example: $$Translated text here, with all original [placeholders] and $variables$ preserved.$$
"""
        return prompt

    def _call_actual_api(self, prompt_text: str, model_name: str, api_key_for_this_call: str) -> Tuple[Optional[str], Any]:
        """
        调用实际的Gemini API
        
        Args:
            prompt_text: 提示词文本
            model_name: 模型名称
            api_key_for_this_call: 本次调用使用的API密钥
            
        Returns:
            (响应文本, token数量或错误类型) 的元组
        """
        if not GEMINI_AVAILABLE:
            # 返回符合格式要求的模拟响应
            simulated_text = f"$${prompt_text[:100]}... [模拟翻译结果]$$"
            self.app_ref.log_message(
                f"翻译器 {self.translator_id}: 使用模拟模式进行翻译（API库不可用）", 
                "warn"
            )
            return simulated_text, 0

        with GEMINI_API_LOCK:
            if self.current_api_key is None or self.current_api_key != api_key_for_this_call:
                self.app_ref.log_message(
                    f"翻译器 {self.translator_id}: API密钥不匹配或未配置，重新配置中...", 
                    "debug"
                )
                if not self._configure_gemini(api_key_for_this_call):
                    self.app_ref.log_message(
                        f"翻译器 {self.translator_id}: Gemini API配置失败", 
                        "error"
                    )
                    return None, "CONFIG_FAILURE"

            try:
                self.app_ref.log_message(
                    f"翻译器 {self.translator_id}: 调用Gemini API，模型: {model_name}，密钥: ...{api_key_for_this_call[-4:]}", 
                    "info"
                )
                
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt_text, request_options={'timeout': 120})
                
                if not response.parts:
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        block_reason_msg = f"内容被API阻止。原因: {response.prompt_feedback.block_reason}."
                        if response.prompt_feedback.safety_ratings:
                            block_reason_msg += f" 安全评级: {response.prompt_feedback.safety_ratings}"
                        self.app_ref.log_message(block_reason_msg, "error")
                        return None, "API_CALL_FAILED_NO_TEXT"
                    self.app_ref.log_message("Gemini API返回空响应", "warn")
                    return None, "API_CALL_FAILED_NO_TEXT"

                # 获取token使用信息
                token_count = None
                usage_metadata = getattr(response, 'usage_metadata', None)
                
                if usage_metadata:
                    token_count = getattr(usage_metadata, 'total_token_count', None)
                    prompt_tokens = getattr(usage_metadata, 'prompt_token_count', None)
                    candidates_tokens = getattr(usage_metadata, 'candidates_token_count', None)
                    self.app_ref.log_message(
                        f"Token使用详情 - 总计: {token_count}, 提示: {prompt_tokens}, 响应: {candidates_tokens}",
                        "debug"
                    )
                else:
                    token_count = getattr(response, 'token_count', None)
                    if token_count is None:
                        self.app_ref.log_message("无法从API响应中获取token使用信息", "warn")
                
                return response.text, token_count
                
            except Exception as e:
                self.app_ref.log_message(f"翻译器 {self.translator_id}: Gemini API调用错误: {e}", "error")
                
                error_str = str(e)
                if any(keyword in error_str for keyword in ["API_KEY_INVALID", "API_KEY_MISSING", "Malformed"]):
                    self.app_ref.log_message(
                        f"翻译器 {self.translator_id}: API密钥可能无效或格式错误", 
                        "error"
                    )
                    return None, "API_KEY_INVALID"
                elif any(keyword in error_str for keyword in ["Rate limit exceeded", "429", "quota exceeded"]):
                    return None, "Rate limit exceeded"
                
                return None, error_str

    def extract_final_translation(self, api_response_text: str) -> Optional[str]:
        """
        从API响应中提取最终翻译结果
        
        Args:
            api_response_text: API响应文本
            
        Returns:
            提取的翻译结果，如果提取失败则返回None
        """
        if api_response_text is None:
            return None
            
        # 使用正则表达式提取$$...$$之间的内容
        match = re.search(r"\$\$\s*(.*?)\s*\$\$", api_response_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 记录提取失败的详细信息
        self.app_ref.log_message(
            f"翻译器 {self.translator_id}: 无法从响应中提取最终翻译 (使用 $$...$$)", 
            "warn"
        )
        self.app_ref.log_message(
            f"翻译器 {self.translator_id}: 完整的API响应文本如下:", 
            "debug"
        )
        self.app_ref.log_message("-------------------- API Response Start --------------------", "debug")
        
        # 分块记录响应内容，避免单条日志过长
        for i in range(0, len(api_response_text), 500):
            self.app_ref.log_message(api_response_text[i:i+500], "debug")
        self.app_ref.log_message("-------------------- API Response End ----------------------", "debug")
        
        return None

    def translate(
        self,
        text_to_translate: str,
        source_lang_name: str,
        target_lang_name: str,
        game_mod_style: str,
        model_name: str,
        api_key_to_use: str
    ) -> Tuple[str, int, Optional[str]]:
        """
        翻译文本

        Args:
            text_to_translate: 要翻译的文本
            source_lang_name: 源语言名称
            target_lang_name: 目标语言名称
            game_mod_style: 游戏/Mod风格提示
            model_name: 使用的模型名称
            api_key_to_use: 使用的API密钥

        Returns:
            (翻译结果, token数量, 错误类型) 的元组
        """
        if not text_to_translate.strip():
            self.app_ref.log_message(
                f"翻译器 {self.translator_id}: 输入文本为空，直接返回空翻译",
                "info"
            )
            return "", 0, None

        prompt = self._build_prompt(text_to_translate, source_lang_name, target_lang_name, game_mod_style)
        self.app_ref.log_message(
            f"翻译器 {self.translator_id}: 翻译中 (使用密钥 ...{api_key_to_use[-4:]}): '{text_to_translate[:50]}...'",
            "debug"
        )

        # 添加重试机制
        last_error_type = "UNKNOWN_ERROR"

        for attempt in range(1, MAX_RETRIES + 1):
            raw_text, token_count_or_error = self._call_actual_api(prompt, model_name, api_key_to_use)

            if raw_text is not None:  # API调用成功
                final_translation = self.extract_final_translation(raw_text)

                # 更新滑动窗口中的token计数
                if isinstance(token_count_or_error, int) and token_count_or_error >= 0:
                    self.token_window.append(token_count_or_error)
                    self.app_ref.log_message(
                        f"翻译器 {self.translator_id}: API调用token使用量: {token_count_or_error} tokens，文本长度: {len(text_to_translate)} 字符",
                        "info"
                    )
                else:
                    self.app_ref.log_message(
                        f"翻译器 {self.translator_id}: 警告: 无法获取本次API调用的token使用量",
                        "warn"
                    )

                return final_translation or text_to_translate, token_count_or_error, None

            # API调用失败
            last_error_type = token_count_or_error if isinstance(token_count_or_error, str) else "API_CALL_FAILED_UNKNOWN"
            self.app_ref.log_message(
                f"翻译器 {self.translator_id}: API调用尝试 {attempt}/{MAX_RETRIES} 失败。错误: {last_error_type}",
                "warn"
            )

            # 对于致命错误，不进行重试
            if last_error_type in ["API_KEY_INVALID", "API_KEY_MISSING", "Malformed", "CONFIG_FAILURE"]:
                self.app_ref.log_message(
                    f"翻译器 {self.translator_id}: 致命错误 ({last_error_type})，不进行重试",
                    "error"
                )
                break

            # 如果还有重试机会，等待后重试
            if attempt < MAX_RETRIES:
                delay = BACKOFF_TIMES[attempt - 1]
                self.app_ref.log_message(
                    f"翻译器 {self.translator_id}: 将在 {delay} 秒后重试...",
                    "warn"
                )
                time.sleep(delay)
            else:
                self.app_ref.log_message(
                    f"翻译器 {self.translator_id}: 所有 {MAX_RETRIES} 次重试均失败",
                    "error"
                )

        # 所有重试失败后或遇到致命错误
        self.failed_translations.append((text_to_translate, last_error_type))
        return text_to_translate, 0, last_error_type

    def get_statistics(self) -> dict:
        """
        获取翻译器统计信息

        Returns:
            统计信息字典
        """
        total_tokens = sum(self.token_window)
        avg_tokens = total_tokens / len(self.token_window) if self.token_window else 0

        return {
            "translator_id": self.translator_id,
            "total_translations": len(self.token_window),
            "total_tokens": total_tokens,
            "avg_tokens": avg_tokens,
            "failed_translations": len(self.failed_translations),
            "current_api_key": f"...{self.current_api_key[-4:]}" if self.current_api_key else "未配置"
        }

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.token_window.clear()
        self.failed_translations.clear()

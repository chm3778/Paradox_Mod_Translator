"""
文件处理工具模块

提供文件路径处理、语言检测、文件生成等功能
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from parsers.yml_parser import YMLParser


class FileProcessor:
    """文件处理器，负责文件相关的操作"""
    
    def __init__(self, yml_parser: YMLParser):
        """
        初始化文件处理器
        
        Args:
            yml_parser: YML解析器实例
        """
        self.yml_parser = yml_parser
    
    def filter_source_language_files(self, file_paths: List[str], source_lang: str) -> List[str]:
        """
        过滤出指定源语言的文件
        
        Args:
            file_paths: 文件路径列表
            source_lang: 源语言代码
            
        Returns:
            匹配源语言的文件路径列表
        """
        source_files = []
        
        for file_path in file_paths:
            try:
                detected_lang, entries = self.yml_parser.load_file(file_path)
                if detected_lang == source_lang and entries:
                    source_files.append(file_path)
            except Exception:
                # 忽略无法解析的文件
                continue
        
        return source_files
    
    def generate_target_file_path(self, source_file_path: str, target_lang: str) -> str:
        """
        生成目标文件路径，创建与源语言文件夹等同级的目标语言文件夹

        Args:
            source_file_path: 源文件路径
            target_lang: 目标语言代码

        Returns:
            目标文件路径
        """
        # 分析源文件路径结构
        file_dir = os.path.dirname(source_file_path)
        file_name = os.path.basename(source_file_path)

        # 检测源语言并生成目标目录
        target_dir = self._generate_target_directory(file_dir, source_file_path, target_lang)

        # 替换文件名中的语言代码
        new_file_name = self._generate_target_filename(file_name, target_lang)

        return os.path.join(target_dir, new_file_name)

    def _generate_target_directory(self, source_dir: str, source_file_path: str, target_lang: str) -> str:
        """
        生成目标语言目录路径

        Args:
            source_dir: 源文件目录
            source_file_path: 源文件完整路径
            target_lang: 目标语言代码

        Returns:
            目标语言目录路径
        """
        # 检测源语言
        try:
            detected_lang, _ = self.yml_parser.load_file(source_file_path)
        except Exception:
            detected_lang = None

        # 如果无法检测源语言，尝试从路径中推断
        if not detected_lang:
            detected_lang = self._detect_language_from_path(source_dir)

        if detected_lang:
            # 检查是否在语言特定的子目录中
            dir_parts = source_dir.split(os.sep)

            # 查找源语言目录
            source_lang_index = -1
            for i, part in enumerate(dir_parts):
                if part.lower() == detected_lang.lower():
                    source_lang_index = i
                    break

            if source_lang_index >= 0:
                # 替换语言目录名
                target_dir_parts = dir_parts.copy()
                target_dir_parts[source_lang_index] = target_lang
                return os.sep.join(target_dir_parts)
            else:
                # 源语言目录不在路径中，在同级创建目标语言目录
                parent_dir = os.path.dirname(source_dir)
                return os.path.join(parent_dir, target_lang)
        else:
            # 无法检测源语言，在同级目录创建目标语言目录
            parent_dir = os.path.dirname(source_dir)
            return os.path.join(parent_dir, target_lang)

    def _detect_language_from_path(self, file_path: str) -> Optional[str]:
        """
        从文件路径中检测语言代码

        Args:
            file_path: 文件路径

        Returns:
            检测到的语言代码，如果无法检测则返回None
        """
        # 常见的语言目录名
        language_mappings = {
            'english': 'english',
            'simp_chinese': 'simp_chinese',
            'trad_chinese': 'trad_chinese',
            'japanese': 'japanese',
            'korean': 'korean',
            'french': 'french',
            'german': 'german',
            'spanish': 'spanish',
            'russian': 'russian'
        }

        path_parts = file_path.lower().split(os.sep)
        for part in path_parts:
            if part in language_mappings:
                return language_mappings[part]

        return None

    def _generate_target_filename(self, source_filename: str, target_lang: str) -> str:
        """
        生成目标文件名

        Args:
            source_filename: 源文件名
            target_lang: 目标语言代码

        Returns:
            目标文件名
        """
        # 替换语言代码
        # 例如：xxx_l_english.yml -> xxx_l_simp_chinese.yml
        pattern = r'_l_[a-zA-Z_]+\.yml$'
        if re.search(pattern, source_filename):
            new_filename = re.sub(pattern, f'_l_{target_lang}.yml', source_filename)
        else:
            # 如果没有找到语言模式，在文件名前添加目标语言
            name_part, ext = os.path.splitext(source_filename)
            new_filename = f"{name_part}_l_{target_lang}{ext}"

        return new_filename
    
    def generate_translated_file(
        self, 
        source_file_path: str, 
        target_file_path: str,
        translation_results: Dict[str, Dict],
        target_lang: str
    ) -> bool:
        """
        生成翻译后的文件
        
        Args:
            source_file_path: 源文件路径
            target_file_path: 目标文件路径
            translation_results: 翻译结果字典
            target_lang: 目标语言代码
            
        Returns:
            是否生成成功
        """
        try:
            # 读取源文件
            detected_lang, entries = self.yml_parser.load_file(source_file_path)
            if not entries:
                return False
            
            # 创建翻译后的条目列表
            translated_entries = []
            
            for entry in entries:
                entry_id = f"{source_file_path}:{entry['key']}"
                
                if entry_id in translation_results:
                    # 使用翻译结果
                    translated_text = translation_results[entry_id]['translated_text']
                    translated_entries.append({
                        'key': entry['key'],
                        'value': translated_text,
                        'original_line_content': entry.get('original_line_content', '')
                    })
                else:
                    # 保持原文
                    translated_entries.append({
                        'key': entry['key'],
                        'value': entry['value'],
                        'original_line_content': entry.get('original_line_content', '')
                    })
            
            # 确保目标目录存在
            target_dir = os.path.dirname(target_file_path)
            os.makedirs(target_dir, exist_ok=True)

            # 使用YMLParser保存文件
            return self.yml_parser.save_file(
                target_file_path,
                target_lang,
                translated_entries,
                detected_lang
            )
            
        except Exception:
            return False
    
    def validate_translation_prerequisites(
        self, 
        api_keys: List[str], 
        source_lang: str, 
        target_lang: str, 
        file_paths: List[str]
    ) -> Tuple[bool, str]:
        """
        验证翻译前置条件
        
        Args:
            api_keys: API密钥列表
            source_lang: 源语言
            target_lang: 目标语言
            file_paths: 文件路径列表
            
        Returns:
            (是否通过验证, 错误信息) 的元组
        """
        # 检查API密钥
        valid_keys = [key for key in api_keys if key != "YOUR_GEMINI_API_KEY" and key.strip()]
        if not valid_keys:
            return False, "请先配置有效的Google Gemini API密钥"
        
        # 检查语言设置
        if not source_lang or not target_lang:
            return False, "请先设置源语言和目标语言"
        
        if source_lang == target_lang:
            return False, "源语言和目标语言不能相同"
        
        # 检查文件选择
        if not file_paths:
            return False, "请先选择要翻译的YML文件"
        
        # 过滤出源语言文件
        source_files = self.filter_source_language_files(file_paths, source_lang)
        if not source_files:
            return False, f"在选中的文件中没有找到源语言({source_lang})的文件"
        
        return True, f"验证通过：找到 {len(source_files)} 个源语言文件"
    
    def scan_yml_files(self, directory: str) -> List[str]:
        """
        扫描目录中的YML文件
        
        Args:
            directory: 要扫描的目录
            
        Returns:
            YML文件路径列表
        """
        yml_files = []
        
        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(('.yml', '.yaml')):
                        yml_files.append(os.path.join(root, file))
        except Exception:
            pass
        
        return yml_files
    
    def get_file_language_info(self, file_path: str) -> Tuple[Optional[str], int]:
        """
        获取文件的语言信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            (语言代码, 条目数量) 的元组
        """
        try:
            detected_lang, entries = self.yml_parser.load_file(file_path)
            return detected_lang, len(entries) if entries else 0
        except Exception:
            return None, 0

    def analyze_directory_structure(self, root_path: str) -> Dict[str, List[str]]:
        """
        分析目录结构，按语言分组文件

        Args:
            root_path: 根目录路径

        Returns:
            按语言分组的文件字典
        """
        language_files = {}

        for root, _, files in os.walk(root_path):
            for file in files:
                if file.lower().endswith(('.yml', '.yaml')):
                    file_path = os.path.join(root, file)
                    lang_code, _ = self.get_file_language_info(file_path)

                    if lang_code:
                        if lang_code not in language_files:
                            language_files[lang_code] = []
                        language_files[lang_code].append(file_path)

        return language_files

    def preview_translation_structure(
        self,
        source_files: List[str],
        target_lang: str
    ) -> List[Tuple[str, str]]:
        """
        预览翻译后的文件结构

        Args:
            source_files: 源文件列表
            target_lang: 目标语言

        Returns:
            (源文件路径, 目标文件路径) 的元组列表
        """
        preview_pairs = []

        for source_file in source_files:
            target_file = self.generate_target_file_path(source_file, target_lang)
            preview_pairs.append((source_file, target_file))

        return preview_pairs

    def validate_target_directory_structure(
        self,
        source_files: List[str],
        target_lang: str
    ) -> Tuple[bool, str, List[str]]:
        """
        验证目标目录结构

        Args:
            source_files: 源文件列表
            target_lang: 目标语言

        Returns:
            (是否有效, 消息, 将要创建的目录列表) 的元组
        """
        directories_to_create = set()
        issues = []

        for source_file in source_files:
            try:
                target_file = self.generate_target_file_path(source_file, target_lang)
                target_dir = os.path.dirname(target_file)

                # 检查目标目录是否需要创建
                if not os.path.exists(target_dir):
                    directories_to_create.add(target_dir)

                # 检查是否有写入权限
                parent_dir = target_dir
                while parent_dir and not os.path.exists(parent_dir):
                    parent_dir = os.path.dirname(parent_dir)

                if parent_dir and not os.access(parent_dir, os.W_OK):
                    issues.append(f"没有写入权限: {parent_dir}")

            except Exception as e:
                issues.append(f"处理文件 {source_file} 时出错: {e}")

        is_valid = len(issues) == 0
        message = "目录结构验证通过" if is_valid else f"发现 {len(issues)} 个问题"

        return is_valid, message, list(directories_to_create)

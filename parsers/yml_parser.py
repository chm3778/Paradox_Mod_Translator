"""
YML文件解析器

负责解析和处理Paradox游戏的本地化YML文件
"""

import os
import re
from typing import List, Dict, Set, Tuple, Optional, Any


class YMLParser:
    """YML文件解析器，专门处理Paradox游戏的本地化文件"""
    
    # 正则表达式模式
    ENTRY_REGEX = re.compile(
        r'^\s*([a-zA-Z0-9_.-]+)\s*:\s*(?:\d+\s*)?"((?:\\.|[^"\\])*)"\s*$', 
        re.UNICODE
    )
    LANGUAGE_HEADER_REGEX = re.compile(r"^\s*l_([a-zA-Z_]+)\s*:\s*$", re.UNICODE)
    
    # 占位符正则表达式列表
    PLACEHOLDER_REGEXES = [
        re.compile(r'(\$.*?\$)'),       # 变量占位符，如$variable$
        re.compile(r'(\[.*?\])'),       # 方括号占位符，如[player.GetName]
        re.compile(r'(@\w+!)'),         # 图标占位符，如@icon!
        re.compile(r'(#\w+(?:;\w+)*.*?#!|\S*#!)'), # 格式化标记，如#bold#文本#!
    ]

    @staticmethod
    def extract_placeholders(text: str) -> Set[str]:
        """
        从文本中提取所有占位符
        
        Args:
            text: 要分析的文本
            
        Returns:
            占位符集合
        """
        placeholders = set()
        for regex in YMLParser.PLACEHOLDER_REGEXES:
            found = regex.findall(text)
            for item in found:
                # 处理元组和字符串
                placeholder = item[0] if isinstance(item, tuple) else item
                placeholders.add(placeholder)
        return placeholders

    @staticmethod
    def load_file(filepath: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
        """
        加载YML文件并解析内容
        
        Args:
            filepath: YML文件路径
            
        Returns:
            (语言代码, 条目列表) 的元组
        """
        entries = []
        language_code = None
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
                
            if not lines:
                return None, []
            
            # 尝试从第一行提取语言代码
            header_match = YMLParser.LANGUAGE_HEADER_REGEX.match(lines[0])
            if header_match:
                language_code = header_match.group(1)
            else:
                # 从文件名提取语言代码
                basename = os.path.basename(filepath)
                match_filename_lang = re.search(r'_l_([a-zA-Z_]+)\.yml$', basename)
                if match_filename_lang:
                    language_code = match_filename_lang.group(1)
                else:
                    return None, []
            
            # 解析每一行
            for i, line_content in enumerate(lines):
                # 跳过头部行
                if i == 0 and header_match:
                    continue
                    
                match = YMLParser.ENTRY_REGEX.match(line_content)
                if match:
                    key, value = match.group(1), match.group(2)
                    # 处理转义字符
                    processed_value = value.replace('\\"', '"').replace('\\n', '\n')
                    
                    entries.append({
                        'key': key,
                        'value': processed_value,
                        'original_line_content': line_content.rstrip('\n\r'),
                        'line_number': i + 1
                    })
            
            return language_code, entries
            
        except Exception as e:
            print(f"YMLParser: 加载文件 {filepath} 时发生错误: {e}")
            return None, []

    @staticmethod
    def save_file(
        filepath: str, 
        language_code: str, 
        translated_entries: List[Dict[str, str]], 
        original_source_lang_code: Optional[str] = None
    ) -> bool:
        """
        保存翻译后的条目到YML文件
        
        Args:
            filepath: 输出文件路径
            language_code: 目标语言代码
            translated_entries: 翻译后的条目列表
            original_source_lang_code: 原始语言代码（可选）
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                # 写入语言头部
                f.write(f"l_{language_code}:\n")
                
                # 跟踪已写入的键，避免重复
                written_keys = set()
                
                for entry in translated_entries:
                    key = entry['key']
                    if key in written_keys:
                        continue
                    written_keys.add(key)
                    
                    # 获取翻译后的值
                    translated_value = entry.get('translated_value', entry.get('value', ''))
                    
                    # 转义特殊字符
                    value_to_write = translated_value.replace('"', '\\"').replace('\n', '\\n')
                    
                    # 尝试保持原始格式
                    original_line = entry.get('original_line_content', '')
                    if original_line:
                        original_line_match = YMLParser.ENTRY_REGEX.match(original_line)
                        if original_line_match:
                            original_key_part = original_line.split('"')[0]
                            key_part_match = re.match(r'\s*([a-zA-Z0-9_.-]+)\s*:\s*(\d*)\s*', original_key_part)
                            
                            if key_part_match and key_part_match.group(2):
                                # 保持数字格式
                                f.write(f" {key_part_match.group(1)}:{key_part_match.group(2)} \"{value_to_write}\"\n")
                            else:
                                f.write(f" {key}: \"{value_to_write}\"\n")
                        else:
                            f.write(f" {key}: \"{value_to_write}\"\n")
                    else:
                        f.write(f" {key}: \"{value_to_write}\"\n")
            
            return True
            
        except Exception as e:
            print(f"YMLParser: 保存文件 {filepath} 时发生错误: {e}")
            return False

    @staticmethod
    def validate_file(filepath: str) -> List[str]:
        """
        验证YML文件的格式

        Args:
            filepath: 文件路径

        Returns:
            错误信息列表，空列表表示文件有效
        """
        errors = []

        # 检查文件是否存在
        if not os.path.exists(filepath):
            errors.append(f"文件不存在: {filepath}")
            return errors

        # 检查文件扩展名
        if not filepath.lower().endswith(('.yml', '.yaml')):
            errors.append("文件必须是YML格式（.yml或.yaml扩展名）")
            return errors

        try:
            language_code, entries = YMLParser.load_file(filepath)

            if language_code is None:
                errors.append("无法识别语言代码")

            if not entries:
                errors.append("文件中没有找到有效的条目")

            # 检查重复键
            keys = [entry['key'] for entry in entries]
            duplicate_keys = set([key for key in keys if keys.count(key) > 1])
            if duplicate_keys:
                errors.append(f"发现重复的键: {', '.join(duplicate_keys)}")

            # 检查空值
            empty_values = [entry['key'] for entry in entries if not entry['value'].strip()]
            if empty_values:
                errors.append(f"发现空值的键: {', '.join(empty_values[:5])}{'...' if len(empty_values) > 5 else ''}")

        except Exception as e:
            errors.append(f"文件读取错误: {str(e)}")

        return errors

    @staticmethod
    def compare_placeholders(original_text: str, translated_text: str) -> Dict[str, Set[str]]:
        """
        比较原文和译文的占位符差异
        
        Args:
            original_text: 原文
            translated_text: 译文
            
        Returns:
            包含差异信息的字典
        """
        original_placeholders = YMLParser.extract_placeholders(original_text)
        translated_placeholders = YMLParser.extract_placeholders(translated_text)
        
        return {
            'original': original_placeholders,
            'translated': translated_placeholders,
            'missing': original_placeholders - translated_placeholders,
            'added': translated_placeholders - original_placeholders,
            'common': original_placeholders & translated_placeholders
        }

    @staticmethod
    def get_file_statistics(filepath: str) -> Dict[str, Any]:
        """
        获取文件统计信息

        Args:
            filepath: 文件路径

        Returns:
            统计信息字典
        """
        try:
            language_code, entries = YMLParser.load_file(filepath)

            if not entries:
                return {'total_entries': 0, 'total_characters': 0, 'avg_length': 0}

            total_chars = sum(len(entry['value']) for entry in entries)
            avg_length = total_chars // len(entries) if entries else 0

            return {
                'total_entries': len(entries),
                'total_characters': total_chars,
                'avg_length': avg_length,
                'language_code': language_code
            }

        except Exception:
            return {'total_entries': 0, 'total_characters': 0, 'avg_length': 0}

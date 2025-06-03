"""
YML解析器测试

测试YML文件解析功能
"""

import unittest
import tempfile
import os
from parsers.yml_parser import YMLParser


class TestYMLParser(unittest.TestCase):
    """YML解析器测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_yml_content = '''l_english:
 test_key_1: "Hello World"
 test_key_2: "Welcome to [player.GetName]'s empire!"
 test_key_3: "You have $MONEY$ coins and @gold_icon! gold."
 test_key_4:1 "This is a numbered entry"
 test_key_5: "Text with #bold#formatting#! and $variables$"
'''
        
        # 创建临时YML文件
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='_l_english.yml', delete=False, encoding='utf-8-sig')
        self.temp_file.write(self.test_yml_content)
        self.temp_file.close()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_load_file(self):
        """测试文件加载"""
        language_code, entries = YMLParser.load_file(self.temp_file.name)
        
        # 验证语言代码
        self.assertEqual(language_code, "english")
        
        # 验证条目数量
        self.assertEqual(len(entries), 5)
        
        # 验证具体条目
        entry_dict = {entry['key']: entry['value'] for entry in entries}
        self.assertEqual(entry_dict['test_key_1'], "Hello World")
        self.assertEqual(entry_dict['test_key_2'], "Welcome to [player.GetName]'s empire!")
        self.assertEqual(entry_dict['test_key_3'], "You have $MONEY$ coins and @gold_icon! gold.")
    
    def test_extract_placeholders(self):
        """测试占位符提取"""
        text1 = "Welcome to [player.GetName]'s empire!"
        placeholders1 = YMLParser.extract_placeholders(text1)
        self.assertIn("[player.GetName]", placeholders1)
        
        text2 = "You have $MONEY$ coins and @gold_icon! gold."
        placeholders2 = YMLParser.extract_placeholders(text2)
        self.assertIn("$MONEY$", placeholders2)
        self.assertIn("@gold_icon!", placeholders2)
        
        text3 = "Text with #bold#formatting#! and $variables$"
        placeholders3 = YMLParser.extract_placeholders(text3)
        self.assertIn("#bold#formatting#!", placeholders3)
        self.assertIn("$variables$", placeholders3)
    
    def test_save_file(self):
        """测试文件保存"""
        # 准备测试数据
        language_code = "simp_chinese"
        translated_entries = [
            {
                'key': 'test_key_1',
                'translated_value': '你好世界',
                'original_line_content': ' test_key_1: "Hello World"'
            },
            {
                'key': 'test_key_2',
                'translated_value': '欢迎来到[player.GetName]的帝国！',
                'original_line_content': ' test_key_2: "Welcome to [player.GetName]\'s empire!"'
            }
        ]
        
        # 创建输出文件
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='_l_simp_chinese.yml', delete=False)
        output_file.close()
        
        try:
            # 保存文件
            success = YMLParser.save_file(output_file.name, language_code, translated_entries)
            self.assertTrue(success)
            
            # 验证保存的文件
            with open(output_file.name, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            
            self.assertIn("l_simp_chinese:", content)
            self.assertIn('test_key_1: "你好世界"', content)
            self.assertIn('test_key_2: "欢迎来到[player.GetName]的帝国！"', content)
            
        finally:
            if os.path.exists(output_file.name):
                os.unlink(output_file.name)
    
    def test_validate_file(self):
        """测试文件验证"""
        # 测试有效文件
        errors = YMLParser.validate_file(self.temp_file.name)
        self.assertEqual(len(errors), 0)
        
        # 测试不存在的文件
        errors = YMLParser.validate_file("nonexistent.yml")
        self.assertGreater(len(errors), 0)
        
        # 测试非YML文件
        txt_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        txt_file.write("This is not a YML file")
        txt_file.close()
        
        try:
            errors = YMLParser.validate_file(txt_file.name)
            self.assertGreater(len(errors), 0)
            self.assertTrue(any("YML格式" in error for error in errors))
        finally:
            os.unlink(txt_file.name)
    
    def test_compare_placeholders(self):
        """测试占位符比较"""
        original_text = "Welcome to [player.GetName] with $MONEY$ coins!"
        translated_text = "欢迎来到[player.GetName]，你有$MONEY$金币！"
        
        comparison = YMLParser.compare_placeholders(original_text, translated_text)
        
        # 验证比较结果
        self.assertEqual(len(comparison['missing']), 0)  # 没有缺失的占位符
        self.assertEqual(len(comparison['added']), 0)    # 没有多余的占位符
        self.assertIn("[player.GetName]", comparison['common'])
        self.assertIn("$MONEY$", comparison['common'])
        
        # 测试有问题的翻译
        bad_translation = "欢迎来到玩家的世界，你有金币！"
        bad_comparison = YMLParser.compare_placeholders(original_text, bad_translation)
        
        self.assertEqual(len(bad_comparison['missing']), 2)  # 缺失两个占位符
        self.assertIn("[player.GetName]", bad_comparison['missing'])
        self.assertIn("$MONEY$", bad_comparison['missing'])
    
    def test_get_file_statistics(self):
        """测试文件统计"""
        stats = YMLParser.get_file_statistics(self.temp_file.name)
        
        self.assertEqual(stats['total_entries'], 5)
        self.assertEqual(stats['language_code'], 'english')
        self.assertGreater(stats['total_characters'], 0)
        self.assertGreater(stats['avg_length'], 0)
    
    def test_escape_handling(self):
        """测试转义字符处理"""
        # 创建包含转义字符的测试文件
        escaped_content = '''l_english:
 test_escape_1: "He said \\"Hello\\""
 test_escape_2: "Line 1\\nLine 2"
'''
        
        escaped_file = tempfile.NamedTemporaryFile(mode='w', suffix='_l_english.yml', delete=False, encoding='utf-8-sig')
        escaped_file.write(escaped_content)
        escaped_file.close()
        
        try:
            language_code, entries = YMLParser.load_file(escaped_file.name)
            
            entry_dict = {entry['key']: entry['value'] for entry in entries}
            self.assertEqual(entry_dict['test_escape_1'], 'He said "Hello"')
            self.assertEqual(entry_dict['test_escape_2'], 'Line 1\nLine 2')
            
        finally:
            os.unlink(escaped_file.name)
    
    def test_numbered_entries(self):
        """测试带数字的条目"""
        language_code, entries = YMLParser.load_file(self.temp_file.name)
        
        # 查找带数字的条目
        numbered_entry = next((entry for entry in entries if entry['key'] == 'test_key_4'), None)
        self.assertIsNotNone(numbered_entry)
        self.assertEqual(numbered_entry['value'], "This is a numbered entry")
    
    def test_empty_file_handling(self):
        """测试空文件处理"""
        empty_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        empty_file.close()
        
        try:
            language_code, entries = YMLParser.load_file(empty_file.name)
            self.assertIsNone(language_code)
            self.assertEqual(len(entries), 0)
        finally:
            os.unlink(empty_file.name)


if __name__ == '__main__':
    unittest.main()

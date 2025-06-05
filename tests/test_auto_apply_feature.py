#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试自动应用占位符匹配翻译功能
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_manager import ConfigManager
from utils.validation import extract_placeholders


class TestAutoApplyFeature(unittest.TestCase):
    """测试自动应用功能"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时配置文件路径
        self.config_file = "test_config.json"
        self.config_manager = ConfigManager(self.config_file)
        
        # 清理可能存在的测试配置文件
        if os.path.exists(self.config_file):
            os.remove(self.config_file)

    def tearDown(self):
        """清理测试环境"""
        # 清理测试配置文件
        if os.path.exists(self.config_file):
            os.remove(self.config_file)

    def test_config_default_value(self):
        """测试配置项的默认值"""
        # 测试默认值
        auto_apply = self.config_manager.get_setting("auto_apply_when_placeholders_match", False)
        self.assertTrue(auto_apply, "默认应该启用自动应用功能")

    def test_config_setting_and_getting(self):
        """测试配置项的设置和获取"""
        # 设置为False
        self.config_manager.set_setting("auto_apply_when_placeholders_match", False)
        result = self.config_manager.get_setting("auto_apply_when_placeholders_match", True)
        self.assertFalse(result, "设置为False后应该返回False")

        # 设置为True
        self.config_manager.set_setting("auto_apply_when_placeholders_match", True)
        result = self.config_manager.get_setting("auto_apply_when_placeholders_match", False)
        self.assertTrue(result, "设置为True后应该返回True")

    def test_placeholder_extraction(self):
        """测试占位符提取功能"""
        # 测试包含占位符的文本
        text_with_placeholders = "Welcome to [player.GetName] with $MONEY$ coins!"
        placeholders = extract_placeholders(text_with_placeholders)
        
        expected_placeholders = {"[player.GetName]", "$MONEY$"}
        self.assertEqual(placeholders, expected_placeholders, "应该正确提取占位符")

    def test_placeholder_matching(self):
        """测试占位符匹配逻辑"""
        # 测试完全匹配的情况
        original_text = "Welcome to [player.GetName] with $MONEY$ coins!"
        translated_text = "欢迎来到[player.GetName]，你有$MONEY$金币！"
        
        original_placeholders = extract_placeholders(original_text)
        translated_placeholders = extract_placeholders(translated_text)
        
        self.assertEqual(original_placeholders, translated_placeholders, 
                        "占位符应该完全匹配")

    def test_placeholder_mismatch(self):
        """测试占位符不匹配的情况"""
        # 测试不匹配的情况
        original_text = "Welcome to [player.GetName] with $MONEY$ coins!"
        translated_text = "欢迎来到玩家的世界，你有金币！"  # 缺少占位符
        
        original_placeholders = extract_placeholders(original_text)
        translated_placeholders = extract_placeholders(translated_text)
        
        self.assertNotEqual(original_placeholders, translated_placeholders, 
                           "占位符应该不匹配")

    def test_empty_placeholders(self):
        """测试无占位符的情况"""
        # 测试都没有占位符的情况
        original_text = "Hello world!"
        translated_text = "你好世界！"
        
        original_placeholders = extract_placeholders(original_text)
        translated_placeholders = extract_placeholders(translated_text)
        
        self.assertEqual(original_placeholders, translated_placeholders, 
                        "都没有占位符时应该匹配")
        self.assertEqual(len(original_placeholders), 0, "应该没有占位符")

    @patch('main.ModTranslatorApp')
    def test_auto_apply_logic_simulation(self, mock_app):
        """模拟测试自动应用逻辑"""
        # 创建模拟的应用实例
        mock_app_instance = Mock()
        mock_app_instance.config_manager = self.config_manager
        mock_app_instance.log_message = Mock()
        
        # 启用自动应用功能
        self.config_manager.set_setting("auto_apply_when_placeholders_match", True)
        
        # 模拟占位符匹配的情况
        original_text = "Welcome to [player.GetName]!"
        ai_translation = "欢迎来到[player.GetName]！"
        
        original_placeholders = extract_placeholders(original_text)
        translated_placeholders = extract_placeholders(ai_translation)
        
        # 检查是否应该自动应用
        auto_apply_enabled = self.config_manager.get_setting("auto_apply_when_placeholders_match", True)
        should_auto_apply = auto_apply_enabled and original_placeholders == translated_placeholders
        
        self.assertTrue(should_auto_apply, "应该自动应用翻译结果")

    @patch('main.ModTranslatorApp')
    def test_manual_review_logic_simulation(self, mock_app):
        """模拟测试需要人工评审的逻辑"""
        # 创建模拟的应用实例
        mock_app_instance = Mock()
        mock_app_instance.config_manager = self.config_manager
        mock_app_instance.log_message = Mock()
        
        # 启用自动应用功能
        self.config_manager.set_setting("auto_apply_when_placeholders_match", True)
        
        # 模拟占位符不匹配的情况
        original_text = "Welcome to [player.GetName] with $MONEY$!"
        ai_translation = "欢迎来到玩家的世界！"  # 缺少占位符
        
        original_placeholders = extract_placeholders(original_text)
        translated_placeholders = extract_placeholders(ai_translation)
        
        # 检查是否应该自动应用
        auto_apply_enabled = self.config_manager.get_setting("auto_apply_when_placeholders_match", True)
        should_auto_apply = auto_apply_enabled and original_placeholders == translated_placeholders
        
        self.assertFalse(should_auto_apply, "应该需要人工评审")

    def test_disabled_auto_apply(self):
        """测试禁用自动应用功能"""
        # 禁用自动应用功能
        self.config_manager.set_setting("auto_apply_when_placeholders_match", False)
        
        # 即使占位符匹配，也不应该自动应用
        original_text = "Welcome to [player.GetName]!"
        ai_translation = "欢迎来到[player.GetName]！"
        
        original_placeholders = extract_placeholders(original_text)
        translated_placeholders = extract_placeholders(ai_translation)
        
        auto_apply_enabled = self.config_manager.get_setting("auto_apply_when_placeholders_match", True)
        should_auto_apply = auto_apply_enabled and original_placeholders == translated_placeholders
        
        self.assertFalse(should_auto_apply, "禁用时不应该自动应用")


if __name__ == '__main__':
    unittest.main()

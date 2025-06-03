"""
配置管理器测试

测试配置管理器的各种功能
"""

import unittest
import tempfile
import os
import json
from config.config_manager import ConfigManager
from config.constants import DEFAULT_API_KEY_PLACEHOLDER


class TestConfigManager(unittest.TestCase):
    """配置管理器测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时配置文件
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        self.config_manager = ConfigManager(self.temp_file.name)
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时文件
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_default_config_creation(self):
        """测试默认配置创建"""
        # 验证默认配置是否正确加载
        self.assertEqual(self.config_manager.get_setting("source_language"), "english")
        self.assertEqual(self.config_manager.get_setting("target_language"), "simp_chinese")
        self.assertEqual(self.config_manager.get_setting("max_concurrent_tasks"), 3)
        self.assertTrue(self.config_manager.get_setting("auto_review_mode"))
    
    def test_save_and_load_config(self):
        """测试配置保存和加载"""
        # 修改配置
        self.config_manager.set_setting("source_language", "french")
        self.config_manager.set_setting("max_concurrent_tasks", 5)
        
        # 创建新的配置管理器实例来测试加载
        new_config_manager = ConfigManager(self.temp_file.name)
        
        # 验证配置是否正确保存和加载
        self.assertEqual(new_config_manager.get_setting("source_language"), "french")
        self.assertEqual(new_config_manager.get_setting("max_concurrent_tasks"), 5)
    
    def test_api_key_management(self):
        """测试API密钥管理"""
        # 测试添加API密钥
        test_key = "AIzaSyTest123456789012345678901234567"
        self.assertTrue(self.config_manager.add_api_key(test_key))
        
        # 验证密钥是否添加成功
        api_keys = self.config_manager.get_api_keys()
        self.assertIn(test_key, api_keys)
        
        # 测试重复添加
        self.assertFalse(self.config_manager.add_api_key(test_key))
        
        # 测试移除API密钥
        self.assertTrue(self.config_manager.remove_api_key(test_key))
        api_keys = self.config_manager.get_api_keys()
        self.assertNotIn(test_key, api_keys)
    
    def test_api_key_update(self):
        """测试API密钥更新"""
        old_key = "AIzaSyOld123456789012345678901234567"
        new_key = "AIzaSyNew123456789012345678901234567"
        
        # 添加旧密钥
        self.config_manager.add_api_key(old_key)
        
        # 更新密钥
        self.assertTrue(self.config_manager.update_api_key(old_key, new_key))
        
        # 验证更新结果
        api_keys = self.config_manager.get_api_keys()
        self.assertNotIn(old_key, api_keys)
        self.assertIn(new_key, api_keys)
    
    def test_invalid_api_key_handling(self):
        """测试无效API密钥处理"""
        # 测试空密钥
        self.assertFalse(self.config_manager.add_api_key(""))
        self.assertFalse(self.config_manager.add_api_key(None))
        
        # 测试占位符密钥
        self.assertFalse(self.config_manager.add_api_key(DEFAULT_API_KEY_PLACEHOLDER))
    
    def test_legacy_api_key_migration(self):
        """测试旧版API密钥迁移"""
        # 创建包含旧版api_key的配置文件
        legacy_config = {
            "api_key": "AIzaSyLegacy123456789012345678901234",
            "source_language": "english"
        }
        
        with open(self.temp_file.name, 'w') as f:
            json.dump(legacy_config, f)
        
        # 创建新的配置管理器，应该自动迁移
        migrated_config_manager = ConfigManager(self.temp_file.name)
        
        # 验证迁移结果
        api_keys = migrated_config_manager.get_api_keys()
        self.assertIn("AIzaSyLegacy123456789012345678901234", api_keys)
        
        # 验证旧版api_key字段已被移除
        self.assertNotIn("api_key", migrated_config_manager.config)
    
    def test_config_validation(self):
        """测试配置验证"""
        # 测试有效配置
        errors = self.config_manager.validate_config()
        # 默认配置应该有一个错误：没有有效的API密钥
        self.assertEqual(len(errors), 1)
        self.assertIn("未配置有效的API密钥", errors[0])
        
        # 添加有效API密钥后重新验证
        self.config_manager.add_api_key("AIzaSyTest123456789012345678901234567")
        errors = self.config_manager.validate_config()
        self.assertEqual(len(errors), 0)
        
        # 测试无效配置
        self.config_manager.set_setting("max_concurrent_tasks", -1)
        errors = self.config_manager.validate_config()
        self.assertGreater(len(errors), 0)
    
    def test_config_export_import(self):
        """测试配置导出和导入"""
        # 设置一些配置
        self.config_manager.set_setting("source_language", "german")
        self.config_manager.add_api_key("AIzaSyTest123456789012345678901234567")
        
        # 导出配置
        export_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        export_file.close()
        
        try:
            self.assertTrue(self.config_manager.export_config(export_file.name))
            
            # 创建新的配置管理器并导入
            new_config_manager = ConfigManager(tempfile.NamedTemporaryFile().name)
            self.assertTrue(new_config_manager.import_config(export_file.name))
            
            # 验证导入结果
            self.assertEqual(new_config_manager.get_setting("source_language"), "german")
            api_keys = new_config_manager.get_api_keys()
            self.assertIn("AIzaSyTest123456789012345678901234567", api_keys)
            
        finally:
            if os.path.exists(export_file.name):
                os.unlink(export_file.name)
    
    def test_reset_to_defaults(self):
        """测试重置为默认值"""
        # 修改一些配置
        self.config_manager.set_setting("source_language", "french")
        self.config_manager.set_setting("max_concurrent_tasks", 8)
        
        # 重置为默认值
        self.assertTrue(self.config_manager.reset_to_defaults())
        
        # 验证重置结果
        self.assertEqual(self.config_manager.get_setting("source_language"), "english")
        self.assertEqual(self.config_manager.get_setting("max_concurrent_tasks"), 3)


if __name__ == '__main__':
    unittest.main()

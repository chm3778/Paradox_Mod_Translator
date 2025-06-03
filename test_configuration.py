#!/usr/bin/env python3
"""
配置功能测试脚本

测试重构后的配置管理功能
"""

import sys
import os
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config_manager import ConfigManager


def test_basic_config_operations():
    """测试基本配置操作"""
    print("🧪 测试基本配置操作...")
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config_path = f.name
    
    try:
        # 初始化配置管理器
        config_manager = ConfigManager(temp_config_path)
        
        # 测试设置和获取
        config_manager.set_setting("source_language", "english")
        config_manager.set_setting("target_language", "simp_chinese")
        config_manager.set_setting("max_concurrent_tasks", 5)
        config_manager.set_setting("api_call_delay", 2.5)
        
        # 验证设置
        assert config_manager.get_setting("source_language") == "english"
        assert config_manager.get_setting("target_language") == "simp_chinese"
        assert config_manager.get_setting("max_concurrent_tasks") == 5
        assert config_manager.get_setting("api_call_delay") == 2.5
        
        print("✅ 基本配置操作测试通过")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)


def test_api_key_management():
    """测试API密钥管理"""
    print("🧪 测试API密钥管理...")
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config_path = f.name
    
    try:
        config_manager = ConfigManager(temp_config_path)
        
        # 测试添加API密钥
        test_key1 = "AIzaSyTest1234567890123456789012345678"
        test_key2 = "AIzaSyTest2345678901234567890123456789"
        
        assert config_manager.add_api_key(test_key1) == True
        assert config_manager.add_api_key(test_key2) == True
        assert config_manager.add_api_key(test_key1) == False  # 重复添加
        
        # 测试获取API密钥
        keys = config_manager.get_api_keys()
        assert test_key1 in keys
        assert test_key2 in keys
        assert len(keys) == 2
        
        # 测试更新API密钥
        new_key = "AIzaSyTest3456789012345678901234567890"
        assert config_manager.update_api_key(test_key1, new_key) == True
        
        keys = config_manager.get_api_keys()
        assert new_key in keys
        assert test_key1 not in keys
        
        # 测试删除API密钥
        assert config_manager.remove_api_key(new_key) == True
        assert config_manager.remove_api_key(new_key) == False  # 重复删除
        
        keys = config_manager.get_api_keys()
        assert new_key not in keys
        assert len(keys) == 1
        
        print("✅ API密钥管理测试通过")
        
    finally:
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)


def test_config_validation():
    """测试配置验证"""
    print("🧪 测试配置验证...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config_path = f.name
    
    try:
        config_manager = ConfigManager(temp_config_path)
        
        # 设置一些无效配置
        config_manager.set_setting("max_concurrent_tasks", -1)  # 无效值
        config_manager.set_setting("api_call_delay", -5.0)      # 无效值
        
        # 验证配置
        errors = config_manager.validate_config()
        
        # 应该有错误
        assert len(errors) > 0
        print(f"   发现 {len(errors)} 个配置错误（预期）")
        
        # 修正配置
        config_manager.set_setting("max_concurrent_tasks", 3)
        config_manager.set_setting("api_call_delay", 3.0)
        
        # 再次验证
        errors = config_manager.validate_config()
        print(f"   修正后错误数: {len(errors)}")
        
        print("✅ 配置验证测试通过")
        
    finally:
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)


def test_config_export_import():
    """测试配置导出导入"""
    print("🧪 测试配置导出导入...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        export_path = f.name
    
    try:
        # 创建配置
        config_manager = ConfigManager(temp_config_path)
        config_manager.set_setting("source_language", "french")
        config_manager.set_setting("target_language", "german")
        config_manager.add_api_key("AIzaSyTest1234567890123456789012345678")
        
        # 导出配置
        assert config_manager.export_config(export_path) == True
        
        # 验证导出文件
        assert os.path.exists(export_path)
        
        # 创建新的配置管理器并导入
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            new_config_path = f.name
        
        new_config_manager = ConfigManager(new_config_path)
        assert new_config_manager.import_config(export_path) == True
        
        # 验证导入的配置
        assert new_config_manager.get_setting("source_language") == "french"
        assert new_config_manager.get_setting("target_language") == "german"
        
        keys = new_config_manager.get_api_keys()
        assert "AIzaSyTest1234567890123456789012345678" in keys
        
        print("✅ 配置导出导入测试通过")
        
        # 清理新配置文件
        if os.path.exists(new_config_path):
            os.unlink(new_config_path)
        
    finally:
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)
        if os.path.exists(export_path):
            os.unlink(export_path)


def test_legacy_migration():
    """测试旧版配置迁移"""
    print("🧪 测试旧版配置迁移...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config_path = f.name
        
        # 创建旧版配置格式
        legacy_config = {
            "api_key": "AIzaSyLegacy123456789012345678901234",
            "source_language": "english",
            "target_language": "japanese"
        }
        
        json.dump(legacy_config, f, indent=4)
    
    try:
        # 加载配置（应该触发迁移）
        config_manager = ConfigManager(temp_config_path)
        
        # 验证迁移结果
        keys = config_manager.get_api_keys()
        assert "AIzaSyLegacy123456789012345678901234" in keys
        
        # 验证旧的api_key字段已被移除
        config = config_manager.config
        assert "api_key" not in config
        assert "api_keys" in config
        
        print("✅ 旧版配置迁移测试通过")
        
    finally:
        if os.path.exists(temp_config_path):
            os.unlink(temp_config_path)


def main():
    """运行所有测试"""
    print("🧪 Paradox Mod Translator - 配置功能测试")
    print("=" * 50)
    
    try:
        test_basic_config_operations()
        test_api_key_management()
        test_config_validation()
        test_config_export_import()
        test_legacy_migration()
        
        print("\n" + "=" * 50)
        print("🎉 所有配置功能测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

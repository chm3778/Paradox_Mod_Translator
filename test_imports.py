#!/usr/bin/env python3
"""
导入测试脚本

测试所有必要的模块是否能够正常导入
专门用于CI/CD环境的快速验证
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_core_imports():
    """测试核心依赖导入"""
    print("Testing core dependencies...")
    
    try:
        import google.generativeai
        print("  google.generativeai: OK")
    except ImportError as e:
        print(f"  google.generativeai: FAILED - {e}")
        return False
    
    try:
        import ttkbootstrap
        print("  ttkbootstrap: OK")
    except ImportError as e:
        print(f"  ttkbootstrap: FAILED - {e}")
        return False
    
    return True


def test_tkinter_imports():
    """测试tkinter相关导入"""
    print("Testing tkinter modules...")
    
    modules = [
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.simpledialog'
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"  {module}: OK")
        except ImportError as e:
            print(f"  {module}: FAILED - {e}")
            return False
    
    return True


def test_project_modules():
    """测试项目模块导入"""
    print("Testing project modules...")
    
    modules = [
        'config.constants',
        'config.config_manager',
        'parsers.yml_parser',
        'core.api_key_manager',
        'core.parallel_translator',
        'utils.logging_utils'
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"  {module}: OK")
        except ImportError as e:
            print(f"  {module}: FAILED - {e}")
            return False
    
    return True


def main():
    """主函数"""
    print("Paradox Mod Translator - Import Test")
    print("=" * 40)
    
    success = True
    
    # 测试核心依赖
    if not test_core_imports():
        success = False
    
    print()
    
    # 测试tkinter模块
    if not test_tkinter_imports():
        success = False
    
    print()
    
    # 测试项目模块
    if not test_project_modules():
        success = False
    
    print()
    print("=" * 40)
    
    if success:
        print("All imports successful!")
        sys.exit(0)
    else:
        print("Some imports failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

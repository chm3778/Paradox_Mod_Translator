#!/usr/bin/env python3
"""导入测试脚本，专门用于CI/CD环境中快速验证所有必要模块是否能导入"""

import sys
import os
import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_core_imports():
    """测试核心依赖导入"""
    print("Testing core dependencies...")

    try:
        __import__("google.generativeai")
        print("  google.generativeai: OK")
    except ImportError:
        pytest.skip("google.generativeai not installed")

    try:
        __import__("ttkbootstrap")
        print("  ttkbootstrap: OK")
    except ImportError:
        pytest.skip("ttkbootstrap not installed")


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
            assert False, f"{module} import failed: {e}"


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
            assert False, f"{module} import failed: {e}"


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

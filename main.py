#!/usr/bin/env python3
"""
Paradox Mod Translator - 主程序

一个专门用于翻译Paradox游戏Mod本地化文件的工具
使用Google Gemini API进行智能翻译

注意：此文件已被重构，主要功能已移至 main_refactored.py
此文件保留用于向后兼容
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """主函数 - 重定向到重构版本"""
    print("🔄 正在启动重构版本...")

    try:
        # 导入并运行重构版本
        from main_refactored import main as refactored_main
        refactored_main()
    except ImportError as e:
        print(f"❌ 无法导入重构版本: {e}")
        print("请确保所有依赖模块都已正确安装")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 运行时错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
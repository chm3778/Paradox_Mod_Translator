#!/usr/bin/env python3
"""
Paradox Mod Translator 启动脚本

这个脚本提供了一个友好的启动界面，包括依赖检查和错误处理
"""

import sys
import os
import subprocess
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print(f"   当前版本: {sys.version}")
        return False
    print(f"✅ Python版本: {sys.version.split()[0]}")
    return True


def check_dependencies():
    """检查必需的依赖包"""
    required_packages = [
        ('google.generativeai', 'google-generativeai'),
        ('ttkbootstrap', 'ttkbootstrap'),
    ]
    
    missing_packages = []
    
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} (未安装)")
            missing_packages.append(package_name)
    
    return missing_packages


def install_dependencies(packages):
    """安装缺失的依赖包"""
    print("\n🔧 正在安装缺失的依赖包...")
    
    for package in packages:
        print(f"   安装 {package}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   ✅ {package} 安装成功")
        except subprocess.CalledProcessError:
            print(f"   ❌ {package} 安装失败")
            return False
    
    return True


def check_config_file():
    """检查配置文件"""
    config_file = Path("translator_config.json")
    if config_file.exists():
        print("✅ 配置文件存在")
        return True
    else:
        print("ℹ️  配置文件不存在，将使用默认配置创建")
        return True


def start_application():
    """启动应用程序"""
    print("\n🚀 启动 Paradox Mod Translator...")
    
    try:
        # 尝试启动重构后的版本
        if Path("main_refactored.py").exists():
            subprocess.run([sys.executable, "main_refactored.py"])
        # 如果重构版本不存在，尝试原版本
        elif Path("main.py").exists():
            subprocess.run([sys.executable, "main.py"])
        else:
            print("❌ 错误: 找不到主程序文件")
            return False
            
    except KeyboardInterrupt:
        print("\n👋 用户取消启动")
        return True
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False
    
    return True


def show_help():
    """显示帮助信息"""
    help_text = """
🎮 Paradox Mod Translator 使用指南

📋 功能特性:
   • 支持多种Paradox游戏的本地化文件翻译
   • 使用Google Gemini AI进行智能翻译
   • 支持多API密钥负载均衡
   • 提供翻译质量评审功能
   • 支持并行翻译提高效率

🔧 系统要求:
   • Python 3.8+
   • google-generativeai 包
   • ttkbootstrap 包

📖 使用步骤:
   1. 配置Google Gemini API密钥
   2. 选择源语言和目标语言
   3. 选择要翻译的YML文件
   4. 开始翻译并评审结果

🆘 获取帮助:
   • 查看 README.md 文件
   • 查看 REFACTORING_REPORT.md 了解架构
   • 运行测试: python run_tests.py

📧 问题反馈:
   如遇到问题，请检查日志文件或联系开发者
"""
    print(help_text)


def main():
    """主函数"""
    print("=" * 60)
    print("🎮 Paradox Mod Translator - 启动器")
    print("=" * 60)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help', 'help']:
            show_help()
            return
        elif sys.argv[1] in ['-v', '--version', 'version']:
            print("版本: 2.0.0 (重构版)")
            return
    
    # 检查Python版本
    print("\n🔍 检查系统环境...")
    if not check_python_version():
        input("按Enter键退出...")
        return
    
    # 检查依赖包
    print("\n📦 检查依赖包...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"\n⚠️  发现 {len(missing_packages)} 个缺失的依赖包")
        response = input("是否自动安装? (y/N): ").strip().lower()
        
        if response in ['y', 'yes', '是']:
            if not install_dependencies(missing_packages):
                print("❌ 依赖安装失败，请手动安装:")
                print(f"   pip install {' '.join(missing_packages)}")
                input("按Enter键退出...")
                return
        else:
            print("请手动安装依赖包:")
            print(f"   pip install {' '.join(missing_packages)}")
            input("按Enter键退出...")
            return
    
    # 检查配置文件
    print("\n⚙️  检查配置...")
    check_config_file()
    
    # 启动应用程序
    if not start_application():
        input("按Enter键退出...")
        return
    
    print("\n👋 感谢使用 Paradox Mod Translator!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户取消操作")
    except Exception as e:
        print(f"\n❌ 启动器发生错误: {e}")
        input("按Enter键退出...")

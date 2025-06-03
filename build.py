#!/usr/bin/env python3
"""
本地构建脚本

用于在本地测试PyInstaller构建过程
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


def get_platform_info():
    """获取平台信息"""
    system = platform.system().lower()
    if system == "windows":
        return "windows", "windows.spec", ".exe"
    elif system == "darwin":
        return "macos", "macos.spec", ""
    elif system == "linux":
        return "linux", "linux.spec", ""
    else:
        raise ValueError(f"不支持的平台: {system}")


def check_dependencies():
    """检查构建依赖"""
    print("🔍 检查构建依赖...")
    
    try:
        import PyInstaller
        print(f"✅ PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller 未安装")
        print("请运行: pip install pyinstaller")
        return False
    
    try:
        import google.generativeai
        print("✅ google-generativeai")
    except ImportError:
        print("❌ google-generativeai 未安装")
        return False
    
    try:
        import ttkbootstrap
        print("✅ ttkbootstrap")
    except ImportError:
        print("❌ ttkbootstrap 未安装")
        return False
    
    return True


def run_tests():
    """运行测试"""
    print("\n🧪 运行测试...")
    
    try:
        result = subprocess.run([sys.executable, "run_tests.py"], 
                              capture_output=True, text=True, check=True)
        print("✅ 所有测试通过")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试失败: {e}")
        print(f"输出: {e.stdout}")
        print(f"错误: {e.stderr}")
        return False


def build_application():
    """构建应用程序"""
    platform_name, spec_file, exe_suffix = get_platform_info()
    
    print(f"\n🔧 为 {platform_name} 平台构建应用程序...")
    
    # 清理之前的构建
    if os.path.exists("build"):
        shutil.rmtree("build")
        print("🧹 清理 build 目录")
    
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("🧹 清理 dist 目录")
    
    # 运行PyInstaller
    spec_path = Path("build-config") / spec_file
    
    try:
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_path)]
        print(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True)
        print("✅ 构建成功")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        return False


def create_release_package():
    """创建发布包"""
    platform_name, _, _ = get_platform_info()
    
    print(f"\n📦 创建 {platform_name} 发布包...")
    
    # 创建发布目录
    release_dir = Path("release")
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # 复制构建结果
    dist_dir = Path("dist/ParadoxModTranslator")
    if not dist_dir.exists():
        print(f"❌ 构建目录不存在: {dist_dir}")
        return False
    
    # 复制所有文件
    for item in dist_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, release_dir)
        else:
            shutil.copytree(item, release_dir / item.name)
    
    # 复制文档
    docs = ["README.md", "CONFIGURATION_GUIDE.md"]
    for doc in docs:
        if Path(doc).exists():
            shutil.copy2(doc, release_dir)
    
    # 创建构建信息
    build_info = release_dir / "BUILD_INFO.txt"
    with open(build_info, "w", encoding="utf-8") as f:
        f.write(f"构建平台: {platform_name}\n")
        f.write(f"构建时间: {subprocess.check_output(['date'], text=True).strip()}\n")
        f.write(f"Python版本: {sys.version}\n")
        f.write(f"PyInstaller版本: {subprocess.check_output([sys.executable, '-c', 'import PyInstaller; print(PyInstaller.__version__)'], text=True).strip()}\n")
    
    print(f"✅ 发布包已创建: {release_dir}")
    
    # 列出文件
    print("\n📁 发布包内容:")
    for item in sorted(release_dir.rglob("*")):
        if item.is_file():
            size = item.stat().st_size
            print(f"  {item.relative_to(release_dir)} ({size:,} bytes)")
    
    return True


def main():
    """主函数"""
    print("🏗️ Paradox Mod Translator - 本地构建脚本")
    print("=" * 50)
    
    # 检查当前目录
    if not Path("main.py").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请安装缺失的依赖")
        sys.exit(1)
    
    # 运行测试
    if not run_tests():
        print("\n❌ 测试失败，请修复问题后重试")
        response = input("是否继续构建? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    
    # 构建应用程序
    if not build_application():
        print("\n❌ 构建失败")
        sys.exit(1)
    
    # 创建发布包
    if not create_release_package():
        print("\n❌ 创建发布包失败")
        sys.exit(1)
    
    print("\n🎉 构建完成！")
    print("发布包位置: release/")
    print("\n使用说明:")
    print("1. 进入 release/ 目录")
    print("2. 运行 ParadoxModTranslator 可执行文件")
    print("3. 首次运行时配置 Google Gemini API 密钥")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
本地代码质量检查脚本

运行与CI/CD流水线相同的代码质量检查，帮助开发者在提交前发现问题。
"""

import subprocess
import sys
import os
import time
from pathlib import Path


def run_command(command, description, critical=True):
    """运行命令并处理结果"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")
    print(f"运行命令: {' '.join(command)}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True,
            cwd=Path(__file__).parent
        )
        
        duration = time.time() - start_time
        print(f"✅ {description} 通过 ({duration:.2f}s)")
        
        if result.stdout:
            print("输出:")
            print(result.stdout)
            
        return True
        
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        print(f"❌ {description} 失败 ({duration:.2f}s)")
        
        if e.stdout:
            print("标准输出:")
            print(e.stdout)
            
        if e.stderr:
            print("错误输出:")
            print(e.stderr)
            
        if critical:
            return False
        else:
            print("⚠️ 非关键检查失败，继续执行...")
            return True
    
    except FileNotFoundError:
        print(f"❌ 命令未找到: {command[0]}")
        print("请确保已安装所有开发依赖: pip install -r requirements-dev.txt")
        return False


def check_dependencies():
    """检查必要的依赖是否已安装"""
    print("🔍 检查开发依赖...")
    
    required_tools = [
        ("black", "代码格式化"),
        ("flake8", "代码风格检查"),
        ("isort", "导入排序"),
        ("mypy", "类型检查"),
        ("bandit", "安全检查"),
        ("pytest", "测试框架"),
    ]
    
    missing_tools = []
    
    for tool, description in required_tools:
        try:
            subprocess.run([tool, "--version"], 
                         capture_output=True, check=True)
            print(f"✅ {tool} ({description})")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {tool} ({description}) - 未安装")
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"\n❌ 缺少以下工具: {', '.join(missing_tools)}")
        print("请运行: pip install -r requirements-dev.txt")
        return False
    
    print("✅ 所有开发依赖已安装")
    return True


def main():
    """主函数"""
    print("🚀 Paradox Mod Translator - 本地代码质量检查")
    print("=" * 60)
    
    # 检查是否在项目根目录
    if not Path("main.py").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 定义检查列表
    checks = [
        # 代码格式化检查
        (["black", "--check", "--diff", "."], "Black代码格式检查", True),
        
        # 导入排序检查
        (["isort", "--check-only", "--diff", "."], "isort导入排序检查", True),
        
        # 代码风格检查
        (["flake8", "."], "Flake8代码风格检查", True),
        
        # 类型检查
        (["mypy", ".", "--ignore-missing-imports"], "MyPy类型检查", False),
        
        # 安全检查
        (["bandit", "-r", ".", "-f", "txt"], "Bandit安全检查", False),
        
        # 运行测试
        (["python", "test_imports.py"], "导入测试", True),
        (["python", "run_tests.py"], "单元测试", True),
        (["python", "test_configuration.py"], "配置测试", True),
    ]
    
    # 如果安装了pytest，使用pytest运行测试
    try:
        subprocess.run(["pytest", "--version"], capture_output=True, check=True)
        # 替换测试命令
        checks = [c for c in checks if "run_tests.py" not in c[0]]
        checks.append((["pytest", "tests/", "-v", "--tb=short"], "Pytest单元测试", True))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # 运行所有检查
    failed_checks = []
    total_checks = len(checks)
    
    for i, (command, description, critical) in enumerate(checks, 1):
        print(f"\n[{i}/{total_checks}] 正在运行: {description}")
        
        if not run_command(command, description, critical):
            failed_checks.append(description)
            if critical:
                print(f"\n❌ 关键检查失败: {description}")
                break
    
    # 总结结果
    print(f"\n{'='*60}")
    print("📊 检查结果总结")
    print(f"{'='*60}")
    
    if failed_checks:
        print(f"❌ 失败的检查 ({len(failed_checks)}):")
        for check in failed_checks:
            print(f"  - {check}")
        
        print(f"\n💡 建议:")
        print("1. 运行 'black .' 自动格式化代码")
        print("2. 运行 'isort .' 自动排序导入")
        print("3. 查看上述错误信息并修复相关问题")
        print("4. 重新运行此脚本验证修复")
        
        sys.exit(1)
    else:
        print("✅ 所有检查通过!")
        print("\n🎉 代码已准备好提交!")
        print("\n💡 下一步:")
        print("1. git add .")
        print("2. git commit -m 'your commit message'")
        print("3. git push")


if __name__ == "__main__":
    main()

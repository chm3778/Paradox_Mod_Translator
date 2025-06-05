#!/usr/bin/env python3
"""
GitHub Actions工作流优化验证脚本

验证所有新增的配置文件和工作流是否正确设置。
"""

import os
import sys
import yaml
from pathlib import Path


def check_file_exists(file_path, description):
    """检查文件是否存在"""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - 文件不存在")
        return False


def check_yaml_syntax(file_path, description):
    """检查YAML文件语法"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        print(f"✅ {description}: YAML语法正确")
        return True
    except yaml.YAMLError as e:
        print(f"❌ {description}: YAML语法错误 - {e}")
        return False
    except Exception as e:
        print(f"❌ {description}: 文件读取错误 - {e}")
        return False


def check_workflow_structure():
    """检查工作流结构"""
    workflow_file = ".github/workflows/test.yml"
    
    if not Path(workflow_file).exists():
        print(f"❌ 工作流文件不存在: {workflow_file}")
        return False
    
    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow = yaml.safe_load(f)
        
        # 检查必要的作业
        required_jobs = [
            'code-quality',
            'dependency-security', 
            'test',
            'build-test',
            'performance-test',
            'final-status'
        ]
        
        jobs = workflow.get('jobs', {})
        missing_jobs = []
        
        for job in required_jobs:
            if job in jobs:
                print(f"✅ 作业存在: {job}")
            else:
                print(f"❌ 作业缺失: {job}")
                missing_jobs.append(job)
        
        if missing_jobs:
            print(f"❌ 缺失的作业: {', '.join(missing_jobs)}")
            return False
        
        print("✅ 所有必要的作业都已配置")
        return True
        
    except Exception as e:
        print(f"❌ 工作流文件解析错误: {e}")
        return False


def main():
    """主验证函数"""
    print("🔍 GitHub Actions工作流优化验证")
    print("=" * 50)
    
    # 检查是否在项目根目录
    if not Path("main.py").exists():
        print("❌ 请在项目根目录运行此脚本")
        sys.exit(1)
    
    all_checks_passed = True
    
    # 1. 检查配置文件
    print("\n📁 检查配置文件...")
    config_files = [
        ("pytest.ini", "Pytest配置文件"),
        ("pyproject.toml", "项目配置文件"),
        (".flake8", "Flake8配置文件"),
        ("conftest.py", "Pytest夹具配置"),
    ]
    
    for file_path, description in config_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # 2. 检查GitHub配置
    print("\n🐙 检查GitHub配置...")
    github_files = [
        (".github/workflows/test.yml", "主要工作流文件"),
        (".github/CODEOWNERS", "代码所有者配置"),
        (".github/pull_request_template.md", "PR模板"),
    ]
    
    for file_path, description in github_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # 3. 检查工具脚本
    print("\n🛠️ 检查工具脚本...")
    tool_files = [
        ("run_quality_checks.py", "本地质量检查脚本"),
        ("verify_optimization.py", "优化验证脚本"),
    ]
    
    for file_path, description in tool_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # 4. 检查文档
    print("\n📚 检查文档...")
    doc_files = [
        ("CI_CD_GUIDE.md", "CI/CD指南"),
        ("OPTIMIZATION_SUMMARY.md", "优化总结"),
    ]
    
    for file_path, description in doc_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    # 5. 检查YAML语法
    print("\n🔍 检查YAML语法...")
    yaml_files = [
        (".github/workflows/test.yml", "主要工作流"),
        (".github/workflows/build-release.yml", "发布工作流"),
    ]
    
    for file_path, description in yaml_files:
        if Path(file_path).exists():
            if not check_yaml_syntax(file_path, description):
                all_checks_passed = False
    
    # 6. 检查工作流结构
    print("\n⚙️ 检查工作流结构...")
    if not check_workflow_structure():
        all_checks_passed = False
    
    # 7. 检查依赖文件
    print("\n📦 检查依赖文件...")
    
    # 检查requirements-dev.txt是否包含新工具
    if Path("requirements-dev.txt").exists():
        with open("requirements-dev.txt", 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_tools = [
            'pytest-xdist',
            'pytest-timeout', 
            'pip-audit',
            'safety',
            'psutil'
        ]
        
        missing_tools = []
        for tool in required_tools:
            if tool in content:
                print(f"✅ 开发依赖包含: {tool}")
            else:
                print(f"❌ 开发依赖缺失: {tool}")
                missing_tools.append(tool)
                all_checks_passed = False
        
        if not missing_tools:
            print("✅ 所有必要的开发工具都已包含")
    
    # 总结
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 所有验证检查通过！")
        print("\n✅ GitHub Actions工作流优化已成功完成")
        print("\n📋 下一步:")
        print("1. 提交所有更改到Git")
        print("2. 创建Pull Request测试新的工作流")
        print("3. 查看CI/CD_GUIDE.md了解详细使用说明")
        print("4. 运行 python run_quality_checks.py 进行本地验证")
    else:
        print("❌ 部分验证检查失败")
        print("请检查上述错误并修复相关问题")
        sys.exit(1)


if __name__ == "__main__":
    main()

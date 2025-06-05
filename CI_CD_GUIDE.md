# CI/CD 流程指南

本文档描述了Paradox Mod Translator项目的持续集成和持续部署(CI/CD)流程。

## 🔄 工作流概述

我们的CI/CD流程包含以下几个主要阶段：

### 1. 代码质量检查 (Code Quality)
- **代码格式化**: 使用Black检查代码格式
- **导入排序**: 使用isort检查导入语句排序
- **代码风格**: 使用Flake8进行代码风格检查
- **类型检查**: 使用MyPy进行静态类型检查
- **安全扫描**: 使用Bandit进行安全漏洞检查

### 2. 依赖安全扫描 (Dependency Security)
- **pip-audit**: 检查Python包的已知安全漏洞
- **Safety**: 额外的依赖安全检查

### 3. 多平台测试 (Multi-platform Testing)
- **平台支持**: Ubuntu, Windows, macOS
- **Python版本**: 3.9, 3.10, 3.11, 3.12
- **测试覆盖率**: 要求最低60%的代码覆盖率
- **并行测试**: 使用pytest-xdist加速测试执行

### 4. 构建验证 (Build Verification)
- **PyInstaller构建**: 在所有平台上测试可执行文件构建
- **启动测试**: 验证构建的可执行文件能够正常启动
- **构建产物**: 自动上传构建产物供下载

### 5. 性能测试 (Performance Testing)
- **内存使用**: 检查应用程序内存使用情况
- **导入性能**: 测试模块导入时间
- **启动时间**: 验证应用启动性能

## 🚀 触发条件

CI/CD流程在以下情况下自动触发：

- **Push到主分支**: `main`, `develop`
- **Pull Request**: 针对`main`分支的PR
- **手动触发**: 通过GitHub Actions界面

## 📋 检查要求

### 必须通过的检查 (Required)
以下检查必须通过，否则PR无法合并：

- ✅ 代码质量检查
- ✅ 单元测试
- ✅ 构建测试

### 建议通过的检查 (Recommended)
以下检查失败不会阻止PR合并，但会发出警告：

- ⚠️ 依赖安全扫描
- ⚠️ 性能测试
- ⚠️ 类型检查

## 🛠️ 本地开发

### 安装开发依赖

```bash
# 安装开发工具
pip install -r requirements-dev.txt
```

### 运行本地检查

```bash
# 运行所有质量检查
python run_quality_checks.py

# 或者单独运行各项检查
black --check .          # 代码格式检查
isort --check-only .      # 导入排序检查
flake8 .                  # 代码风格检查
mypy .                    # 类型检查
bandit -r .               # 安全检查
pytest                    # 运行测试
```

### 自动修复

```bash
# 自动格式化代码
black .

# 自动排序导入
isort .
```

## 📊 测试覆盖率

项目要求最低60%的测试覆盖率。覆盖率报告会自动生成并上传到CI artifacts。

### 查看覆盖率报告

1. 本地运行: `pytest --cov=. --cov-report=html`
2. 打开 `htmlcov/index.html` 查看详细报告

### 提高覆盖率

- 为新功能添加单元测试
- 为边界条件添加测试用例
- 测试错误处理路径

## 🔒 安全检查

### Bandit安全扫描
检查常见的安全问题：
- 硬编码密码
- SQL注入风险
- 不安全的随机数生成
- 不安全的临时文件使用

### 依赖安全扫描
- **pip-audit**: 检查已知CVE漏洞
- **Safety**: 检查安全数据库

## 🏗️ 构建流程

### PyInstaller配置
- **Windows**: 生成 `.exe` 文件
- **Linux/macOS**: 生成可执行二进制文件
- **参数**: `--onefile --windowed`

### 构建验证
- 检查可执行文件是否生成
- 验证文件大小合理
- 测试基本启动功能

## 📈 性能监控

### 内存使用监控
- 启动时内存使用 < 200MB
- 模块导入内存增长监控

### 导入性能
- 所有模块导入时间 < 5秒
- 关键模块导入时间监控

## 🔧 配置文件

### pytest配置 (`pytest.ini`)
- 测试发现规则
- 覆盖率配置
- 标记定义

### 代码质量配置
- **Black**: `pyproject.toml`
- **isort**: `pyproject.toml`
- **Flake8**: `.flake8`
- **MyPy**: `pyproject.toml`
- **Bandit**: `pyproject.toml`

## 🚨 故障排除

### 常见问题

1. **代码格式检查失败**
   ```bash
   black .  # 自动修复
   ```

2. **导入排序检查失败**
   ```bash
   isort .  # 自动修复
   ```

3. **测试失败**
   ```bash
   pytest -v  # 查看详细错误信息
   ```

4. **构建失败**
   - 检查依赖是否正确安装
   - 查看PyInstaller日志

### 获取帮助

- 查看GitHub Actions日志
- 运行本地检查脚本
- 检查相关配置文件

## 📝 贡献指南

1. **提交前检查**
   ```bash
   python run_quality_checks.py
   ```

2. **创建PR**
   - 使用PR模板
   - 确保所有检查通过
   - 添加适当的测试

3. **代码审查**
   - 等待自动检查完成
   - 响应审查意见
   - 保持代码质量

## 🔄 持续改进

我们持续改进CI/CD流程：

- 监控构建时间和成功率
- 优化测试执行速度
- 增强安全检查覆盖
- 改进错误报告质量

---

如有问题或建议，请创建Issue或联系维护者。

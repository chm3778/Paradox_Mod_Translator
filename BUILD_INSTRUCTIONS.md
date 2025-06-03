# 🏗️ Paradox Mod Translator 构建说明

本文档详细说明如何使用GitHub Actions自动构建和发布Paradox Mod Translator。

## 🚀 自动发布流程

### 1. 触发构建

有两种方式触发自动构建：

#### 方式一：推送版本标签（推荐）
```bash
# 1. 确保所有更改已提交
git add .
git commit -m "准备发布 v1.0.0"
git push origin main

# 2. 创建并推送版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

#### 方式二：手动触发
1. 访问 GitHub 仓库页面
2. 点击 "Actions" 选项卡
3. 选择 "🚀 Build and Release" 工作流
4. 点击 "Run workflow"
5. 输入版本号（如 v1.0.0）
6. 点击 "Run workflow" 按钮

### 2. 构建过程

GitHub Actions 将自动执行以下步骤：

1. **环境准备**
   - 在 Windows、Linux、macOS 三个平台上设置 Python 3.11
   - 安装项目依赖

2. **质量检查**
   - 运行所有单元测试
   - 验证配置功能

3. **应用构建**
   - 使用 PyInstaller 构建可执行文件
   - 为每个平台创建优化的构建配置

4. **打包发布**
   - 创建压缩包（Windows/macOS: .zip, Linux: .tar.gz）
   - 包含可执行文件、文档和构建信息

5. **自动发布**
   - 创建 GitHub Release
   - 上传所有平台的构建包
   - 生成详细的发布说明

### 3. 构建结果

构建完成后，将在 GitHub Releases 页面看到：

- **Paradox-Mod-Translator-Windows.zip** - Windows 可执行文件
- **Paradox-Mod-Translator-Linux.tar.gz** - Linux 可执行文件  
- **Paradox-Mod-Translator-macOS.zip** - macOS 应用程序包

## 🔧 本地构建

### 安装构建依赖
```bash
# 安装完整依赖（包括 PyInstaller）
pip install -r requirements.txt
```

### 运行本地构建
```bash
# 使用构建脚本
python build.py
```

### 手动构建
```bash
# Windows
pyinstaller --clean --noconfirm build-config/windows.spec

# Linux
pyinstaller --clean --noconfirm build-config/linux.spec

# macOS
pyinstaller --clean --noconfirm build-config/macos.spec
```

## ⚙️ 构建配置

### PyInstaller 配置文件

项目包含三个平台特定的 spec 文件：

- `build-config/windows.spec` - Windows 配置
- `build-config/linux.spec` - Linux 配置
- `build-config/macos.spec` - macOS 配置

### 关键配置项

#### 隐藏导入模块
```python
hiddenimports = [
    'google.generativeai',
    'ttkbootstrap',
    'tkinter',
    # ... 其他必需模块
]
```

#### 数据文件包含
```python
datas = [
    ('config', 'config'),
    ('core', 'core'),
    ('parsers', 'parsers'),
    # ... 其他模块目录
]
```

#### 排除模块
```python
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    # ... 不需要的大型库
]
```

## 🐛 故障排除

### 常见构建问题

#### 1. 模块导入错误
**症状**: `ModuleNotFoundError` 在运行时出现
**解决**: 将缺失模块添加到 `hiddenimports` 列表

#### 2. 文件缺失错误
**症状**: 运行时找不到配置文件或资源
**解决**: 检查 `datas` 配置，确保包含所有必需文件

#### 3. 构建包过大
**症状**: 生成的可执行文件体积过大
**解决**: 
- 添加不需要的库到 `excludes` 列表
- 启用 UPX 压缩
- 检查是否包含了不必要的数据文件

#### 4. 平台特定问题

**Windows**:
- 确保设置 `console=False` 用于 GUI 应用
- 可能需要管理员权限运行

**Linux**:
- 检查依赖库兼容性
- 确保目标系统有必要的系统库

**macOS**:
- 验证应用程序包配置
- 检查代码签名要求

### GitHub Actions 问题

#### 1. 构建超时
**解决**: 增加 `max_wait_seconds` 值或优化构建配置

#### 2. 权限错误
**解决**: 检查 `GITHUB_TOKEN` 权限设置

#### 3. 依赖安装失败
**解决**: 
- 检查 `requirements.txt` 文件
- 验证包版本兼容性
- 考虑使用缓存加速安装

## 📊 构建优化

### 减少构建时间
1. **使用缓存**: GitHub Actions 自动缓存 pip 依赖
2. **并行构建**: 多平台同时构建
3. **增量构建**: 只在代码变更时重新构建

### 减少包大小
1. **排除不需要的模块**: 更新 `excludes` 列表
2. **启用压缩**: 使用 UPX 压缩
3. **优化资源**: 只包含必需的数据文件

### 提高构建质量
1. **自动测试**: 构建前运行完整测试套件
2. **多版本测试**: 在多个 Python 版本上测试
3. **跨平台验证**: 确保在所有目标平台上正常工作

## 📋 发布检查清单

发布前请确认：

- [ ] 所有测试通过
- [ ] 版本号已更新
- [ ] 文档已更新
- [ ] 构建配置正确
- [ ] 本地构建测试成功
- [ ] GitHub Actions 权限正确

## 🔄 版本管理

### 版本号规范
使用语义化版本控制：`v主版本.次版本.修订版`

- **主版本**: 不兼容的 API 修改
- **次版本**: 向下兼容的功能性新增  
- **修订版**: 向下兼容的问题修正

### 标签命名
- 正式版本: `v1.0.0`
- 预发布版: `v1.0.0-beta.1`
- 候选版本: `v1.0.0-rc.1`

通过遵循这些说明，您可以轻松地为 Paradox Mod Translator 创建专业的自动化构建和发布流程！

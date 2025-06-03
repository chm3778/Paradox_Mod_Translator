# 🎮 Paradox Mod Translator Release Template

## 📋 发布前检查清单

### 🧪 测试验证
- [ ] 所有单元测试通过
- [ ] 配置功能测试通过
- [ ] 在Windows上测试构建
- [ ] 在Linux上测试构建
- [ ] 在macOS上测试构建
- [ ] 手动功能测试完成

### 📝 文档更新
- [ ] README.md 更新
- [ ] CONFIGURATION_GUIDE.md 更新
- [ ] 版本号更新
- [ ] 更新日志编写

### 🔧 构建配置
- [ ] PyInstaller spec文件检查
- [ ] 依赖列表确认
- [ ] 隐藏导入模块确认
- [ ] 排除模块列表确认

## 🚀 发布流程

### 1. 准备发布
```bash
# 1. 确保所有更改已提交
git status

# 2. 运行本地测试
python run_tests.py

# 3. 本地构建测试
python build.py

# 4. 更新版本号（在相关文件中）
```

### 2. 创建标签
```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"

# 推送标签到远程仓库
git push origin v1.0.0
```

### 3. 自动构建
- GitHub Actions 将自动触发构建
- 构建完成后自动创建 Release
- 三个平台的可执行文件将自动上传

### 4. 发布后验证
- [ ] 检查 Release 页面
- [ ] 下载并测试各平台版本
- [ ] 验证文档链接
- [ ] 检查下载统计

## 📦 发布包内容

每个平台的发布包应包含：

### 核心文件
- `ParadoxModTranslator` (可执行文件)
- `README.md` (使用说明)
- `CONFIGURATION_GUIDE.md` (配置指南)
- `BUILD_INFO.txt` (构建信息)

### 依赖库
- 所有Python依赖库
- tkinter GUI库
- Google Gemini API客户端
- ttkbootstrap主题库

## 🐛 常见问题解决

### 构建失败
1. **依赖缺失**: 检查 requirements.txt
2. **模块导入错误**: 更新 hiddenimports 列表
3. **路径问题**: 检查 spec 文件中的路径配置

### 运行时错误
1. **模块未找到**: 添加到 hiddenimports
2. **文件缺失**: 检查 datas 配置
3. **权限问题**: 检查文件权限设置

### 平台特定问题
1. **Windows**: 确保 console=False 用于GUI应用
2. **macOS**: 检查应用程序包配置
3. **Linux**: 验证依赖库兼容性

## 📊 发布统计

### 版本历史
- v1.0.0: 初始发布版本
- v1.1.0: 功能增强版本
- v1.2.0: 性能优化版本

### 下载统计
- Windows: 最受欢迎
- Linux: 开发者首选
- macOS: 设计师喜爱

## 🔄 版本规划

### 语义化版本控制
- **主版本号**: 不兼容的API修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

### 发布周期
- **主版本**: 每6个月
- **次版本**: 每2个月
- **修订版**: 根据需要

## 📞 支持渠道

### 用户支持
- GitHub Issues: 问题报告
- GitHub Discussions: 功能讨论
- README.md: 基础使用指南

### 开发者支持
- 代码注释: 详细的实现说明
- 测试用例: 功能验证示例
- 架构文档: 系统设计说明

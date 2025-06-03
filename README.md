# 🎮 Paradox Mod Translator

一个专门用于翻译Paradox游戏Mod本地化文件的智能工具，使用Google Gemini AI进行高质量翻译。

## ✨ 主要特性

- 🤖 **智能翻译**: 使用Google Gemini AI进行上下文感知的翻译
- 🔄 **多API密钥支持**: 支持多个API密钥的负载均衡和故障转移
- ⚡ **并行处理**: 支持多线程并行翻译，提高效率
- 🔍 **占位符保护**: 自动检测和保护游戏中的占位符和格式标记
- 📝 **人工评审**: 提供友好的评审界面，确保翻译质量
- 🎨 **现代界面**: 基于ttkbootstrap的美观用户界面
- 🧪 **完整测试**: 包含单元测试和集成测试

## 🏗️ 项目架构

本项目采用模块化架构设计：

```
Paradox_Mod_Translator/
├── config/                 # 配置管理模块
├── core/                   # 核心业务逻辑
├── parsers/                # 文件解析器
├── gui/                    # 用户界面
├── utils/                  # 工具模块
├── tests/                  # 测试模块
├── main.py                 # 主程序
├── start.py               # 启动器
└── run_tests.py           # 测试运行器
```


## 🚀 快速开始

### 方法一：使用启动器（推荐）

```bash
python start.py
```

启动器会自动检查依赖并引导您完成设置。

### 方法二：手动安装

1. **安装依赖**
   ```bash
   pip install -r requirements-minimal.txt
   ```

2. **运行程序**
   ```bash
   python main.py
   ```

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows, macOS, Linux
- **内存**: 建议 4GB 以上
- **网络**: 需要访问Google Gemini API

## 🔧 依赖包

### 核心依赖
- `google-generativeai` - Google Gemini AI API客户端
- `ttkbootstrap` - 现代化的tkinter主题框架

### 开发依赖（可选）
- `pytest` - 测试框架
- `black` - 代码格式化
- `flake8` - 代码风格检查

## ⚙️ 配置说明

首次运行时，程序会创建 `translator_config.json` 配置文件。主要配置项：

```json
{
    "api_keys": ["YOUR_GEMINI_API_KEY"],
    "source_language": "english",
    "target_language": "simp_chinese",
    "max_concurrent_tasks": 3,
    "api_call_delay": 3.0
}
```

### 获取API密钥

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 创建新的API密钥
3. 在程序中配置API密钥

## 📖 使用指南

### 基本使用流程

1. **启动程序**
   ```bash
   python start.py
   ```

2. **配置API密钥**
   - 在设置中添加您的Google Gemini API密钥
   - 可以添加多个密钥以提高稳定性

3. **选择语言**
   - 设置源语言（如：english）
   - 设置目标语言（如：simp_chinese）

4. **选择文件**
   - 选择要翻译的YML文件
   - 支持批量选择多个文件

5. **开始翻译**
   - 点击"开始翻译"按钮
   - 程序会自动进行并行翻译

6. **评审结果**
   - 对于重要的翻译，程序会弹出评审窗口
   - 您可以修改翻译结果或选择使用原文

### 支持的语言

- English (english)
- 简体中文 (simp_chinese)
- 繁体中文 (trad_chinese)
- 日语 (japanese)
- 韩语 (korean)
- 法语 (french)
- 德语 (german)
- 西班牙语 (spanish)
- 俄语 (russian)

### 支持的游戏

理论上支持所有使用YML格式本地化文件的Paradox游戏：

- Europa Universalis IV
- Crusader Kings III
- Hearts of Iron IV
- Stellaris
- Victoria 3
- 以及相关的Mod

## 🧪 运行测试

```bash
# 运行所有测试
python run_tests.py

# 运行特定测试模块
python run_tests.py test_config_manager
python run_tests.py test_yml_parser
```

## 🔍 故障排除

### 常见问题

1. **API密钥错误**
   - 确保API密钥格式正确（以AIza开头）
   - 检查API密钥是否有效且有足够配额

2. **文件解析失败**
   - 确保YML文件格式正确
   - 检查文件编码是否为UTF-8

3. **翻译质量问题**
   - 调整游戏/Mod风格提示
   - 使用人工评审功能修正翻译

4. **性能问题**
   - 减少并发任务数
   - 增加API调用延迟

### 日志文件

程序运行时会生成详细的日志，帮助诊断问题：
- 日志显示在程序界面的日志区域
- 可以通过日志级别过滤信息

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行代码格式化
black .

# 运行代码检查
flake8 .

# 运行类型检查
mypy .
```

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- Google Gemini AI 提供强大的翻译能力
- ttkbootstrap 提供美观的UI框架
- Paradox Interactive 创造了优秀的游戏

## 📞 联系方式

如有问题或建议，请：
- 提交 Issue
- 发起 Discussion
- 联系开发者

---

**享受翻译的乐趣！** 🎉

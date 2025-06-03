# 🔧 Paradox Mod Translator 配置指南

本文档详细介绍了重构后的Paradox Mod Translator的配置功能和使用方法。

## 📋 配置界面概览

重构后的应用程序提供了完整的图形化配置界面，分为三个主要选项卡：

### 1. 基本设置 (Basic Settings)

#### 🌍 语言设置
- **源语言**: 选择要翻译的原始语言
  - 支持: English, 简体中文, 繁体中文, 日语, 韩语, 法语, 德语, 西班牙语, 俄语
  - 默认: English
  
- **目标语言**: 选择翻译的目标语言
  - 支持: 同上
  - 默认: 简体中文

#### 📁 文件路径
- **本地化目录**: 设置包含YML文件的根目录
  - 点击"浏览"按钮选择目录
  - 自动扫描子目录中的所有YML文件
  - 支持拖拽文件夹

#### 🎨 翻译风格
- **游戏/Mod风格提示**: 自定义翻译风格指导
- **预设风格按钮**:
  - **通用游戏**: "General video game localization, maintain tone of original."
  - **策略游戏**: "Strategy game localization, formal and precise tone."
  - **角色扮演**: "RPG localization, immersive and narrative style."
  - **历史题材**: "Historical game localization, period-appropriate language."

### 2. API设置 (API Settings)

#### 🔑 API密钥管理
- **多密钥支持**: 支持添加多个Google Gemini API密钥
- **负载均衡**: 自动在多个密钥间轮换使用
- **密钥操作**:
  - ➕ **添加**: 添加新的API密钥
  - ✏️ **编辑**: 修改现有API密钥
  - 🗑️ **删除**: 删除不需要的API密钥
- **密钥验证**: 自动验证密钥格式（AIza开头，39字符长度）
- **安全显示**: 只显示密钥的前4位和后4位

#### 🤖 AI模型设置
- **模型选择**: 选择使用的Gemini模型
  - `gemini-1.5-flash-latest` (推荐，速度快)
  - `gemini-1.5-pro-latest` (质量高)
  - `models/gemini-2.0-flash-lite` (轻量版)
  - `models/gemini-2.0-flash` (最新版)

### 3. 高级设置 (Advanced Settings)

#### ⚡ 并发设置
- **并发任务数**: 同时进行的翻译任务数量
  - 范围: 1-10
  - 默认: 3
  - 建议: 根据API配额和网络状况调整

- **API延迟(秒)**: API调用之间的延迟时间
  - 范围: 0.5-30.0秒
  - 默认: 3.0秒
  - 用途: 避免触发API速率限制

#### 📝 评审设置
- **启用自动评审模式**: 自动弹出评审窗口
  - 开启: 每个翻译完成后立即评审
  - 关闭: 批量翻译完成后统一评审

- **启用延迟评审**: 翻译完成后统一评审
  - 开启: 所有翻译完成后一次性评审
  - 关闭: 实时评审每个翻译

## ⚙️ 配置文件结构

配置信息保存在 `translator_config.json` 文件中：

```json
{
    "api_keys": [
        "AIzaSyExample1234567890123456789012345",
        "AIzaSyExample2345678901234567890123456"
    ],
    "source_language": "english",
    "target_language": "simp_chinese",
    "localization_root_path": "C:/Games/MyMod/localization",
    "selected_model": "gemini-1.5-flash-latest",
    "max_concurrent_tasks": 3,
    "api_call_delay": 3.0,
    "auto_review_mode": true,
    "delayed_review": true,
    "game_mod_style": "Strategy game localization, formal and precise tone.",
    "key_rotation_strategy": "round_robin"
}
```

## 🔄 配置同步

- **实时保存**: 所有配置更改立即保存到文件
- **自动加载**: 启动时自动加载上次的配置
- **配置迁移**: 自动从旧版本配置迁移
- **默认值**: 缺失配置项自动使用默认值

## 🛠️ 高级配置技巧

### 1. 性能优化
```json
{
    "max_concurrent_tasks": 5,
    "api_call_delay": 1.0
}
```
- 适用于: 高配额API密钥，稳定网络环境

### 2. 保守设置
```json
{
    "max_concurrent_tasks": 1,
    "api_call_delay": 5.0
}
```
- 适用于: 免费API密钥，不稳定网络环境

### 3. 批量处理
```json
{
    "auto_review_mode": false,
    "delayed_review": true
}
```
- 适用于: 大量文件翻译，后期统一质检

## 🔍 故障排除

### 常见配置问题

1. **API密钥无效**
   - 检查密钥格式: 必须以"AIza"开头，长度39字符
   - 验证密钥状态: 确保在Google AI Studio中有效
   - 检查配额: 确保有足够的API调用配额

2. **文件路径错误**
   - 确保路径存在且可访问
   - 检查权限: 确保程序有读取权限
   - 路径格式: 使用正斜杠或双反斜杠

3. **并发设置过高**
   - 症状: 频繁的API错误或超时
   - 解决: 降低并发任务数，增加API延迟

4. **翻译质量问题**
   - 调整翻译风格提示
   - 尝试不同的AI模型
   - 启用人工评审模式

### 配置重置

如果配置出现问题，可以：

1. **删除配置文件**: 删除 `translator_config.json`，重启程序使用默认配置
2. **手动编辑**: 直接编辑JSON文件修复错误配置
3. **程序内重置**: 在设置界面重新配置各项参数

## 📊 配置建议

### 新手用户
- 并发任务数: 1-2
- API延迟: 5.0秒
- 启用所有评审选项
- 使用预设翻译风格

### 高级用户
- 并发任务数: 3-5
- API延迟: 1.0-3.0秒
- 自定义翻译风格
- 根据项目需求调整评审设置

### 批量处理
- 并发任务数: 5-10
- API延迟: 0.5-1.0秒
- 关闭实时评审
- 启用延迟评审

## 🔐 安全注意事项

1. **API密钥保护**
   - 不要分享配置文件
   - 定期轮换API密钥
   - 监控API使用情况

2. **文件备份**
   - 翻译前备份原始文件
   - 定期备份配置文件
   - 使用版本控制系统

3. **权限管理**
   - 确保程序只有必要的文件访问权限
   - 不要在共享计算机上保存敏感配置

---

通过合理配置这些选项，您可以获得最佳的翻译体验和效果！

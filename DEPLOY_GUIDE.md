# 部署指南 (Deploy Guide)

本指南详细说明如何将B站直播弹幕排队管理系统部署到GitHub并进行后续维护。

## 📋 准备工作

### 1. 环境要求
- Git (已安装)
- GitHub账户
- Python 3.8+ (用于本地测试)

### 2. 项目文件检查
运行准备脚本确保所有文件已正确清理：
```bash
python prepare_github.py
```

## 🚀 GitHub上传步骤

### 步骤1: 创建GitHub仓库
1. 登录GitHub (https://github.com)
2. 点击右上角的 "+" -> "New repository"
3. 填写仓库信息：
   - Repository name: `bilibili-danmaku-queue-system`
   - Description: `B站直播弹幕排队管理系统 - 基于PyQt6的直播间弹幕监控和队列管理工具`
   - 选择 Public (公开) 或 Private (私有)
   - 不要勾选 "Initialize this repository with README" (因为我们已有README)
4. 点击 "Create repository"

### 步骤2: 本地Git初始化和上传
在项目目录中执行以下命令：

```bash
# 初始化Git仓库
git init

# 添加所有文件到暂存区
git add .

# 创建第一次提交
git commit -m "🎉 初始提交: B站直播弹幕排队管理系统

✨ 功能特性:
- 实时弹幕监控和关键词识别
- 自动排队、插队、上车功能
- 随机选择用户与动画效果
- 舰长礼物监控和次数奖励
- CSV名单管理和状态保存
- 完整的PyQt6 GUI界面

🛠️ 技术栈:
- Python 3.8+
- PyQt6 界面框架
- bilibili-api 弹幕接口
- CSV 数据存储
- 多线程异步处理"

# 添加远程仓库 (将YOUR_USERNAME替换为您的GitHub用户名)
git remote add origin https://github.com/YOUR_USERNAME/bilibili-danmaku-queue-system.git

# 推送到GitHub
git branch -M main
git push -u origin main
```

### 步骤3: 验证上传
1. 访问您的GitHub仓库页面
2. 检查所有文件是否正确上传
3. 确认README.md正确显示

## 📦 发布版本 (可选)

### 创建Release
1. 在GitHub仓库页面点击 "Releases"
2. 点击 "Create a new release"
3. 填写版本信息：
   - Tag version: `v1.7.0` (从 version_info.py 获取)
   - Release title: `B站直播弹幕排队管理系统 v1.7.0`
   - 描述发布内容和功能
4. 可以上传编译好的exe文件 (使用 `python build_exe.py` 构建)

## 🔧 维护和更新

### 日常更新流程
```bash
# 拉取最新代码 (如果有协作者)
git pull origin main

# 查看文件状态
git status

# 添加修改的文件
git add .

# 提交更改
git commit -m "✨ 添加新功能: 功能描述"

# 推送到GitHub
git push origin main
```

### 推荐的提交信息格式
- `✨ feat:` 新功能
- `🐛 fix:` 修复bug
- `📝 docs:` 文档更新
- `💄 style:` 代码格式调整
- `♻️ refactor:` 代码重构
- `⚡ perf:` 性能优化
- `🔧 chore:` 构建工具或辅助工具的变动

## 🛡️ 安全注意事项

### 敏感信息保护
以下文件已通过`.gitignore`排除，请勿上传：
- `bilibili_cookies.json` - 登录凭据
- `config.json` - 个人配置
- `名单.csv` - 用户数据
- `*.log` - 日志文件
- `queue_state.json` - 队列状态

### 示例文件说明
项目包含以下示例文件供用户参考：
- `config.example.json` - 配置文件模板
- `名单.example.csv` - 名单文件模板
- `bilibili_cookies.example.json` - 登录凭据模板

## 📞 问题排查

### 常见问题
1. **Git推送失败**: 检查远程仓库地址和权限
2. **文件太大**: 确认已排除构建文件和数据文件
3. **编码问题**: 确保所有文件使用UTF-8编码

### 获取帮助
- 查看GitHub仓库的Issues页面
- 参考项目README.md中的使用说明
- 检查项目的更新日志.txt

## 🎉 完成部署

恭喜！您已成功将项目部署到GitHub。现在可以：
1. 与他人分享您的项目
2. 接受贡献和反馈
3. 持续改进和维护代码
4. 构建社区和用户群体

---

> **提示**: 记住定期备份重要数据，并保持项目文档的更新！

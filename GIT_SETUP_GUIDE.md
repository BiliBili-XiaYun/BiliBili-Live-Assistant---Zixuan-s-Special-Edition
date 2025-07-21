# Git安装和GitHub上传完整指南

## 🔧 第一步：安装Git

### 方法一：官网下载安装（推荐）
1. 访问Git官网：https://git-scm.com/
2. 点击 "Download for Windows"
3. 下载完成后运行安装程序
4. 安装过程中保持默认设置即可
5. 安装完成后重启命令行

### 方法二：使用包管理器
如果您已安装Chocolatey：
```powershell
choco install git
```

如果您已安装Winget：
```powershell
winget install Git.Git
```

## ⚙️ 第二步：配置Git

安装Git后，打开新的PowerShell或命令提示符窗口，执行以下配置：

```bash
# 设置用户名（替换为您的GitHub用户名）
git config --global user.name "您的GitHub用户名"

# 设置邮箱（替换为您的GitHub邮箱）
git config --global user.email "您的GitHub邮箱"

# 设置默认分支名为main
git config --global init.defaultBranch main

# 验证配置
git config --list
```

## 🐙 第三步：创建GitHub仓库

1. 登录GitHub (https://github.com)
2. 点击右上角的 "+" -> "New repository"
3. 填写仓库信息：
   - **Repository name**: `bilibili-danmaku-queue-system`
   - **Description**: `B站直播弹幕排队管理系统 - 基于PyQt6的直播间弹幕监控和队列管理工具`
   - 选择 **Public** (公开) 或 **Private** (私有)
   - ❌ **不要勾选** "Add a README file"
   - ❌ **不要勾选** "Add .gitignore"
   - ❌ **不要勾选** "Choose a license"
4. 点击 "Create repository"

## 📁 第四步：上传项目到GitHub

在项目目录中执行以下命令（一行一行执行）：

```bash
# 1. 进入项目目录
cd "c:\Users\mytia\Desktop\自动排队工具"

# 2. 初始化Git仓库
git init

# 3. 添加所有文件到暂存区
git add .

# 4. 查看将要提交的文件
git status

# 5. 创建第一次提交
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

# 6. 添加远程仓库（将YOUR_USERNAME替换为您的GitHub用户名）
git remote add origin https://github.com/YOUR_USERNAME/bilibili-danmaku-queue-system.git

# 7. 设置主分支
git branch -M main

# 8. 推送到GitHub
git push -u origin main
```

## 🔐 身份验证

### 首次推送时的身份验证
当您执行 `git push` 时，可能需要身份验证：

#### 方法一：Personal Access Token（推荐）
1. 访问 GitHub Settings -> Developer settings -> Personal access tokens -> Tokens (classic)
2. 点击 "Generate new token (classic)"
3. 设置过期时间和权限（选择 `repo` 权限）
4. 复制生成的token
5. 在Git推送时，用户名输入GitHub用户名，密码输入token

#### 方法二：GitHub CLI
```bash
# 安装GitHub CLI
winget install GitHub.cli

# 登录
gh auth login
```

## ✅ 验证上传成功

1. 访问您的GitHub仓库页面
2. 检查所有文件是否正确上传
3. 确认README.md正确显示
4. 查看提交历史

## 📝 后续维护命令

### 日常更新流程
```bash
# 查看状态
git status

# 添加修改的文件
git add .

# 提交更改
git commit -m "✨ 功能描述"

# 推送到GitHub
git push
```

### 拉取更新
```bash
git pull origin main
```

## 🛠️ 常见问题解决

### 1. Git命令不识别
- 重新安装Git
- 重启命令行窗口
- 检查PATH环境变量

### 2. 推送失败
```bash
# 如果远程仓库已有内容，强制推送（谨慎使用）
git push -f origin main

# 或者先拉取再推送
git pull origin main --allow-unrelated-histories
git push origin main
```

### 3. 文件编码问题
```bash
# 设置Git处理中文文件名
git config --global core.quotepath false
```

## 🎉 完成！

按照以上步骤，您就能成功将项目上传到GitHub了。如果遇到问题，可以参考GitHub的官方文档或搜索相关错误信息。

---

## 📞 需要帮助？

如果在任何步骤遇到问题，请：
1. 检查错误信息
2. 确认网络连接
3. 验证GitHub仓库设置
4. 查看Git配置是否正确

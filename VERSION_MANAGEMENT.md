# 版本管理使用指南

## 📋 概述

从 v1.7 开始，项目使用集中式版本管理。所有版本相关信息都存储在 `version_info.py` 文件中，其他文件通过导入的方式获取这些信息。

## 🔧 版本信息文件结构

`version_info.py` 包含以下信息：

### 基本信息
- `APP_NAME`: 应用程序名称
- `APP_VERSION`: 当前版本号
- `APP_VERSION_FULL`: 完整版本号（用于发布）
- `APP_AUTHOR`: 作者信息
- `APP_AUTHOR_EMAIL`: 作者邮箱
- `APP_DESCRIPTION`: 应用描述

### 组织信息
- `ORGANIZATION_NAME`: 组织名称
- `ORGANIZATION_DOMAIN`: 组织域名

### GitHub 信息
- `GITHUB_REPO_URL`: 仓库地址
- `GITHUB_REPO_NAME`: 仓库名称
- `GITHUB_OWNER`: 仓库所有者

## 📝 如何更新版本

### 1. 更新版本号
编辑 `version_info.py` 文件中的版本信息：

```python
# 更新这些变量
APP_VERSION = "1.8"  # 新版本号
APP_VERSION_FULL = "1.8.0"  # 完整版本号
```

### 2. 更新版本历史
在 `VERSION_HISTORY` 字典中添加新版本的更新内容：

```python
VERSION_HISTORY = {
    "1.8": {
        "date": "2025-XX-XX",
        "changes": [
            "新功能1",
            "修复bug1",
            "改进xxx"
        ]
    },
    # ... 其他版本
}
```

### 3. 自动同步
由于所有文件都从 `version_info.py` 读取信息，更新后会自动同步到：
- `main.py` - 启动日志和应用信息
- `build_exe.py` - 构建配置
- `config/__init__.py` - 应用常量
- GUI界面中的版本显示

## 🔄 使用方式

### 在代码中引用版本信息

```python
# 导入基本信息
from version_info import APP_NAME, APP_VERSION, APP_DESCRIPTION

# 导入辅助函数
from version_info import get_version_string, get_app_info

# 使用示例
print(f"启动 {get_version_string()}")
app_info = get_app_info()
```

### 在构建脚本中使用

```python
from version_info import APP_NAME, APP_VERSION, APP_AUTHOR

PROJECT_NAME = APP_NAME
VERSION = APP_VERSION
AUTHOR = APP_AUTHOR
```

## 🎯 优势

1. **集中管理**: 所有版本信息在一个文件中维护
2. **自动同步**: 更新一次，所有文件自动同步
3. **减少错误**: 避免不同文件中版本号不一致的问题
4. **易于维护**: 发布新版本时只需修改一个文件
5. **版本追踪**: 包含完整的版本历史记录

## 📊 涉及的文件

以下文件已更新为使用 `version_info.py`：

- ✅ `main.py` - 主程序入口
- ✅ `build_exe.py` - 构建脚本
- ✅ `config/__init__.py` - 配置模块
- ✅ `DEPLOY_GUIDE.md` - 部署指南
- ✅ `更新日志.txt` - 版本历史

## ⚠️ 注意事项

1. 修改 `version_info.py` 后，记得更新 `更新日志.txt`
2. 发布新版本前，确保所有功能正常工作
3. 版本号建议遵循语义化版本规范 (Semantic Versioning)
4. 重大更新时记得更新 `APP_VERSION_FULL`

## 🚀 发布流程

1. 更新 `version_info.py` 中的版本信息
2. 更新 `VERSION_HISTORY` 记录变更
3. 测试应用程序功能
4. 提交代码到 Git
5. 创建 GitHub Release
6. 构建并上传可执行文件

这个集中式版本管理系统让项目维护变得更加简单和可靠！

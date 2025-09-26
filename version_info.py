#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本信息配置文件
集中管理应用程序的版本号、名称、作者等信息
"""

# 应用程序基本信息
APP_NAME = "子轩专属排队工具"
APP_VERSION = "1.9.0"
APP_VERSION_FULL = "1.9.0"  # 新增投票系统
APP_AUTHOR = "BiliBili-XiaYun"
APP_AUTHOR_EMAIL = "mytianyi0712@outlook.com"
APP_DESCRIPTION = "B站直播弹幕排队管理系统 - 基于PyQt6的直播间弹幕监控和队列管理工具"

# 组织信息
ORGANIZATION_NAME = "子轩专属排队工具"
ORGANIZATION_DOMAIN = "github.com/BiliBili-XiaYun"

# GitHub 仓库信息
GITHUB_REPO_URL = "https://github.com/BiliBili-XiaYun/BiliBili-Live-Assistant---Zixuan-s-Special-Edition"
GITHUB_REPO_NAME = "BiliBili-Live-Assistant---Zixuan-s-Special-Edition"
GITHUB_OWNER = "BiliBili-XiaYun"

# 版本历史和更新信息
VERSION_HISTORY = {
    "1.7": {
        "date": "2025-07-21",
        "changes": [
            "版本号更新至1.7",
            "项目已上传至GitHub进行开源管理", 
            "随机数算法升级，现在随机数的随机性更强了",
            "添加了已中奖队列，采用先进先出方式维护了一个长度为10的队列",
            "添加了自动检测插队的功能"
        ]
    },
    "1.5": {
        "date": "2025-06-30",
        "changes": [
            "舰长自动追加到名单最后",
            "排队队列添加随机功能，使用滚筒式抽奖",
            "随机选择2个用户，选中后自动置顶"
        ]
    }
}

# 技术栈信息
TECH_STACK = [
    "Python 3.8+",
    "PyQt6 界面框架", 
    "bilibili-api 弹幕接口",
    "CSV 数据存储",
    "多线程异步处理"
]

# 功能特性列表
FEATURES = [
    "实时弹幕监控和关键词识别",
    "自动排队、插队、上车功能", 
    "随机选择用户与动画效果",
    "舰长礼物监控和次数奖励",
    "CSV名单管理和状态保存",
    "完整的PyQt6 GUI界面"
]

# 构建版本信息字符串的辅助函数
def get_version_string():
    """获取版本字符串"""
    return f"{APP_NAME} v{APP_VERSION}"

def get_full_version_string():
    """获取完整版本字符串"""
    return f"{APP_NAME} v{APP_VERSION_FULL}"

def get_app_info():
    """获取应用信息字典"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "version_full": APP_VERSION_FULL,
        "author": APP_AUTHOR,
        "email": APP_AUTHOR_EMAIL,
        "description": APP_DESCRIPTION,
        "organization": ORGANIZATION_NAME,
        "github_url": GITHUB_REPO_URL
    }

def get_commit_message_template():
    """获取Git提交信息模板"""
    features_text = "\n".join([f"- {feature}" for feature in FEATURES])
    tech_stack_text = "\n".join([f"- {tech}" for tech in TECH_STACK])
    
    return f"""🎉 初始提交: {APP_DESCRIPTION}

✨ 功能特性:
{features_text}

🛠️ 技术栈:
{tech_stack_text}"""

# 版本检查函数
def is_dev_version():
    """检查是否为开发版本"""
    return "dev" in APP_VERSION.lower() or "beta" in APP_VERSION.lower()

def get_version_tuple():
    """获取版本号元组，用于版本比较"""
    try:
        # 移除可能的dev/beta后缀
        clean_version = APP_VERSION.split('-')[0].split('+')[0]
        return tuple(map(int, clean_version.split('.')))
    except ValueError:
        return (1, 7, 0)  # 默认版本

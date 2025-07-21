#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装和初始化脚本
"""

import os
import shutil
import sys
from pathlib import Path

def setup_project():
    """设置项目环境"""
    print("🚀 正在初始化B站直播弹幕排队管理系统...")
    
    current_dir = Path(__file__).parent
    
    # 复制示例配置文件
    config_files = [
        ("config.example.json", "config.json"),
        ("名单.example.csv", "名单.csv"),
        ("bilibili_cookies.example.json", "bilibili_cookies.json")
    ]
    
    for src, dst in config_files:
        src_path = current_dir / src
        dst_path = current_dir / dst
        
        if src_path.exists() and not dst_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"✅ 创建配置文件: {dst}")
        elif dst_path.exists():
            print(f"⚠️ 配置文件已存在: {dst}")
        else:
            print(f"❌ 示例文件不存在: {src}")
    
    print("\n📝 下一步操作:")
    print("1. 编辑 config.json 设置直播间ID")
    print("2. 编辑 名单.csv 添加用户名单")
    print("3. 运行 python main.py 启动程序")
    print("\n🎉 初始化完成!")

if __name__ == "__main__":
    setup_project()

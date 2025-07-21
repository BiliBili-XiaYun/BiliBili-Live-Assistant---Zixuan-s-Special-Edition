#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub上传准备脚本 - 清理和准备项目文件用于上传
"""

import os
import shutil
import sys
from pathlib import Path

def prepare_for_github():
    """准备项目文件用于GitHub上传"""
    print("🚀 准备项目文件用于GitHub上传...")
    
    current_dir = Path(__file__).parent
    
    # 需要删除的文件（包含个人信息或不必要的文件）
    files_to_remove = [
        "bilibili_cookies.json",
        "config.json", 
        "名单.csv",
        "system.log",
        "次数扣除日志.txt",
        "count_changes.txt",
        "queue_state.json",
        "test_queue_system.py",
        "test_report.json",
        "子轩专属排队工具.spec"
    ]
    
    # 需要删除的目录
    dirs_to_remove = [
        "build",
        "dist", 
        ".vscode",
        "__pycache__",
        "backup_logs"
    ]
    
    # 需要删除的模式文件
    patterns_to_remove = [
        "*-新舰长.csv",
        "排队日志_*.txt",
        "optimize_*.py",
        "*_REPORT.md",
        "cleanup_project.py",
        "final_log_optimization.py",
        "refactor_logs.py",
        "replace_logs.py"
    ]
    
    # 删除文件
    for file_name in files_to_remove:
        file_path = current_dir / file_name
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"✅ 删除文件: {file_name}")
            except Exception as e:
                print(f"❌ 删除文件失败: {file_name} - {e}")
    
    # 删除目录
    for dir_name in dirs_to_remove:
        dir_path = current_dir / dir_name
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"✅ 删除目录: {dir_name}")
            except Exception as e:
                print(f"❌ 删除目录失败: {dir_name} - {e}")
    
    # 删除模式匹配的文件
    import glob
    for pattern in patterns_to_remove:
        for file_path in current_dir.glob(pattern):
            try:
                file_path.unlink()
                print(f"✅ 删除文件: {file_path.name}")
            except Exception as e:
                print(f"❌ 删除文件失败: {file_path.name} - {e}")
    
    # 清理Python缓存
    for root, dirs, files in os.walk(current_dir):
        # 删除 __pycache__ 目录
        if "__pycache__" in dirs:
            pycache_path = Path(root) / "__pycache__"
            try:
                shutil.rmtree(pycache_path)
                print(f"✅ 删除缓存: {pycache_path}")
            except:
                pass
        
        # 删除 .pyc 文件
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                pyc_path = Path(root) / file
                try:
                    pyc_path.unlink()
                    print(f"✅ 删除缓存文件: {pyc_path}")
                except:
                    pass
    
    # 检查必要文件是否存在
    required_files = [
        "README.md",
        "LICENSE", 
        ".gitignore",
        "requirements.txt",
        "setup.py",
        "build_exe.py",
        "main.py",
        "config.example.json",
        "名单.example.csv",
        "bilibili_cookies.example.json"
    ]
    
    print("\n📋 检查必要文件...")
    missing_files = []
    for file_name in required_files:
        file_path = current_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name}")
        else:
            print(f"❌ {file_name}")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"\n⚠️ 缺少文件: {', '.join(missing_files)}")
        return False
    
    # 显示最终的文件列表
    print("\n📁 准备上传的文件和目录:")
    for item in sorted(current_dir.iterdir()):
        if item.name.startswith('.git'):
            continue
        if item.is_dir():
            print(f"📁 {item.name}/")
        else:
            print(f"📄 {item.name}")
    
    print("\n✅ 项目准备完成!")
    print("\n📝 下一步:")
    print("1. 检查 DEPLOY_GUIDE.md 了解详细上传步骤")
    print("2. 在GitHub创建新仓库")
    print("3. 使用Git命令上传项目文件")
    
    return True

if __name__ == "__main__":
    success = prepare_for_github()
    if success:
        print("\n🎉 准备成功!")
    else:
        print("\n💥 准备失败!")
        sys.exit(1)

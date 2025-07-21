#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller 打包脚本 - 子轩专属排队工具
使用目录模式打包，便于调试和部署
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 项目信息 - 从 version_info.py 获取
from version_info import APP_NAME, APP_VERSION, APP_AUTHOR

PROJECT_NAME = APP_NAME
EXECUTABLE_NAME = APP_NAME  
VERSION = APP_VERSION
AUTHOR = APP_AUTHOR

# 路径配置
CURRENT_DIR = Path(__file__).parent.absolute()
PACKAGE_ROOT_DIR = CURRENT_DIR.parent / "打包"  # 打包输出根目录
BUILD_DIR = PACKAGE_ROOT_DIR / "build"
DIST_DIR = PACKAGE_ROOT_DIR / "dist"
MAIN_SCRIPT = CURRENT_DIR / "main.py"
ICON_PATH = CURRENT_DIR / "resource" / "icon" / "app_icon.ico"

# 需要包含的数据文件
DATA_FILES = [
    ("resource/icon/*.ico", "resource/icon/"),
    ("config.json", "."),
    ("名单.csv", "."),
    ("qt.conf", "."),
]

# 需要包含的Python包
HIDDEN_IMPORTS = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtWidgets", 
    "PyQt6.QtGui",
    "bilibili_api",
    "bilibili_api.live",
    "bilibili_api.login",
    "aiohttp",
    "websockets",
    "qrcode",
    "PIL",
    "plyer",
    "asyncio",
    "json",
    "csv",
    "sqlite3",
]

# 排除的模块（减少打包大小）
EXCLUDES = [
    "tkinter",
    "matplotlib",
    "numpy",
    "scipy",
    "pandas",
    "jupyter",
    "notebook",
    "test",
    "unittest",
    "pydoc",
    "doctest",
]


def clean_build_dirs():
    """清理构建目录"""
    print("🧹 清理构建目录...")
    
    # 确保打包根目录存在
    if not PACKAGE_ROOT_DIR.exists():
        PACKAGE_ROOT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ 创建打包目录: {PACKAGE_ROOT_DIR}")
    
    # 清理旧的构建文件
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"   ✅ 清理完成: {dir_path}")
            except Exception as e:
                print(f"   ⚠️ 清理失败: {dir_path} - {e}")
    
    # 清理 __pycache__ 和 .pyc 文件
    print("🧹 清理Python缓存文件...")
    for root, dirs, files in os.walk(CURRENT_DIR):
        # 删除 __pycache__ 目录
        if "__pycache__" in dirs:
            pycache_path = Path(root) / "__pycache__"
            try:
                shutil.rmtree(pycache_path)
                print(f"   ✅ 删除: {pycache_path}")
            except:
                pass
        
        # 删除 .pyc 文件
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                pyc_path = Path(root) / file
                try:
                    pyc_path.unlink()
                    print(f"   ✅ 删除: {pyc_path}")
                except:
                    pass


def check_dependencies():
    """检查依赖是否安装"""
    print("🔍 检查依赖...")
    
    # 定义包名映射（pip包名 -> 导入名）
    package_mapping = {
        "PyQt6": "PyQt6",
        "bilibili_api": "bilibili_api", 
        "pyinstaller": "PyInstaller"
    }
    
    missing_packages = []
    
    for pip_name, import_name in package_mapping.items():
        try:
            __import__(import_name)
            print(f"   ✅ {pip_name}")
        except ImportError:
            missing_packages.append(pip_name)
            print(f"   ❌ {pip_name}")
    
    if missing_packages:
        print(f"\n❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 所有依赖检查通过!")
    return True


def create_spec_file():
    """创建PyInstaller spec文件"""
    print("📝 创建 PyInstaller spec 文件...")
    
    # 构建数据文件列表
    datas_list = []
    for src, dst in DATA_FILES:
        datas_list.append(f"('{src}', '{dst}')")
    
    datas_str = "[" + ",\n             ".join(datas_list) + "]"
    
    # 构建隐式导入列表
    hiddenimports_str = "[" + ",\n                    ".join([f"'{pkg}'" for pkg in HIDDEN_IMPORTS]) + "]"
    
    # 构建排除列表
    excludes_str = "[" + ",\n             ".join([f"'{pkg}'" for pkg in EXCLUDES]) + "]"
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# {PROJECT_NAME} v{VERSION} - PyInstaller配置文件
# 生成时间: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

from PyInstaller.utils.hooks import collect_all, collect_submodules
import datetime

# 收集所有bilibili_api模块
try:
    bilibili_datas, bilibili_binaries, bilibili_hiddenimports = collect_all('bilibili_api')
except:
    bilibili_datas, bilibili_binaries, bilibili_hiddenimports = [], [], []

# 收集PyQt6模块
try:
    pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')
except:
    pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = [], [], []

a = Analysis(
    ['{MAIN_SCRIPT.name}'],
    pathex=[r'{CURRENT_DIR}'],
    binaries=bilibili_binaries + pyqt6_binaries,
    datas={datas_str} + bilibili_datas + pyqt6_datas,
    hiddenimports={hiddenimports_str} + bilibili_hiddenimports + pyqt6_hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes_str},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=r'{EXECUTABLE_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 设置为False隐藏控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{ICON_PATH}',
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=r'{EXECUTABLE_NAME}',
)
'''
    
    spec_file = CURRENT_DIR / f"{EXECUTABLE_NAME}.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"   ✅ 创建完成: {spec_file}")
    return spec_file


def run_pyinstaller(spec_file):
    """运行PyInstaller"""
    print("🚀 开始打包...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",              # 清理临时文件
        "--noconfirm",          # 不询问确认
        "--log-level", "INFO",  # 设置日志级别
        "--workpath", str(BUILD_DIR),  # 指定工作目录
        "--distpath", str(DIST_DIR),   # 指定输出目录
        str(spec_file)
    ]
    
    print(f"   执行命令: {' '.join(cmd)}")
    
    try:
        # 使用系统默认编码，避免UTF-8解码错误
        result = subprocess.run(
            cmd, 
            cwd=CURRENT_DIR,  # 在源代码目录执行
            capture_output=True, 
            text=True, 
            encoding='gbk',  # 使用GBK编码
            errors='ignore'  # 忽略编码错误
        )
        
        if result.returncode == 0:
            print("✅ 打包成功!")
            print("标准输出:")
            print(result.stdout)
            return True
        else:
            print(f"❌ 打包失败! 返回码: {result.returncode}")
            print("标准输出:")
            print(result.stdout)
            print("错误输出:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 打包过程中出现异常: {e}")
        return False


def post_build_setup():
    """打包后的设置"""
    print("🔧 执行打包后设置...")
    
    # 检查输出目录
    output_dir = DIST_DIR / EXECUTABLE_NAME
    if not output_dir.exists():
        print(f"❌ 输出目录不存在: {output_dir}")
        return False
    
    # 复制额外的配置文件
    extra_files = [
        "更新日志.txt",
        "README.md",
    ]
    
    for file_name in extra_files:
        src_file = CURRENT_DIR / file_name
        if src_file.exists():
            dst_file = output_dir / file_name
            try:
                shutil.copy2(src_file, dst_file)
                print(f"   ✅ 复制: {file_name}")
            except Exception as e:
                print(f"   ⚠️ 复制失败: {file_name} - {e}")
    
    # 创建启动脚本（可选）
    startup_script = output_dir / "启动.bat"
    with open(startup_script, 'w', encoding='gbk') as f:
        f.write(f"""@echo off
echo 正在启动 {PROJECT_NAME}...
"{EXECUTABLE_NAME}.exe"
pause
""")
    print(f"   ✅ 创建启动脚本: 启动.bat")
    
    return True


def print_summary():
    """打印打包总结"""
    output_dir = DIST_DIR / EXECUTABLE_NAME
    
    print("\n" + "="*60)
    print(f"🎉 {PROJECT_NAME} v{VERSION} 打包完成!")
    print("="*60)
    print(f"📁 输出目录: {output_dir}")
    print(f"🚀 主程序: {output_dir / f'{EXECUTABLE_NAME}.exe'}")
    print("\n📋 打包信息:")
    print(f"   - 打包模式: 目录模式 (便于调试和部署)")
    print(f"   - 控制台: 隐藏 (无黑窗口)")
    print(f"   - 图标: {ICON_PATH.name}")
    print(f"   - Python版本: {sys.version}")
    
    # 显示目录大小
    try:
        total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"   - 打包大小: {size_mb:.1f} MB")
    except:
        pass
    
    print("\n📝 使用说明:")
    print(f"   1. 进入目录: {output_dir}")
    print(f"   2. 运行程序: {EXECUTABLE_NAME}.exe")
    print(f"   3. 或双击: 启动.bat")
    print("\n✨ 现在可以将整个目录复制到其他电脑使用!")


def main():
    """主函数"""
    print(f"🔨 {PROJECT_NAME} v{VERSION} 打包工具")
    print(f"📅 Python版本: {sys.version}")
    print("="*60)
    
    # 检查主脚本是否存在
    if not MAIN_SCRIPT.exists():
        print(f"❌ 主脚本不存在: {MAIN_SCRIPT}")
        return False
    
    # 检查图标文件
    if not ICON_PATH.exists():
        print(f"⚠️ 图标文件不存在: {ICON_PATH}")
        print("   将使用默认图标")
    
    # 执行打包流程
    try:
        # 1. 清理构建目录
        clean_build_dirs()
        
        # 2. 检查依赖
        if not check_dependencies():
            return False
        
        # 3. 创建spec文件
        spec_file = create_spec_file()
        
        # 4. 运行PyInstaller
        if not run_pyinstaller(spec_file):
            return False
        
        # 5. 打包后设置
        if not post_build_setup():
            return False
        
        # 6. 打印总结
        print_summary()
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户取消打包")
        return False
    except Exception as e:
        print(f"\n❌ 打包过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import datetime
    success = main()
    
    if success:
        print(f"\n🎊 打包成功完成! ({datetime.datetime.now().strftime('%H:%M:%S')})")
        sys.exit(0)
    else:
        print(f"\n💥 打包失败! ({datetime.datetime.now().strftime('%H:%M:%S')})")
        input("按回车键退出...")
        sys.exit(1)

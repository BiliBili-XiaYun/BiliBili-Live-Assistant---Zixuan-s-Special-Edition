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
import datetime
from pathlib import Path

# 项目信息 - 从 version_info.py 获取
from version_info import APP_NAME, APP_VERSION, APP_AUTHOR

PROJECT_NAME = APP_NAME
EXECUTABLE_NAME = APP_NAME  
EXECUTABLE_NAME2 = f"{APP_NAME} - 排队工具2"  # 排队工具2的exe名称
VERSION = APP_VERSION
AUTHOR = APP_AUTHOR

# 路径配置
CURRENT_DIR = Path(__file__).parent.absolute()
PACKAGE_ROOT_DIR = CURRENT_DIR.parent / "打包"  # 打包输出根目录
BUILD_DIR = PACKAGE_ROOT_DIR / "build"
DIST_DIR = PACKAGE_ROOT_DIR / "dist"
MAIN_SCRIPT = CURRENT_DIR / "main.py"
MAIN2_SCRIPT = CURRENT_DIR / "main2.py"  # 排队工具2主文件
ICON_PATH = CURRENT_DIR / "resource" / "icon" / "app_icon.ico"

# 需要包含的数据文件
DATA_FILES = [
    ("resource/icon/*.ico", "resource/icon/"),
    ("config.json", "."),          # 包含当前配置文件
    ("更新日志.txt", "."),          # 包含更新日志
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


def create_spec_files():
    """创建两个PyInstaller spec文件 - 主程序和排队工具2"""
    print("📝 创建 PyInstaller spec 文件...")
    
    # 检查第二个主文件是否存在
    if not MAIN2_SCRIPT.exists():
        print(f"❌ 排队工具2主脚本不存在: {MAIN2_SCRIPT}")
        print("   将只生成主程序的spec文件")
        return create_single_spec_file(MAIN_SCRIPT, EXECUTABLE_NAME)
    
    # 检查并构建存在的数据文件列表
    valid_datas = []
    for src, dst in DATA_FILES:
        # 处理通配符路径
        if '*' in src:
            from glob import glob
            matching_files = glob(src)
            if matching_files:
                valid_datas.append(f"('{src}', '{dst}')")
                print(f"   ✅ 找到数据文件: {src} ({len(matching_files)} 个文件)")
            else:
                print(f"   ⚠️ 跳过数据文件: {src} (未找到匹配文件)")
        else:
            # 处理单个文件
            src_path = CURRENT_DIR / src
            if src_path.exists():
                valid_datas.append(f"('{src}', '{dst}')")
                print(f"   ✅ 找到数据文件: {src}")
            else:
                print(f"   ⚠️ 跳过数据文件: {src} (文件不存在)")
    
    datas_str = "[" + ",\n             ".join(valid_datas) + "]"
    
    # 构建隐式导入列表
    hiddenimports_str = "[" + ",\n                    ".join([f"'{pkg}'" for pkg in HIDDEN_IMPORTS]) + "]"
    
    # 构建排除列表
    excludes_str = "[" + ",\n             ".join([f"'{pkg}'" for pkg in EXCLUDES]) + "]"
    
    # 生成主程序spec文件
    spec_content1 = f'''# -*- mode: python ; coding: utf-8 -*-
# {PROJECT_NAME} v{VERSION} - PyInstaller配置文件 (主程序)
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
    
    # 生成排队工具2 spec文件
    spec_content2 = f'''# -*- mode: python ; coding: utf-8 -*-
# {PROJECT_NAME} v{VERSION} - PyInstaller配置文件 (排队工具2)
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

a2 = Analysis(
    ['{MAIN2_SCRIPT.name}'],
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

pyz2 = PYZ(a2.pure, a2.zipped_data, cipher=None)

exe2 = EXE(
    pyz2,
    a2.scripts,
    [],
    exclude_binaries=True,
    name=r'{EXECUTABLE_NAME2}',
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

coll2 = COLLECT(
    exe2,
    a2.binaries,
    a2.zipfiles,
    a2.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=r'{EXECUTABLE_NAME2}',
)
'''
    
    # 写入spec文件
    spec_file1 = CURRENT_DIR / f"{EXECUTABLE_NAME}.spec"
    spec_file2 = CURRENT_DIR / f"{EXECUTABLE_NAME2}.spec"
    
    with open(spec_file1, 'w', encoding='utf-8') as f:
        f.write(spec_content1)
    print(f"   ✅ 主程序spec文件: {spec_file1}")
    
    with open(spec_file2, 'w', encoding='utf-8') as f:
        f.write(spec_content2)
    print(f"   ✅ 排队工具2 spec文件: {spec_file2}")
    
    return [spec_file1, spec_file2]


def create_single_spec_file(main_script, executable_name):
    """创建单个spec文件（向后兼容）"""
    # 检查并构建存在的数据文件列表
    valid_datas = []
    for src, dst in DATA_FILES:
        # 处理通配符路径
        if '*' in src:
            from glob import glob
            matching_files = glob(src)
            if matching_files:
                valid_datas.append(f"('{src}', '{dst}')")
                print(f"   ✅ 找到数据文件: {src} ({len(matching_files)} 个文件)")
            else:
                print(f"   ⚠️ 跳过数据文件: {src} (未找到匹配文件)")
        else:
            # 处理单个文件
            src_path = CURRENT_DIR / src
            if src_path.exists():
                valid_datas.append(f"('{src}', '{dst}')")
                print(f"   ✅ 找到数据文件: {src}")
            else:
                print(f"   ⚠️ 跳过数据文件: {src} (文件不存在)")
    
    datas_str = "[" + ",\n             ".join(valid_datas) + "]"
    
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
    ['{main_script.name}'],
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
    name=r'{executable_name}',
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
    name=r'{executable_name}',
)
'''
    
    spec_file = CURRENT_DIR / f"{executable_name}.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"   ✅ 创建完成: {spec_file}")
    return [spec_file]


def run_pyinstaller(spec_files):
    """运行PyInstaller打包多个spec文件"""
    print("🚀 开始打包...")
    
    if not isinstance(spec_files, list):
        spec_files = [spec_files]
    
    for i, spec_file in enumerate(spec_files, 1):
        print(f"\n📦 打包 {i}/{len(spec_files)}: {spec_file.name}")
        
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
                encoding='gbk',  # Windows中文系统使用GBK编码
                errors='ignore'  # 忽略解码错误
            )
            
            if result.returncode == 0:
                print(f"   ✅ 打包成功: {spec_file.name}")
            else:
                print(f"   ❌ 打包失败: {spec_file.name}")
                print("错误输出:")
                print(result.stderr)
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"   ❌ PyInstaller执行失败: {e}")
            return False
        except Exception as e:
            print(f"   ❌ 执行命令时出现异常: {e}")
            return False
    
    return True


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
        "LICENSE",
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
    
    # 获取GitHub仓库URL
    try:
        from version_info import GITHUB_REPO_URL
        github_url = GITHUB_REPO_URL
    except ImportError:
        github_url = 'https://github.com/BiliBili-XiaYun/BiliBili-Live-Assistant---Zixuan-s-Special-Edition'
    
    # 创建配置文件使用说明
    config_readme = output_dir / "配置说明.txt"
    with open(config_readme, 'w', encoding='utf-8') as f:
        f.write(f"""📝 {PROJECT_NAME} v{VERSION} 配置说明

🚀 首次使用步骤：

1. 配置文件设置
   - 已包含当前 config.json 配置文件
   - 可根据需要编辑 config.json 中的直播间ID和其他设置

2. 名单文件设置  
   - 需要创建 名单.csv 文件，或使用程序内的名单编辑功能
   - 名单格式：用户名(次数)，例如：张三(100)

3. 启动程序
   - 双击 {EXECUTABLE_NAME}.exe 或 启动.bat
   - 首次运行可能需要登录B站账号

📁 重要文件说明：
   - config.json: 主要配置文件（已包含，可直接使用）
   - 更新日志.txt: 版本更新记录
   - 名单.csv: 用户名单文件（需要自行创建或使用程序内编辑功能）

⚠️ 注意事项：
   - 请确保网络连接正常
   - 首次使用需要配置B站登录信息
   - 建议定期备份配置文件和名单文件
   - 如需名单文件，可在程序中使用名单编辑功能创建

🔗 更多帮助：
   GitHub: {github_url}
""")
    print(f"   ✅ 创建配置说明: 配置说明.txt")
    
    # 创建启动脚本（可选）
    startup_script = output_dir / "启动.bat"
    with open(startup_script, 'w', encoding='utf-8') as f:
        f.write(f"""@echo off
chcp 65001 >nul
echo 正在启动 {PROJECT_NAME}...
echo.
echo 首次使用请先阅读"配置说明.txt"
echo.
"{EXECUTABLE_NAME}.exe"
pause
""")
    print(f"   ✅ 创建启动脚本: 启动.bat")
    
    return True


def print_summary():
    """打印打包总结"""
    output_dir1 = DIST_DIR / EXECUTABLE_NAME
    output_dir2 = DIST_DIR / EXECUTABLE_NAME2
    
    print("\n" + "="*60)
    print(f"🎉 {PROJECT_NAME} v{VERSION} 打包完成!")
    print("="*60)
    print(f"📁 输出目录: {DIST_DIR}")
    print(f"🚀 主程序: {output_dir1 / f'{EXECUTABLE_NAME}.exe'}")
    print(f"🎯 排队工具2: {output_dir2 / f'{EXECUTABLE_NAME2}.exe'}")
    print("\n📋 打包信息:")
    print(f"   - 打包模式: 目录模式 (便于调试和部署)")
    print(f"   - 控制台: 隐藏 (无黑窗口)")
    print(f"   - 图标: {ICON_PATH.name}")
    print(f"   - Python版本: {sys.version}")
    
    # 显示总目录大小
    try:
        total_size1 = sum(f.stat().st_size for f in output_dir1.rglob('*') if f.is_file()) if output_dir1.exists() else 0
        total_size2 = sum(f.stat().st_size for f in output_dir2.rglob('*') if f.is_file()) if output_dir2.exists() else 0
        size1_mb = total_size1 / (1024 * 1024)
        size2_mb = total_size2 / (1024 * 1024)
        total_mb = size1_mb + size2_mb
        print(f"   - 主程序大小: {size1_mb:.1f} MB")
        print(f"   - 排队工具2大小: {size2_mb:.1f} MB")
        print(f"   - 总大小: {total_mb:.1f} MB")
    except:
        pass
    
    print("\n📝 使用说明:")
    print(f"   主程序:")
    print(f"     - 进入目录: {output_dir1}")
    print(f"     - 运行程序: {EXECUTABLE_NAME}.exe")
    print(f"   排队工具2:")
    print(f"     - 进入目录: {output_dir2}")
    print(f"     - 运行程序: {EXECUTABLE_NAME2}.exe")
    print("\n✨ 现在可以将这两个目录分别复制到其他电脑使用!")
    print("\n🔍 两个版本的区别:")
    print(f"   - 主程序: 完整功能版本")
    print(f"   - 排队工具2: 简化版本，专注排队和插队功能，支持独立插队名单")


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
        spec_files = create_spec_files()
        
        # 4. 运行PyInstaller
        if not run_pyinstaller(spec_files):
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

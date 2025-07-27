#!/usr/bin/env python
"""CocoroCore2 ビルドスクリプト - MemOS統合バックエンド"""

import io
import shutil
import subprocess
import sys
from pathlib import Path

# Windows環境でのUTF-8出力対応
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ビルド設定
BUILD_CONFIG = {
    "app_name": "CocoroCore2",
    "icon_path": None,  # アイコンが必要な場合は指定
    "hidden_imports": [
        # MemOS関連
        "memos",
        "memos.configs",
        "memos.configs.mem_os",
        "memos.mem_os",
        "memos.mem_os.main",
        # FastAPI関連
        "fastapi",
        "uvicorn",
        "uvicorn.workers",
        # LLM関連
        "litellm",
        "litellm.utils",
        "openai",
        # その他
        "tiktoken",
        "tiktoken.core",
        "pydantic",
        "httpx",
        "json",
        "asyncio",
        "logging",
        "pathlib",
        "datetime",
        "typing",
    ],
    "excludes": [
        # 不要なモジュールを除外してサイズ削減
        "torch",
        "tensorflow",
        "matplotlib",
        "scipy",
        "numpy.distutils",
        "tkinter",
        "test",
        "unittest",
    ],
    "onefile": False,  # フォルダ形式（メンテナンス性のため）
    "console": True,   # コンソール表示（ログ出力のため）
    "datas": [
        # 設定ファイル
        ("config", "config"),
    ],
}


def clean_build_dirs():
    """ビルドディレクトリをクリーンアップ"""
    print("🧹 古いビルドファイルをクリーンアップ中...")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"  ✅ {dir_name} を削除しました")
            except Exception as e:
                print(f"  ⚠️ {dir_name} の削除に失敗: {e}")


def create_spec_file():
    """PyInstallerスペックファイルを動的生成"""
    print("📋 PyInstallerスペックファイルを生成中...")
    
    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas={BUILD_CONFIG['datas']},
    hiddenimports={BUILD_CONFIG['hidden_imports']},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={BUILD_CONFIG['excludes']},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{BUILD_CONFIG['app_name']}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={str(BUILD_CONFIG['console']).lower()},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={repr(BUILD_CONFIG['icon_path'])},
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{BUILD_CONFIG['app_name']}',
)
"""
    
    spec_file = f"{BUILD_CONFIG['app_name']}.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"  ✅ {spec_file} を生成しました")
    return spec_file


def run_pyinstaller(spec_file):
    """PyInstallerを実行"""
    print("🔨 PyInstallerを実行中...")
    
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]
    
    print(f"  実行コマンド: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("  ✅ PyInstaller実行完了")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ PyInstaller実行エラー:")
        print(f"    stdout: {e.stdout}")
        print(f"    stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("  ❌ PyInstallerが見つかりません")
        print("    pip install pyinstaller を実行してください")
        return False


def copy_additional_files():
    """追加ファイルをdistディレクトリにコピー"""
    print("📁 追加ファイルをコピー中...")
    
    dist_dir = Path("dist") / BUILD_CONFIG['app_name']
    
    # コピーするファイル/ディレクトリ
    files_to_copy = [
        ("README.md", "README.md"),
        ("requirements.txt", "requirements.txt"),
        ("config", "config"),
    ]
    
    for src, dst in files_to_copy:
        src_path = Path(src)
        dst_path = dist_dir / dst
        
        if src_path.exists():
            try:
                if src_path.is_dir():
                    if dst_path.exists():
                        shutil.rmtree(dst_path)
                    shutil.copytree(src_path, dst_path)
                else:
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dst_path)
                print(f"  ✅ {src} → {dst}")
            except Exception as e:
                print(f"  ⚠️ {src} のコピーに失敗: {e}")
        else:
            print(f"  ⚠️ {src} が見つかりません（スキップ）")


def create_startup_script():
    """起動スクリプトを作成"""
    print("📜 起動スクリプトを作成中...")
    
    dist_dir = Path("dist") / BUILD_CONFIG['app_name']
    
    # Windows用バッチファイル
    batch_content = """@echo off
chcp 65001 > nul
echo Starting CocoroCore2 - MemOS Unified Backend...
echo.

REM Check if OPENAI_API_KEY is set
if "%OPENAI_API_KEY%"=="" (
    echo Warning: OPENAI_API_KEY environment variable is not set
    echo Please set your OpenAI API key for full functionality
    echo.
)

REM Start CocoroCore2
CocoroCore2.exe --environment production

echo.
echo CocoroCore2 has stopped.
pause
"""
    
    batch_file = dist_dir / "start_cocoro_core2.bat"
    with open(batch_file, 'w', encoding='utf-8') as f:
        f.write(batch_content)
    
    print(f"  ✅ {batch_file} を作成しました")


def print_build_summary():
    """ビルド結果サマリーを表示"""
    dist_dir = Path("dist") / BUILD_CONFIG['app_name']
    exe_file = dist_dir / f"{BUILD_CONFIG['app_name']}.exe"
    
    print("\n" + "="*60)
    print("🎉 CocoroCore2 ビルド完了!")
    print("="*60)
    
    if exe_file.exists():
        size_mb = exe_file.stat().st_size / (1024 * 1024)
        print(f"📦 実行ファイル: {exe_file}")
        print(f"📏 ファイルサイズ: {size_mb:.1f} MB")
    
    print(f"📁 出力ディレクトリ: {dist_dir}")
    print("🚀 起動方法:")
    print(f"   cd {dist_dir}")
    print("   start_cocoro_core2.bat")
    print("\n💡 実行前に以下の環境変数を設定してください:")
    print("   set OPENAI_API_KEY=your_api_key_here")
    print("="*60)


def build_cocoro2():
    """CocoroCore2のビルドを実行"""
    print("\n🚀 CocoroCore2 ビルドを開始します")
    print(f"アプリケーション名: {BUILD_CONFIG['app_name']}")
    print(f"出力形式: {'単一ファイル' if BUILD_CONFIG['onefile'] else 'フォルダ'}")
    print(f"コンソール: {'表示' if BUILD_CONFIG['console'] else '非表示'}")
    
    try:
        # 1. クリーンアップ
        clean_build_dirs()
        
        # 2. スペックファイル生成
        spec_file = create_spec_file()
        
        # 3. PyInstaller実行
        if not run_pyinstaller(spec_file):
            return False
        
        # 4. 追加ファイルコピー
        copy_additional_files()
        
        # 5. 起動スクリプト作成
        create_startup_script()
        
        # 6. サマリー表示
        print_build_summary()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ビルドエラー: {e}")
        return False


if __name__ == "__main__":
    success = build_cocoro2()
    sys.exit(0 if success else 1)
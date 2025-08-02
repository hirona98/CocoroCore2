# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CocoroCore2 - MemOS統合バックエンド

CocoroCore2は、MemOS（Memory Operating System）を統合したCocoroAIの次世代バックエンドシステムです。従来のCocoroCore + CocoroMemoryの組み合わせを単一のサービスに統合し、高度な記憶機能とリアルタイム応答を実現します。

## 開発環境セットアップ

### 必須要件
- Python 3.10以上
- **重要**: Python UTF-8モード必須（`python -X utf8`）
- Windows環境またはWSL2環境
- OpenAI API Key（設定ファイル経由）

### セットアップ手順

```bash
# 仮想環境作成
py -3.10 -m venv .venv

# 仮想環境活性化（WSL環境）
powershell.exe ".\.venv\Scripts\Activate"

# 仮想環境活性化（Windows環境）
.\.venv\Scripts\Activate

# 依存関係インストール
pip install -r requirements.txt
```

## 開発・実行コマンド

### 開発実行
```bash
# 開発環境で実行（UTF-8モード必須）
python -X utf8 src/main.py --environment development

# 本番環境で実行
python -X utf8 src/main.py --environment production

# 設定ファイル指定
python -X utf8 src/main.py --config-file ../UserData2/setting.json
```

### ビルド
```bash
# 自動ビルド実行
build.bat

# または手動実行
python build_cocoro2.py
```

## MemOSドキュメント
ソースコード: ../Reference/MemOS
ドキュメント: ../Reference/MemOS-Docs
GitHub: https://github.com/MemTensor/MemOS （Deepwiki対応）

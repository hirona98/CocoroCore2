# CocoroCore2 - MemOS Unified Backend

CocoroAI デスクトップマスコットのための統合バックエンドシステム。

## 🔧 インストール・セットアップ

### 1. 依存関係インストール

```bash
# 仮想環境作成
py -3.10 -m venv .venv
.\.venv\Scripts\Activate

# 依存関係インストール
pip install -r requirements.txt
```

## 🏃‍♂️ 実行方法

### 開発環境での実行

```bash
# 仮想環境アクティベート
.\.venv\Scripts\Activate

# CocoroCore2起動
python -X utf8 src/main.py --environment development
```

### 本番ビルド・実行

```bash
# ビルド実行
build.bat

# ビルド成果物実行
cd dist/CocoroCore2
start_cocoro_core2.bat
```

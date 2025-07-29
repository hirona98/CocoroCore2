# CocoroCore2 - MemOS Unified Backend

CocoroAI デスクトップマスコットのための統合バックエンドシステム。従来の CocoroCore（AIAvatarKit）と CocoroMemory（ChatMemory）の機能を、**MemOS**を基盤として統合・再構成した次世代システムです。

## 🚀 主要機能

### 統合された機能
- **MemOS統合**: 先進的な記憶管理システムによる高性能な対話エンジン
- **既存API互換**: CocoroDock・CocoroShell との完全互換性
- **統一プロセス**: 2つのプロセス → 1つのプロセスへの簡素化

### MemOS の利点
- **自動記憶管理**: 会話の自動保存・分類・関連付け
- **高性能検索**: 埋め込みベクトルによる高速類似検索
- **マルチユーザー対応**: ユーザーごとの独立した記憶空間
- **拡張可能設計**: モジュラー設計による将来機能拡張

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

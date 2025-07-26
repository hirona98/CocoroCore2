# CocoroCore2 - MemOS Unified Backend

CocoroAI デスクトップマスコットのための統合バックエンドシステム。従来の CocoroCore（AIAvatarKit）と CocoroMemory（ChatMemory）の機能を、**MemOS**を基盤として統合・再構成した次世代システムです。

## 🚀 主要機能

### 統合された機能
- **MemOS統合**: 先進的な記憶管理システムによる高性能な対話エンジン
- **既存API互換**: CocoroDock・CocoroShell との完全互換性
- **統一プロセス**: 2つのプロセス → 1つのプロセスへの簡素化
- **SSEストリーミング**: リアルタイム対話レスポンス

### MemOS の利点
- **自動記憶管理**: 会話の自動保存・分類・関連付け
- **高性能検索**: 埋め込みベクトルによる高速類似検索
- **マルチユーザー対応**: ユーザーごとの独立した記憶空間
- **拡張可能設計**: モジュラー設計による将来機能拡張

## 📋 システム要件

- **Python**: 3.10以上
- **OS**: Windows 10/11
- **メモリ**: 4GB以上推奨
- **API**: OpenAI API キー（ChatGPT/GPTモデル用）

## 🔧 インストール・セットアップ

### 1. 依存関係インストール

```bash
# 仮想環境作成
py -3.10 -m venv .venv
.\.venv\Scripts\Activate

# 依存関係インストール
pip install -r requirements.txt
```

### 2. 環境変数設定

```bash
# OpenAI API キー設定（必須）
set OPENAI_API_KEY=your_api_key_here
```

### 3. 設定ファイル

`config/development.json` を編集して環境に合わせて設定を調整：

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 55601
  },
  "mos_config": {
    "user_id": "hirona",
    "chat_model": {
      "backend": "openai",
      "config": {
        "model_name_or_path": "claude-3-5-sonnet-latest",
        "api_key": "${OPENAI_API_KEY}"
      }
    }
  }
}
```

## 🏃‍♂️ 実行方法

### 開発環境での実行

```bash
# 仮想環境アクティベート
.\.venv\Scripts\Activate

# CocoroCore2起動
python src/main.py --environment development
```

### 本番ビルド・実行

```bash
# ビルド実行
build.bat

# ビルド成果物実行
cd dist/CocoroCore2
start_cocoro_core2.bat
```

## 🌐 API エンドポイント

### 互換性エンドポイント（CocoroDock向け）

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/chat` | SSEストリーミング対話 |
| GET | `/health` | ヘルスチェック |
| POST | `/api/control` | システム制御 |

### MemOS純正エンドポイント

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/memos/chat` | 純正チャット（非ストリーミング） |
| POST | `/api/memory/search` | 記憶検索 |
| POST | `/api/memory/add` | 記憶追加 |

### 管理エンドポイント

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/sessions/statistics` | セッション統計 |
| GET | `/api/users/{user_id}/statistics` | ユーザー統計 |

## 🔄 移行について

### 従来システムとの違い

| 項目 | 従来（CocoroCore + CocoroMemory） | CocoroCore2 |
|------|--------------------------------|------------|
| プロセス数 | 2つ（Core + Memory） | 1つ（統合） |
| 記憶システム | ChatMemory（PostgreSQL） | MemOS |
| 通信方式 | HTTP通信（プロセス間） | 直接統合 |
| 記憶機能 | 基本的な保存・検索 | 高度な自動管理 |

### 既存設定の互換性

- CocoroDock: **完全互換** - 変更不要
- CocoroShell: **完全互換** - 変更不要  
- 設定ファイル: 部分互換 - `setting.json` の一部設定を継承

## 📁 ディレクトリ構成

```
CocoroCore2/
├── src/                    # ソースコード
│   ├── main.py            # エントリーポイント
│   ├── app.py             # FastAPIアプリケーション
│   ├── config.py          # 設定管理
│   ├── core_app.py        # MemOS統合コアアプリ
│   ├── core/              # コア機能
│   │   ├── session_manager.py  # セッション管理
│   │   └── user_manager.py     # ユーザー管理
│   └── api/               # API関連
│       ├── endpoints.py   # エンドポイント定義
│       ├── models.py      # データモデル
│       └── legacy_adapter.py   # 互換性レイヤー
├── config/                # 設定ファイル
│   ├── development.json   # 開発環境設定
│   └── default_memos_config.json  # MemOS設定
├── tests/                 # テストコード
├── requirements.txt       # 依存関係
├── pyproject.toml        # プロジェクト設定
├── build.bat             # ビルドスクリプト
└── README.md             # このファイル
```

## 🐛 トラブルシューティング

### よくあるエラー

1. **`OPENAI_API_KEY` が設定されていません**
   ```bash
   set OPENAI_API_KEY=your_api_key_here
   ```

2. **Python 3.10以上が必要**
   ```bash
   py -3.10 --version  # 3.10以上を確認
   ```

3. **MemOS初期化エラー**
   - `config/default_memos_config.json` の設定を確認
   - API キーが正しく設定されているか確認

4. **ポート55601が使用中**
   - `config/development.json` の `server.port` を変更

### ログ確認

```bash
# ログファイル確認
tail -f logs/cocoro_core2.log
```

## 📄 ライセンス

MIT License - 詳細は CocoroAI プロジェクトの LICENSE ファイルを参照

## 🤝 貢献

CocoroAI プロジェクトの一部として開発されています。

## 📚 関連ドキュメント

- [CocoroCore2設計書](./CocoroCore2設計書.md) - 詳細な設計仕様
- [MemOS公式ドキュメント](https://memos-docs.openmem.net/) - MemOS の詳細
- [CocoroAI全体概要](../CLAUDE.md) - プロジェクト全体の説明
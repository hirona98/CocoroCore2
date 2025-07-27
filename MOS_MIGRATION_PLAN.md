# CocoroCore2 MOS.simple() 移行計画案

## 概要

CocoroCore2では現在`MOS.simple()`を使用していますが、将来の多機能化に向けて正規のMOS APIへの移行を行います。
この文書では、機能を維持したまま安全に移行するための詳細な計画を示します。

## 現状分析

### 現在の実装状況

#### ファイル構成
- **メインファイル**: `src/core_app.py:17-280`
- **初期化箇所**: `src/core_app.py:34` - `self.mos = MOS.simple()`
- **使用メソッド**:
  - `self.mos.chat(query=query)` - チャット処理 (line 158)
  - `self.mos.add(memory_content=memory_content)` - 記憶追加 (line 193)
  - `self.mos.search(query=query)` - 記憶検索 (line 213)
  - `self.mos.get_all()` - 全記憶取得 (line 233)

#### 現在の設定管理
- 設定ファイル: 外部設定から`self.config.mos_config`で取得
- API Key設定: `_setup_memos_environment()`で環境変数設定
- シングルユーザーモード: `user_id`パラメータは無視される

#### 制限事項
- **シングルユーザーのみ**: マルチユーザー対応なし
- **設定の柔軟性不足**: `MOS.simple()`は内部で固定設定を使用
- **高度な機能へのアクセス不可**: MemCube、MOSProduct、カスタムMemory等

### 正規版MOSの機能

#### 主要な改善点
1. **マルチユーザー対応**: ユーザーごとの記憶管理
2. **設定の完全制御**: 全てのコンポーネントを詳細設定可能
3. **MemCube統合**: より高度なメモリ管理機能
4. **拡張性**: カスタムメモリタイプや外部ツール統合

#### API差分

| 機能 | `MOS.simple()` | 正規版MOS |
|------|----------------|-----------|
| 初期化 | `MOS.simple()` | `MOS(mos_config)` |
| ユーザー管理 | 不要（シングルユーザー） | `create_user(user_id)` |
| チャット | `chat(query)` | `chat(query, user_id)` |
| 記憶追加 | `add(memory_content)` | `add(memory_content, user_id)` |
| 検索 | `search(query)` | `search(query, user_id)` |
| 全取得 | `get_all()` | `get_all(user_id)` |

## 移行計画

### フェーズ1: 設定ファイル準備

#### 1.1 MOSConfig設定ファイル作成
新しい設定ファイル: `config/mos_config.json`

```json
{
  "user_id": "root", 
  "chat_model": {
    "backend": "openai",
    "config": {
      "model_name_or_path": "gpt-4o-mini",
      "temperature": 0.8,
      "max_tokens": 1024,
      "api_key": "{{ API_KEY }}",
      "api_base": "https://api.openai.com/v1"
    }
  },
  "mem_reader": {
    "backend": "simple_struct",
    "config": {
      "llm": {
        "backend": "openai",
        "config": {
          "model_name_or_path": "gpt-4o-mini",
          "temperature": 0.0,
          "api_key": "{{ API_KEY }}",
          "api_base": "https://api.openai.com/v1"
        }
      },
      "embedder": {
        "backend": "universal_api",
        "config": {
          "model_name_or_path": "text-embedding-3-small",
          "api_key": "{{ API_KEY }}",
          "api_base": "https://api.openai.com/v1"
        }
      }
    }
  },
  "max_turns_window": 20,
  "top_k": 5,
  "enable_textual_memory": true,
  "enable_activation_memory": false,
  "enable_parametric_memory": false
}
```

#### 1.2 設定読み込み機能拡張
`src/config.py`にMOSConfig読み込み機能を追加:

```python
def load_mos_config(self) -> dict:
    """MOSConfig設定を読み込み、テンプレート変数を置換"""
    # 設定ファイル読み込み
    # APIキーテンプレート置換
    # 戻り値として辞書形式で返す
```

### フェーズ2: コア実装変更

#### 2.1 `core_app.py` の修正

**Before**:
```python
def __init__(self, config: CocoroCore2Config):
    # MOS.simple()で簡単な統合
    self.mos = MOS.simple()
```

**After**:
```python
def __init__(self, config: CocoroCore2Config):
    # 正規版MOS初期化
    from memos.configs.mem_os import MOSConfig
    
    mos_config = MOSConfig.from_dict(config.mos_config)
    self.mos = MOS(mos_config)
    
    # デフォルトユーザー作成
    self.default_user_id = config.mos_config.get("user_id", "default")
    self.mos.create_user(user_id=self.default_user_id)
```

#### 2.2 メソッド更新

各メソッドで`user_id`パラメータ対応:

```python
def memos_chat(self, query: str, user_id: Optional[str] = None, context: Optional[Dict] = None) -> str:
    effective_user_id = user_id or self.default_user_id
    return self.mos.chat(query=query, user_id=effective_user_id)

def add_memory(self, content: str, user_id: Optional[str] = None, **context) -> None:
    effective_user_id = user_id or self.default_user_id
    self.mos.add(memory_content=content, user_id=effective_user_id)

def search_memory(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    effective_user_id = user_id or self.default_user_id
    return self.mos.search(query=query, user_id=effective_user_id)

def get_user_memories(self, user_id: Optional[str] = None) -> Dict[str, Any]:
    effective_user_id = user_id or self.default_user_id
    return self.mos.get_all(user_id=effective_user_id)
```

### フェーズ3: テストと検証

#### 3.1 単体テスト作成
```python
# tests/test_mos_integration.py
class TestMOSIntegration:
    def test_mos_initialization(self):
        """正規版MOS初期化テスト"""
        
    def test_chat_functionality(self):
        """チャット機能テスト"""
        
    def test_memory_operations(self):
        """記憶操作テスト（追加・検索・取得）"""
        
    def test_user_management(self):
        """ユーザー管理テスト"""
```

#### 3.2 統合テスト
- チャット機能の一貫性検証
- 記憶データの動作確認
- API互換性確認
- パフォーマンス検証

## リスク管理

### 主要リスク

#### 1. API互換性の問題
**リスク**: `MOS.simple()`と正規版MOSの動作差異
**対策**: 
- 詳細な単体テスト実装
- 移行前後での動作比較検証
- 段階的な機能確認

#### 2. パフォーマンス影響
**リスク**: 正規版MOSでの初期化・応答時間増加
**対策**:
- パフォーマンステスト実施
- 設定最適化
- 必要に応じてキャッシュ機能追加

#### 3. 設定管理の複雑化
**リスク**: 設定ファイルの肥大化・管理困難化
**対策**:
- 設定検証機能実装
- デフォルト値の適切な設定
- 詳細な設定ドキュメント作成

### 回避策

#### ロールバック計画
1. **バックアップ**: 移行前のコード・設定を保持
2. **バージョン管理**: Git履歴での変更点明確化
3. **データ保護**: 記憶データのバックアップ体制

#### 監視体制
- アプリケーションログでの動作監視
- エラー率・応答時間の継続監視
- 機能動作の確認

## スケジュール（想定）

| フェーズ | 期間 | 主要作業 |
|---------|------|----------|
| Phase 1 | 1週間 | 設定ファイル・設定読み込み機能実装 |
| Phase 2 | 1週間 | core_app.py修正・API変更対応 |
| Phase 3 | 1週間 | テスト作成・動作検証・パフォーマンス確認 |

**総期間**: 約3週間

## 将来の拡張可能性

### 正規版MOS移行後の追加機能

#### 1. マルチユーザー対応
- セッション管理との統合
- ユーザーごとの記憶分離
- 権限管理機能

#### 2. 高度なメモリ機能
- Tree Text Memory（構造化記憶）
- Activation Memory（KVキャッシュ）
- カスタムMemCube開発

#### 3. 外部ツール統合
- MemOS MCPプロトコル対応
- プラグインアーキテクチャ
- スケジューラー機能

## 結論

この移行計画は以下の原則に基づいています：

1. **シンプル性**: 不要な複雑さを排除したストレートな移行
2. **安全性**: 詳細なテスト・検証による既存機能の保護
3. **拡張性**: 将来の機能追加への基盤作り
4. **保守性**: クリーンなアーキテクチャ設計

ストレートかつ計画的な実行により、リスクを最小化しながらMOS.simple()からの脱却を実現します。
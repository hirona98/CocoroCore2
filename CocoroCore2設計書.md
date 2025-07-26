# CocoroCore2 詳細設計書
## MemOSベース記憶統合システム

### バージョン: 1.1.0
### 作成日: 2025-07-26
### 最終更新: 2025-07-26 (記憶管理統一化)

---

## 1. プロジェクト概要

### 1.1 目的と背景

CocoroCore2は、現在のCocoroCore（AIAvatarKit使用）とCocoroMemory（ChatMemory使用）の機能を、**MemOS**を基盤として統合・再構成する新システムです。

**移行の目的:**
- **記憶システムの高度化**: MemOSの先進的な記憶管理機能を活用
- **アーキテクチャの単純化**: 2つのコンポーネントを1つに統合し保守性向上
- **性能の向上**: MemOSの高性能な記憶検索・管理機能を利用
- **将来拡張性**: モジュラー設計による機能拡張の容易さ

### 1.2 現行システム分析

#### 現行CocoroCore（AIAvatarKit）
```
機能:
- FastAPI HTTP サーバー（ポート: 55601）
- LLM対話エンジン（多プロバイダー対応）
- Speech-To-Speech パイプライン
- ChatMemory との非同期通信
- MCP（Model Context Protocol）ツール統合
- セッション管理（5分タイムアウト）

技術スタック:
- Python 3.10
- aiavatar（AIAvatarKit）フレームワーク
- FastAPI + uvicorn
- httpx（非同期HTTP通信）
- litellm（マルチLLMプロバイダー）
```

#### 現行CocoroMemory（ChatMemory）
```
機能:
- PostgreSQL ベース長期記憶
- 埋め込みベクトルによる類似検索
- 会話履歴の要約・分類・検索
- chatmemory ライブラリベース

技術スタック:
- Python 3.10
- PostgreSQL + pgvector
- chatmemory ライブラリ
- FastAPI（独立サーバー）
```

#### 現行システムの課題
1. **2つのプロセス管理の複雑さ**: CocoroCore と CocoroMemory の分離
2. **通信オーバーヘッド**: HTTP通信による記憶操作の遅延
3. **依存関係管理**: 異なるライブラリ（aiavatar vs chatmemory）の並行管理
4. **記憶機能の制限**: chatmemorycに比べMemOSのより高度な記憶管理機能

### 1.3 MemOSの特徴と利点

MemOS（Memory Operating System for LLMs）は大規模言語モデル向けの記憶管理システムです。

#### 主要機能
```
記憶タイプ:
- Textual Memory: 構造化・非構造化テキスト知識
- Activation Memory: KVキャッシュによる推論高速化
- Parametric Memory: LoRA重みなどモデル適応パラメータ

アーキテクチャ:
- MemCube: モジュラー記憶アーキテクチャ
- Memory-Augmented Generation (MAG): 統一API
- 拡張可能設計: カスタムメモリモジュール対応
```

---

## 2. CocoroCore2 設計方針

### 2.1 設計原則

1. **統合性**: 記憶機能を内包した単一プロセス設計
2. **互換性**: 既存のCocoroDock・CocoroShellとの連携維持
3. **シンプル性**: 複雑な通信を廃止し、直接的な記憶アクセス
4. **拡張性**: MemOSのモジュラー設計を活用した機能拡張
5. **性能**: MemOSの高性能記憶検索による応答速度向上

### 2.2 移行戦略

#### フェーズ1: 基盤構築
- MemOSベースの基本チャット機能実装
- 既存API互換レイヤー作成
- 基本記憶機能（検索・追加）実装

#### フェーズ2: 高度機能移行
- STT/VAD機能の統合
- MCP ツール統合
- 既存記憶データの移行

#### フェーズ3: 最適化
- パフォーマンス最適化
- 新機能追加（MemOS固有機能活用）

---

## 3. システムアーキテクチャ

### 3.1 全体構成

```
 ┌────────────────┐    ┌─────────────────────────────────┐    ┌─────────────────┐
 │   CocoroDock   │◄──►│        CocoroCore2              │◄──►│  CocoroShell    │
 │  (WPF UI)      │    │    (FastAPI + MemOS)            │    │ (Unity/VRM)     │
 │  Port: 55600   │    │      Port: 55601                │    │  Port: 55605    │
 │                │    │                                 │    └─────────────────┘
 │                │    │ ┌─────────────────────────────┐ │
 │  Notification  │    │ │     MemOS Core              │ │
 │    Server      │    │ │  - Memory Management        │ │
 │  Port: 55604   │    │ │  - Chat Integration         │ │
 │                │    │ │  - Multi-User Support       │ │
 │                │    │ │  - MemCube Management       │ │
 └────────────────┘    │ └─────────────────────────────┘ │
                       │                                 │
                       │ ┌─────────────────────────────┐ │             
                       │ │    Additional Features      │ │             
                       │ │  - STT/VAD Pipeline         │ │             
                       │ │  - MCP Tool Integration     │ │             
                       │ │  - Session Management       │ │             
                       │ └─────────────────────────────┘ │             
                       └─────────────────────────────────┘             
```

### 3.2 コンポーネント設計

#### 3.2.1 MemOS統合レイヤー
```python
# CocoroCore2メインアプリケーション - MemOS直接統合
class CocoroCore2App:
    """MemOSを直接統合したCocoroCore2アプリケーション"""
    
    def __init__(self, config: CocoroCore2Config):
        # MemOSを直接統合
        self.mos = MOS(config.mos_config)
        self.config = config
        self.session_manager = SessionManager()
        self.voice_processor = VoiceProcessor()
        self.mcp_tools = MCPToolsManager()
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """メモリ統合チャット"""
        
    async def add_memory(self, content: str, user_id: str) -> None:
        """記憶追加"""
        
    async def search_memory(self, query: str, user_id: str) -> List[Memory]:
        """記憶検索"""
```

#### 3.2.2 互換性レイヤー
```python
# 既存API互換性維持
class LegacyAPIAdapter:
    """既存CocoroCore APIとの互換性を提供"""
    
    async def handle_legacy_chat(self, request: LegacyChatRequest) -> SSEResponse:
        """既存/chatエンドポイントの処理"""
        
    async def handle_legacy_health(self) -> HealthResponse:
        """既存/healthエンドポイントの処理"""
        
    async def handle_legacy_control(self, command: ControlCommand) -> StandardResponse:
        """既存/api/controlエンドポイントの処理"""
```

#### 3.2.3 音声処理統合
```python
# 音声処理パイプライン
class SpeechToSpeechPipeline:
    """STT → LLM → TTS パイプライン（CocoroShell連携）"""
    
    def __init__(self, config: STSConfig):
        self.vad = VADManager(config.vad)
        self.stt = STTManager(config.stt)
        self.shell_client = CocoroShellClient(config.shell_port)
    
    async def process_voice_input(self, audio_data: bytes) -> None:
        """音声入力の処理"""
```

### 3.3 データフロー

#### 3.3.1 通常チャット
```
1. CocoroDock → POST /chat → CocoroCore2
2. CocoroCore2 → MemOS → 記憶検索・LLM推論
3. CocoroCore2 → SSE レスポンス → CocoroDock
4. CocoroCore2 → 記憶自動保存 → MemOS
5. CocoroCore2 → 音声合成要求 → CocoroShell
```

#### 3.3.2 音声対話
```
1. 音声入力 → VAD → STT → テキスト変換
2. テキスト → 通常チャットフロー
3. レスポンステキスト → CocoroShell → TTS → 音声出力
```

#### 3.3.3 記憶操作
```
1. MemOS内部 → 記憶検索・分類・要約
2. 自動記憶管理 → Memory Scheduler
3. 記憶永続化 → MemCube（JSON/SQLite/ベクトルDB）
```

---

## 4. API設計

### 4.1 外部API（CocoroDock/CocoroShell向け）

#### 4.1.1 チャットエンドポイント
```http
POST /chat
Content-Type: application/json
Accept: text/event-stream

# リクエスト
{
  "user_id": "hirona",
  "session_id": "session_123",
  "text": "こんにちは",
  "metadata": {
    "image_description": "猫の写真",
    "image_category": "animal",
    "image_mood": "cute"
  }
}

# レスポンス（SSE）
data: {"type": "content", "content": "こんにちは！", "finished": false}
data: {"type": "content", "content": "今日はどうされましたか？", "finished": false}
data: {"type": "memory", "action": "saved", "details": "会話を記憶しました"}
data: {"type": "content", "content": "", "finished": true}
```

#### 4.1.2 記憶管理エンドポイント
```http
# 記憶検索
POST /api/memory/search
{
  "user_id": "hirona",
  "query": "ユーザーの好きな食べ物",
  "limit": 5
}

# 記憶追加
POST /api/memory/add
{
  "user_id": "hirona", 
  "content": "hirona は猫が好きで、2匹飼っている",
  "category": "personal_info"
}

# 記憶削除
DELETE /api/memory/{memory_id}?user_id=hirona
```

#### 4.1.3 システム制御エンドポイント
```http
# ヘルスチェック
GET /health
{
  "status": "healthy",
  "version": "2.0.0",
  "character": "つくよみちゃん", 
  "memory_enabled": true,
  "llm_model": "claude-3-5-sonnet-latest",
  "active_sessions": 2,
  "memos_status": {
    "users": 1,
    "mem_cubes": 3,
    "total_memories": 1250
  }
}

# システム制御
POST /api/control
{
  "command": "shutdown|sttControl|microphoneControl",
  "params": {...},
  "reason": "操作理由"
}
```

### 4.2 内部API（MemOS統合）

#### 4.2.1 MemOS設定
```python
# CocoroCore2専用MemOS設定
mos_config = {
    "user_id": "hirona",
    "chat_model": {
        "backend": "openai",  # openai, ollama, huggingface
        "config": {
            "model_name_or_path": "claude-3-5-sonnet-latest",
            "temperature": 0.7,
            "max_tokens": 4096
        }
    },
    "mem_reader": {
        "backend": "simple_struct",
        "config": {
            "llm": {...},
            "embedder": {
                "backend": "openai",
                "config": {
                    "model_name_or_path": "text-embedding-3-small"
                }
            },
            "chunker": {
                "backend": "sentence",
                "config": {
                    "chunk_size": 512,
                    "chunk_overlap": 128
                }
            }
        }
    },
    "max_turns_window": 20,
    "top_k": 5,
    "enable_textual_memory": true,
    "enable_activation_memory": false,  # 将来拡張用
    "enable_parametric_memory": false   # 将来拡張用
}
```

#### 4.2.2 MemOS直接統合
```python
# MemOSを直接統合 - シンプルで強力
class CocoroCore2App:
    """MemOSを直接活用したCocoroCore2メインアプリケーション"""
    
    def __init__(self, config: CocoroCore2Config):
        # MemOSを直接初期化
        self.mos = MOS(config.mos_config)
        self.config = config
        
    async def chat_request(self, message: str, user_id: str, **context):
        """チャットリクエスト処理 - MemOS統合チャット"""
        
        # MemOSの統合チャット機能を直接利用
        # - 自動記憶検索
        # - LLM推論
        # - 記憶保存
        # - 分類・関連付け
        response = await self.mos.chat(
            message=message,
            user_id=user_id,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "character": self.config.character_name,
                **context
            }
        )
        
        return response
    
    async def add_memory(self, content: str, user_id: str, **context):
        """記憶追加 - MemOSが全自動処理"""
        await self.mos.add(
            memory_content=content,
            user_id=user_id,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "character": self.config.character_name,
                **context
            }
        )
    
    async def search_memory(self, query: str, user_id: str):
        """記憶検索 - MemOSの高性能検索エンジン"""
        return await self.mos.search(query=query, user_id=user_id)
```

---

## 5. 実装仕様

### 5.1 ディレクトリ構造

```
CocoroCore2/
├── src/
│   ├── main.py                    # エントリーポイント
│   ├── app.py                     # FastAPIアプリケーション
│   ├── config.py                  # 設定管理
│   ├── core/
│   │   ├── session_manager.py     # セッション管理
│   │   └── user_manager.py        # ユーザー管理
│   ├── api/
│   │   ├── endpoints.py           # メインAPI
│   │   ├── legacy_adapter.py      # 互換性レイヤー
│   │   └── models.py              # APIモデル
│   ├── voice/
│   │   ├── pipeline.py            # STS パイプライン
│   │   ├── vad_manager.py         # VAD管理
│   │   └── stt_manager.py         # STT管理
│   ├── tools/
│   │   ├── mcp_integration.py     # MCP統合
│   │   └── cocoro_tools.py        # CocoroAI固有ツール
│   └── utils/
│       ├── shell_client.py        # CocoroShell通信
│       └── logging.py             # ログ管理
├── config/
│   ├── default_memos_config.json  # デフォルトMemOS設定
│   └── development.json           # 開発環境設定
├── tests/                         # テストコード
├── requirements.txt               # 依存関係
├── pyproject.toml                # プロジェクト設定
├── build.bat                     # ビルドスクリプト
└── README.md                     # ドキュメント
```

### 5.2 主要クラス設計

#### 5.2.1 CocoroCore2App
```python
class CocoroCore2App:
    """CocoroCore2 メインアプリケーションクラス"""
    
    def __init__(self, config_path: str):
        self.config = CocoroCore2Config.load(config_path)
        # MemOSを直接統合
        self.mos = MOS(self.config.mos_config)
        self.session_manager = SessionManager()
        self.voice_pipeline = SpeechToSpeechPipeline(self.config.sts)
        self.mcp_tools = MCPToolsManager(self.config.mcp)
        
    async def startup(self):
        """アプリケーション起動処理"""
        # MemOS初期化は不要（自動的に処理される）
        await self.voice_pipeline.initialize()
        await self.mcp_tools.initialize()
        
    async def shutdown(self):
        """アプリケーション終了処理"""
        await self.memos_integrator.cleanup()
        await self.voice_pipeline.cleanup()
```

#### 5.2.2 CocoroCore2アプリケーション詳細
```python
# CocoroCore2アプリケーションの詳細実装
class CocoroCore2App:
    """MemOS直接統合による統一アプリケーション"""
    
    def __init__(self, config: CocoroCore2Config):
        # MemOSを直接統合 - 中間レイヤー不要
        self.mos = MOS(config.mos_config)
        self.config = config
        
    async def handle_chat_request(self, 
                                 message: str, 
                                 user_id: str,
                                 context: Optional[Dict] = None) -> AsyncIterator[str]:
        """統合チャット処理 - MemOSが全自動管理"""
        
        # MemOSによる記憶統合チャット（ストリーミング対応）
        async for chunk in self.mos.chat_stream(
            message=message,
            user_id=user_id,
            metadata={
                "character": self.config.character_name,
                "timestamp": datetime.now().isoformat(),
                **(context or {})
            }
        ):
            yield chunk
            
        # 記憶は自動的に保存・分類・関連付けされる
        
    async def add_contextual_memory(self, content: str, user_id: str, **context):
        """コンテキスト記憶追加"""
        await self.mos.add(
            memory_content=content,
            user_id=user_id,
            metadata={
                "character": self.config.character_name,
                "timestamp": datetime.now().isoformat(),
                **context
            }
        )
        
    async def search_user_memories(self, query: str, user_id: str):
        """ユーザー記憶検索"""
        return await self.mos.search(query=query, user_id=user_id)
```

### 5.3 設定管理

#### 5.3.1 統合設定ファイル
```json
{
  "version": "2.0.0",
  "server": {
    "host": "127.0.0.1",
    "port": 55601,
    "workers": 1
  },
  "mos_config": {
    "user_id": "root",
    "chat_model": {
      "backend": "openai",
      "config": {
        "model_name_or_path": "claude-3-5-sonnet-latest",
        "temperature": 0.7,
        "max_tokens": 4096,
        "api_key": "${OPENAI_API_KEY}"
      }
    },
    "mem_reader": {
      "backend": "simple_struct", 
      "config": {
        "llm": {
          "backend": "openai",
          "config": {
            "model_name_or_path": "gpt-4o-mini",
            "temperature": 0.0
          }
        },
        "embedder": {
          "backend": "openai",
          "config": {
            "model_name_or_path": "text-embedding-3-small"
          }
        }
      }
    },
    "max_turns_window": 20,
    "top_k": 5,
    "enable_textual_memory": true
  },
  "speech": {
    "enabled": true,
    "vad": {
      "auto_adjustment": true,
      "fixed_threshold": -40.0
    },
    "stt": {
      "engine": "openai",
      "model": "whisper-1",
      "language": "ja"
    }
  },
  "shell_integration": {
    "port": 55605,
    "auto_tts": true
  },
  "mcp": {
    "enabled": true,
    "config_file": "CocoroAiMcp.json"
  }
}
```

---

## 6. データベース・記憶設計

### 6.1 MemOS記憶構造

#### 6.1.1 MemCube設計
```python
# CocoroAI専用MemCube構成
{
  "cube_id": "cocoro_main",
  "textual_memory": {
    "backend": "general_text",  # または "tree_text"（Neo4j必要）
    "config": {
      "embedder": "openai/text-embedding-3-small",
      "vector_db": "qdrant",  # または "faiss"
      "max_memories": 10000
    }
  },
  "metadata": {
    "character": "つくよみちゃん",
    "created_date": "2025-07-26",
    "version": "2.0.0"
  }
}
```

#### 6.1.2 MemOS直接利用
```python
# MemOSを直接利用 - 中間レイヤー不要
class CocoroMemOSIntegrator:
    """MemOSの強力なAPIを直接活用"""
    
    def __init__(self, config: CocoroCore2Config):
        # MemOSを直接初期化
        self.mos = MOS(config.mos_config)
        self.user_mapping = {}
        
    async def ensure_user(self, user_id: str) -> str:
        """ユーザー確保（必要時のみ作成）"""
        if user_id not in self.user_mapping:
            await self.mos.create_user(user_id=user_id)
            self.user_mapping[user_id] = user_id
        return user_id
        
    async def chat_with_memory(self, message: str, user_id: str, **context):
        """記憶統合チャット - MemOSが全自動処理"""
        user_id = await self.ensure_user(user_id)
        
        # MemOSが自動的に：
        # - 関連記憶を検索
        # - LLM推論を実行  
        # - 会話を記憶に保存
        # - 記憶を分析・分類・関連付け
        return await self.mos.chat(
            message=message,
            user_id=user_id,
            metadata=context
        )
        
    async def add_contextual_memory(self, content: str, user_id: str, **context):
        """コンテキスト付き記憶追加"""
        user_id = await self.ensure_user(user_id)
        
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "character": "つくよみちゃん",
            **context
        }
        
        # MemOSの自動記憶管理
        await self.mos.add(
            memory_content=content,
            user_id=user_id,
            metadata=metadata
        )
        
    async def search_memories(self, query: str, user_id: str):
        """記憶検索 - MemOSの高性能検索"""
        user_id = await self.ensure_user(user_id)
        return await self.mos.search(query=query, user_id=user_id)
```

---

## 7. セキュリティ・パフォーマンス

シンプルさを優先するために考慮しないが、非同期処理による高速化程度は行う。

---

## 9. 運用・メンテナンス

### 9.1 ログ・監視

#### 9.1.1 構造化ログ
```python
# 構造化ログ設定
logging_config = {
    "version": 1,
    "formatters": {
        "json": {
            "format": {
                "timestamp": "%(asctime)s",
                "level": "%(levelname)s", 
                "component": "%(name)s",
                "message": "%(message)s",
                "user_id": "%(user_id)s",
                "session_id": "%(session_id)s"
            }
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/cocoro_core2.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    }
}
```

#### 9.1.2 メトリクス収集
```python
# アプリケーションメトリクス
class CocoroCore2Metrics:
    """パフォーマンス・使用状況メトリクス"""
    
    def __init__(self):
        self.chat_requests = Counter()
        self.memory_operations = Counter()
        self.response_times = Histogram()
        self.active_sessions = Gauge()
        
    def record_chat_request(self, user_id: str, duration: float):
        """チャットリクエストの記録"""
        
    def record_memory_search(self, query_type: str, duration: float):
        """記憶検索の記録"""
```

### 9.2 設定管理

#### 9.2.1 環境別設定
```
config/
├── base.json              # 基本設定
├── development.json       # 開発環境
├── production.json        # 本番環境
└── user_overrides.json    # ユーザー固有設定
```

#### 9.2.2 動的設定更新
```python
# 設定のホットリロード
class ConfigManager:
    """設定管理・動的更新"""
    
    async def reload_config(self, config_path: str):
        """設定のリロード（サーバー再起動なし）"""
        
    async def update_llm_config(self, new_config: LLMConfig):
        """LLM設定の動的更新"""
```

---

## 10. 移行・展開計画

### 10.1 移行手順

#### Phase 1: 基盤準備（1-2週間）
```
1. 開発環境構築
   - MemOS環境セットアップ
   - 基本設定作成
   - ビルドパイプライン構築

2. 基本機能実装
   - FastAPI基盤
   - MemOS統合
   - 簡単なチャット機能
```

#### Phase 2: 互換性実装（2-3週間）
```
1. 既存API互換性
   - /chat エンドポイント
   - /health エンドポイント  
   - /api/control エンドポイント

2. CocoroDock連携テスト
   - SSEストリーミング（必要性があれば）
   - 基本チャット動作確認
```

#### Phase 3: 高度機能（3-4週間）
```
1. 音声機能
   - STT/VAD統合
   - CocoroShell連携

2. 記憶機能
   - 高度検索・分類

3. MCP統合
   - ツール機能移行
```

---

## 11. 参考情報

### 11.1 技術参考

#### MemOS公式ドキュメント
- Documentation: https://memos-docs.openmem.net/
- GitHub: https://github.com/MemTensor/MemOS
- API Reference: https://memos-docs.openmem.net/docs/api/

#### 既存システムドキュメント
- CocoroCore仕様書: ./CocoroCore/仕様書.md
- CocoroMemory仕様書: ./CocoroMemory/README.md
- AIAvatarKit: ./Reference/aiavatarkit

### 11.2 設定例

```json
{
  "mos_config": {
    "user_id": "hirona",
    "chat_model": {
      "backend": "openai",
      "config": {
        "model_name_or_path": "claude-3-5-sonnet-latest",
        "temperature": 0.7,
        "max_tokens": 4096
      }
    },
    "mem_reader": {
      "backend": "simple_struct",
      "config": {
        "llm": {
          "backend": "openai",
          "config": {
            "model_name_or_path": "gpt-4o-mini",
            "temperature": 0.0
          }
        },
        "embedder": {
          "backend": "openai",
          "config": {
            "model_name_or_path": "text-embedding-3-small"
          }
        }
      }
    },
    "top_k": 10,
    "max_turns_window": 30,
    "enable_textual_memory": true
  }
}
```

---

## 12. まとめ

CocoroCore2は、MemOSの先進的な記憶管理機能を活用し、既存システムの課題を解決する統合ソリューションです。

### 主要な利点
1. **統合による単純化**: 2プロセス → 1プロセス
2. **記憶機能の大幅向上**: MemOSの高性能記憶システム
3. **既存機能の完全継承**: 互換性レイヤーによる安全な移行
4. **将来拡張性**: MemOSのモジュラー設計活用

### 実装のポイント  
1. **段階的移行**: リスクを最小化する段階的アプローチ
2. **互換性重視**: 既存CocoroDock/CocoroShellとの連携維持
3. **パフォーマンス**: MemOSの高速記憶検索活用
4. **保守性**: シンプルで分かりやすいアーキテクチャ

この設計書に基づいて実装することで、より高性能で保守しやすいCocoroAIシステムを実現できます。

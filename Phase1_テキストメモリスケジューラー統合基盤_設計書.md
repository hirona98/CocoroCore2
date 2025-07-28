# Phase 1: テキストメモリスケジューラー統合基盤 - 設計書

## 📅 作成日: 2025-01-28
## 🎯 目的: CocoroCore2にMemOSテキストメモリスケジューラーの統合基盤を構築

---

## 🔍 調査結果概要

### 現在の状況
- **CocoroCore2App**: 既にMOSインスタンスを初期化・保持済み
- **設定管理**: `CocoroCore2Config`で`mos_config`を辞書形式で管理
- **ライフサイクル**: `startup()`/`shutdown()`でアプリケーション管理
- **アクティベーションメモリ**: 既に無効化済み（`enable_activation_memory: false`）

### MemOSスケジューラー要件
- **設定クラス**: `GeneralSchedulerConfig`が必要
- **ファクトリー**: `SchedulerConfigFactory`経由で作成
- **初期化**: `initialize_modules(chat_llm, process_llm)`でLLM設定
- **ライフサイクル**: `start()`/`stop()`で管理

---

## 🏗️ Phase 1 設計詳細

### 1. 設定拡張

#### 1.1 config.py の拡張

**新規クラス追加**:
```python
class MemSchedulerConfig(BaseModel):
    """メモリスケジューラー設定"""
    enabled: bool = False
    top_k: int = 5
    context_window_size: int = 5
    enable_act_memory_update: bool = False
    enable_parallel_dispatch: bool = False
    thread_pool_max_workers: int = 3
    consume_interval_seconds: int = 2
    act_mem_update_interval: int = 300
    
    # テキストメモリ特化設定
    text_memory_optimization: Dict[str, Any] = Field(default_factory=lambda: {
        "enable_deduplication": True,
        "similarity_threshold": 0.95,
        "working_memory_size": 20,
        "long_term_memory_capacity": 10000,
        "user_memory_capacity": 10000
    })
```

**CocoroCore2Config の拡張**:
```python
class CocoroCore2Config(BaseModel):
    # 既存フィールド...
    mem_scheduler: MemSchedulerConfig = Field(default_factory=MemSchedulerConfig)
```

#### 1.2 default_memos_config.json の拡張

```json
{
  "existing_config": "...",
  "mem_scheduler": {
    "enabled": true,
    "top_k": 5,
    "context_window_size": 5,
    "enable_act_memory_update": false,
    "enable_parallel_dispatch": false,
    "thread_pool_max_workers": 3,
    "consume_interval_seconds": 2,
    "act_mem_update_interval": 300,
    "text_memory_optimization": {
      "enable_deduplication": true,
      "similarity_threshold": 0.95,
      "working_memory_size": 20,
      "long_term_memory_capacity": 10000,
      "user_memory_capacity": 10000
    }
  }
}
```

### 2. 新規ファイル作成

#### 2.1 src/core/text_memory_scheduler.py

**目的**: MemOSスケジューラーとCocoroCore2の統合レイヤー

```python
"""
CocoroCore2 テキストメモリスケジューラー統合モジュール

MemOSのGeneralSchedulerをCocoroCore2に統合するためのレイヤー
"""

import logging
from typing import Optional, Dict, Any

from memos.configs.mem_scheduler import SchedulerConfigFactory, GeneralSchedulerConfig
from memos.mem_scheduler.scheduler_factory import SchedulerFactory
from memos.mem_scheduler.general_scheduler import GeneralScheduler
from memos.mem_scheduler.modules.schemas import (
    ScheduleMessageItem, 
    QUERY_LABEL, 
    ANSWER_LABEL, 
    ADD_LABEL
)
from memos.llms.base import BaseLLM

from ..config import CocoroCore2Config


class TextMemorySchedulerManager:
    """テキストメモリスケジューラー管理クラス"""
    
    def __init__(self, config: CocoroCore2Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.scheduler: Optional[GeneralScheduler] = None
        self.is_initialized = False
        self.is_running = False
    
    def initialize(self, chat_llm: BaseLLM, process_llm: Optional[BaseLLM] = None):
        """スケジューラーを初期化"""
        # 省略: 詳細実装
    
    async def start(self):
        """スケジューラーを開始"""
        # 省略: 詳細実装
    
    async def stop(self):
        """スケジューラーを停止"""
        # 省略: 詳細実装
    
    def submit_query_message(self, user_id: str, content: str, mem_cube):
        """クエリメッセージを送信"""
        # 省略: 詳細実装
    
    def submit_answer_message(self, user_id: str, content: str, mem_cube):
        """応答メッセージを送信"""
        # 省略: 詳細実装
    
    def submit_add_message(self, user_id: str, content: str, mem_cube):
        """記憶追加メッセージを送信"""
        # 省略: 詳細実装
```

#### 2.2 src/core/scheduler_config.py

**目的**: スケジューラー設定の変換・管理

```python
"""
MemOSスケジューラー設定管理モジュール

CocoroCore2ConfigからMemOSスケジューラー設定への変換を担当
"""

from typing import Dict, Any
from memos.configs.mem_scheduler import SchedulerConfigFactory, GeneralSchedulerConfig

from ..config import CocoroCore2Config


def create_scheduler_config_factory(config: CocoroCore2Config) -> SchedulerConfigFactory:
    """CocoroCore2ConfigからSchedulerConfigFactoryを作成"""
    
    scheduler_config_dict = {
        "top_k": config.mem_scheduler.top_k,
        "context_window_size": config.mem_scheduler.context_window_size,
        "enable_act_memory_update": config.mem_scheduler.enable_act_memory_update,
        "enable_parallel_dispatch": config.mem_scheduler.enable_parallel_dispatch,
        "thread_pool_max_workers": config.mem_scheduler.thread_pool_max_workers,
        "consume_interval_seconds": config.mem_scheduler.consume_interval_seconds,
        "act_mem_update_interval": config.mem_scheduler.act_mem_update_interval,
    }
    
    return SchedulerConfigFactory(
        backend="general_scheduler",
        config=scheduler_config_dict
    )


def validate_scheduler_config(config: CocoroCore2Config) -> bool:
    """スケジューラー設定の妥当性を検証"""
    # 省略: 詳細実装
    return True
```

### 3. 既存ファイル修正

#### 3.1 src/core_app.py の修正

**追加インポート**:
```python
from .core.text_memory_scheduler import TextMemorySchedulerManager
```

**CocoroCore2App クラスの拡張**:
```python
class CocoroCore2App:
    def __init__(self, config: CocoroCore2Config):
        # 既存の初期化...
        
        # テキストメモリスケジューラー初期化
        self.text_memory_scheduler: Optional[TextMemorySchedulerManager] = None
        if config.mem_scheduler.enabled:
            self.text_memory_scheduler = TextMemorySchedulerManager(config)
    
    async def startup(self):
        """アプリケーション起動処理"""
        try:
            # 既存の起動処理...
            
            # テキストメモリスケジューラー初期化・開始
            if self.text_memory_scheduler:
                self.logger.info("Initializing text memory scheduler...")
                # chat_llmを取得（MOSから）
                chat_llm = self._get_chat_llm_from_mos()
                self.text_memory_scheduler.initialize(chat_llm)
                await self.text_memory_scheduler.start()
                self.logger.info("Text memory scheduler started")
            
        except Exception as e:
            self.logger.error(f"Failed to start CocoroCore2App: {e}")
            raise
    
    async def shutdown(self):
        """アプリケーション終了処理"""
        try:
            # テキストメモリスケジューラー停止
            if self.text_memory_scheduler and self.text_memory_scheduler.is_running:
                self.logger.info("Stopping text memory scheduler...")
                await self.text_memory_scheduler.stop()
                self.logger.info("Text memory scheduler stopped")
            
            # 既存の終了処理...
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def _get_chat_llm_from_mos(self) -> BaseLLM:
        """MOSからchat_llmインスタンスを取得"""
        # 省略: MOSの内部からLLMインスタンスを取得
        pass
```

---

## 📁 ファイル構成変更

### 新規作成ファイル
```
CocoroCore2/
├── src/
│   ├── core/
│   │   ├── text_memory_scheduler.py      # NEW: スケジューラー統合管理
│   │   └── scheduler_config.py           # NEW: 設定変換・管理
│   └── config.py                         # MODIFIED: 設定クラス拡張
├── config/
│   └── default_memos_config.json         # MODIFIED: スケジューラー設定追加
└── Phase1_実装詳細.md                    # NEW: 実装詳細ドキュメント
```

### 修正ファイル
- `src/core_app.py`: スケジューラー統合
- `src/config.py`: 設定クラス拡張
- `config/default_memos_config.json`: デフォルト設定追加

---

## 🔧 実装手順

### Step 1: 設定拡張
1. `src/config.py`に`MemSchedulerConfig`クラスを追加
2. `config/default_memos_config.json`に設定項目を追加
3. 設定の読み込み・検証機能を拡張

### Step 2: スケジューラー統合モジュール作成
1. `src/core/scheduler_config.py`を作成
2. `src/core/text_memory_scheduler.py`を作成
3. 設定変換・スケジューラー管理機能を実装

### Step 3: CocoroCore2App統合
1. `src/core_app.py`にスケジューラー統合
2. 初期化・ライフサイクル管理の実装
3. MOSからLLMインスタンス取得の実装

### Step 4: テスト・検証
1. 設定読み込みのテスト
2. スケジューラー初期化のテスト
3. ライフサイクル管理のテスト

---

## 🎯 Phase 1 完了基準

### 必須項目
- [ ] スケジューラー設定の追加・読み込み
- [ ] `TextMemorySchedulerManager`の基本実装
- [ ] CocoroCore2Appでのスケジューラー初期化・開始・停止
- [ ] エラーハンドリングとログ出力

### 確認項目
- [ ] 設定ファイルからスケジューラー設定が正常に読み込まれる
- [ ] スケジューラーが正常に初期化される
- [ ] アプリケーション起動・終了時にスケジューラーが適切に管理される
- [ ] 既存のMOS機能に影響を与えない

---

## 📝 注意事項

### 技術的考慮点
1. **スレッドセーフティ**: スケジューラーは別スレッドで動作するため、適切な同期処理が必要
2. **エラーハンドリング**: スケジューラーエラーがメインアプリケーションを停止させないよう注意
3. **リソース管理**: スケジューラー停止時の適切なリソースクリーンアップ
4. **後方互換性**: 既存のMOS機能への影響を最小限に抑制

### 設計原則
1. **段階的統合**: 既存機能を破綻させずに段階的に統合
2. **設定駆動**: スケジューラーの有効/無効を設定で制御
3. **ログ重視**: デバッグのための詳細なログ出力
4. **テスト可能性**: 各コンポーネントの独立したテスト可能性を確保

---

*この設計書はPhase 1実装のガイドラインとして使用します。実装進行に応じて更新される場合があります。*
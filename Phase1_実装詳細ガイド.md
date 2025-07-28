# Phase 1: 実装詳細ガイド

## 📅 作成日: 2025-01-28
## 🎯 目的: Phase 1設計書の詳細実装ガイド

---

## 🚀 実装ステップ詳細

### Step 1: 設定拡張の実装

#### 1.1 config.py の修正

**追加する内容**:

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

**CocoroCore2Config クラスに追加**:
```python
class CocoroCore2Config(BaseModel):
    # 既存フィールド...
    mem_scheduler: MemSchedulerConfig = Field(default_factory=MemSchedulerConfig)
```

#### 1.2 default_memos_config.json の修正

**追加する内容**:
```json
{
  "existing_content": "...",
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

### Step 2: スケジューラー統合モジュールの実装

#### 2.1 src/core/scheduler_config.py

```python
"""
MemOSスケジューラー設定管理モジュール

CocoroCore2ConfigからMemOSスケジューラー設定への変換を担当
"""

import logging
from typing import Dict, Any

from memos.configs.mem_scheduler import SchedulerConfigFactory, GeneralSchedulerConfig

from ..config import CocoroCore2Config


logger = logging.getLogger(__name__)


def create_scheduler_config_factory(config: CocoroCore2Config) -> SchedulerConfigFactory:
    """CocoroCore2ConfigからSchedulerConfigFactoryを作成
    
    Args:
        config: CocoroCore2設定
        
    Returns:
        SchedulerConfigFactory: MemOSスケジューラー設定ファクトリー
    """
    
    scheduler_config_dict = {
        "top_k": config.mem_scheduler.top_k,
        "context_window_size": config.mem_scheduler.context_window_size,
        "enable_act_memory_update": config.mem_scheduler.enable_act_memory_update,
        "enable_parallel_dispatch": config.mem_scheduler.enable_parallel_dispatch,
        "thread_pool_max_workers": config.mem_scheduler.thread_pool_max_workers,
        "consume_interval_seconds": config.mem_scheduler.consume_interval_seconds,
        "act_mem_update_interval": config.mem_scheduler.act_mem_update_interval,
    }
    
    logger.info(f"Creating scheduler config: {scheduler_config_dict}")
    
    return SchedulerConfigFactory(
        backend="general_scheduler",
        config=scheduler_config_dict
    )


def validate_scheduler_config(config: CocoroCore2Config) -> bool:
    """スケジューラー設定の妥当性を検証
    
    Args:
        config: CocoroCore2設定
        
    Returns:
        bool: 設定が有効かどうか
    """
    mem_sched_config = config.mem_scheduler
    
    # 必須チェック
    if mem_sched_config.top_k <= 0:
        logger.error("top_k must be greater than 0")
        return False
    
    if mem_sched_config.context_window_size <= 0:
        logger.error("context_window_size must be greater than 0")
        return False
    
    if mem_sched_config.thread_pool_max_workers <= 0:
        logger.error("thread_pool_max_workers must be greater than 0")
        return False
    
    if mem_sched_config.consume_interval_seconds <= 0:
        logger.error("consume_interval_seconds must be greater than 0")
        return False
    
    # アクティベーションメモリが無効化されているかチェック
    if mem_sched_config.enable_act_memory_update:
        logger.warning("enable_act_memory_update is True, but this implementation is text-memory only")
    
    logger.info("Scheduler configuration validation passed")
    return True


def get_text_memory_optimization_config(config: CocoroCore2Config) -> Dict[str, Any]:
    """テキストメモリ最適化設定を取得
    
    Args:
        config: CocoroCore2設定
        
    Returns:
        Dict[str, Any]: テキストメモリ最適化設定
    """
    return config.mem_scheduler.text_memory_optimization
```

#### 2.2 src/core/text_memory_scheduler.py

```python
"""
CocoroCore2 テキストメモリスケジューラー統合モジュール

MemOSのGeneralSchedulerをCocoroCore2に統合するためのレイヤー
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from memos.mem_scheduler.scheduler_factory import SchedulerFactory
from memos.mem_scheduler.general_scheduler import GeneralScheduler
from memos.mem_scheduler.modules.schemas import (
    ScheduleMessageItem, 
    QUERY_LABEL, 
    ANSWER_LABEL, 
    ADD_LABEL
)
from memos.llms.base import BaseLLM
from memos.mem_cube.general import GeneralMemCube

from ..config import CocoroCore2Config
from .scheduler_config import create_scheduler_config_factory, validate_scheduler_config


class TextMemorySchedulerManager:
    """テキストメモリスケジューラー管理クラス"""
    
    def __init__(self, config: CocoroCore2Config):
        """初期化
        
        Args:
            config: CocoroCore2設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.scheduler: Optional[GeneralScheduler] = None
        self.is_initialized = False
        self.is_running = False
        
        # 設定検証
        if not validate_scheduler_config(config):
            raise ValueError("Invalid scheduler configuration")
    
    def initialize(self, chat_llm: BaseLLM, process_llm: Optional[BaseLLM] = None):
        """スケジューラーを初期化
        
        Args:
            chat_llm: チャット用LLM
            process_llm: 処理用LLM（Noneの場合はchat_llmを使用）
        """
        try:
            self.logger.info("Initializing text memory scheduler...")
            
            # スケジューラー設定ファクトリー作成
            config_factory = create_scheduler_config_factory(self.config)
            
            # スケジューラーインスタンス作成
            self.scheduler = SchedulerFactory.from_config(config_factory)
            
            # LLM設定
            if process_llm is None:
                process_llm = chat_llm
            
            self.scheduler.initialize_modules(chat_llm, process_llm)
            
            self.is_initialized = True
            self.logger.info("Text memory scheduler initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize text memory scheduler: {e}")
            raise
    
    async def start(self):
        """スケジューラーを開始"""
        if not self.is_initialized:
            raise RuntimeError("Scheduler must be initialized before starting")
        
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        try:
            self.logger.info("Starting text memory scheduler...")
            self.scheduler.start()
            self.is_running = True
            self.logger.info("Text memory scheduler started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start text memory scheduler: {e}")
            raise
    
    async def stop(self):
        """スケジューラーを停止"""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        try:
            self.logger.info("Stopping text memory scheduler...")
            self.scheduler.stop()
            self.is_running = False
            self.logger.info("Text memory scheduler stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop text memory scheduler: {e}")
            raise
    
    def submit_query_message(self, user_id: str, content: str, mem_cube: GeneralMemCube):
        """クエリメッセージを送信
        
        Args:
            user_id: ユーザーID
            content: クエリ内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping query message")
            return
        
        try:
            message = ScheduleMessageItem(
                user_id=user_id,
                mem_cube_id=mem_cube.config.cube_id,
                label=QUERY_LABEL,
                mem_cube=mem_cube,
                content=content,
                timestamp=datetime.now()
            )
            
            self.scheduler.submit_messages(message)
            self.logger.debug(f"Submitted query message: {content[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to submit query message: {e}")
    
    def submit_answer_message(self, user_id: str, content: str, mem_cube: GeneralMemCube):
        """応答メッセージを送信
        
        Args:
            user_id: ユーザーID
            content: 応答内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping answer message")
            return
        
        try:
            message = ScheduleMessageItem(
                user_id=user_id,
                mem_cube_id=mem_cube.config.cube_id,
                label=ANSWER_LABEL,
                mem_cube=mem_cube,
                content=content,
                timestamp=datetime.now()
            )
            
            self.scheduler.submit_messages(message)
            self.logger.debug(f"Submitted answer message: {content[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to submit answer message: {e}")
    
    def submit_add_message(self, user_id: str, content: str, mem_cube: GeneralMemCube):
        """記憶追加メッセージを送信
        
        Args:
            user_id: ユーザーID
            content: 記憶内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping add message")
            return
        
        try:
            # 記憶追加メッセージは配列形式で送信
            import json
            content_array = [content]
            
            message = ScheduleMessageItem(
                user_id=user_id,
                mem_cube_id=mem_cube.config.cube_id,
                label=ADD_LABEL,
                mem_cube=mem_cube,
                content=json.dumps(content_array),
                timestamp=datetime.now()
            )
            
            self.scheduler.submit_messages(message)
            self.logger.debug(f"Submitted add message: {content[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to submit add message: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """スケジューラーステータスを取得
        
        Returns:
            Dict[str, Any]: ステータス情報
        """
        status = {
            "initialized": self.is_initialized,
            "running": self.is_running,
            "enabled": self.config.mem_scheduler.enabled,
            "configuration": {
                "top_k": self.config.mem_scheduler.top_k,
                "context_window_size": self.config.mem_scheduler.context_window_size,
                "enable_act_memory_update": self.config.mem_scheduler.enable_act_memory_update,
                "enable_parallel_dispatch": self.config.mem_scheduler.enable_parallel_dispatch,
                "thread_pool_max_workers": self.config.mem_scheduler.thread_pool_max_workers,
                "consume_interval_seconds": self.config.mem_scheduler.consume_interval_seconds,
            }
        }
        
        if self.is_running and self.scheduler:
            try:
                # スケジューラーログを取得
                scheduler_logs = self.scheduler.get_web_log_messages()
                status["recent_logs_count"] = len(scheduler_logs)
            except Exception as e:
                self.logger.warning(f"Failed to get scheduler logs: {e}")
                status["recent_logs_count"] = -1
        
        return status
    
    def get_scheduler_logs(self) -> list:
        """スケジューラーログを取得
        
        Returns:
            list: ログエントリのリスト
        """
        if not self.is_running or not self.scheduler:
            return []
        
        try:
            return self.scheduler.get_web_log_messages()
        except Exception as e:
            self.logger.error(f"Failed to get scheduler logs: {e}")
            return []
```

### Step 3: CocoroCore2App統合の実装

#### 3.1 src/core_app.py の修正箇所

**追加インポート**:
```python
from .core.text_memory_scheduler import TextMemorySchedulerManager
```

**__init__ メソッドに追加**:
```python
def __init__(self, config: CocoroCore2Config):
    # 既存の初期化...
    
    # テキストメモリスケジューラー初期化
    self.text_memory_scheduler: Optional[TextMemorySchedulerManager] = None
    if config.mem_scheduler.enabled:
        try:
            self.text_memory_scheduler = TextMemorySchedulerManager(config)
            self.logger.info("Text memory scheduler manager created")
        except Exception as e:
            self.logger.error(f"Failed to create text memory scheduler manager: {e}")
            # スケジューラーエラーはアプリケーション全体を停止させない
            self.text_memory_scheduler = None
```

**startup メソッドに追加**:
```python
async def startup(self):
    """アプリケーション起動処理"""
    try:
        # 既存の起動処理...
        
        # テキストメモリスケジューラー初期化・開始
        if self.text_memory_scheduler:
            try:
                self.logger.info("Initializing text memory scheduler...")
                
                # chat_llmを取得（MOSから）
                chat_llm = self._get_chat_llm_from_mos()
                self.text_memory_scheduler.initialize(chat_llm)
                await self.text_memory_scheduler.start()
                
                self.logger.info("Text memory scheduler started successfully")
            except Exception as e:
                self.logger.error(f"Failed to start text memory scheduler: {e}")
                # スケジューラーエラーはアプリケーション全体を停止させない
                self.text_memory_scheduler = None
        
    except Exception as e:
        self.logger.error(f"Failed to start CocoroCore2App: {e}")
        raise
```

**shutdown メソッドに追加**:
```python
async def shutdown(self):
    """アプリケーション終了処理"""
    try:
        # テキストメモリスケジューラー停止
        if self.text_memory_scheduler and self.text_memory_scheduler.is_running:
            try:
                self.logger.info("Stopping text memory scheduler...")
                await self.text_memory_scheduler.stop()
                self.logger.info("Text memory scheduler stopped")
            except Exception as e:
                self.logger.error(f"Failed to stop text memory scheduler: {e}")
        
        # 既存の終了処理...
        
    except Exception as e:
        self.logger.error(f"Error during shutdown: {e}")
```

**新しいメソッドを追加**:
```python
def _get_chat_llm_from_mos(self) -> BaseLLM:
    """MOSからchat_llmインスタンスを取得
    
    Returns:
        BaseLLM: チャット用LLMインスタンス
    """
    try:
        # MOSのインターナルからLLMを取得する
        # これはMemOSの内部実装に依存するため、将来変更される可能性がある
        if hasattr(self.mos, 'chat_llm'):
            return self.mos.chat_llm
        elif hasattr(self.mos, '_chat_model'):
            return self.mos._chat_model
        else:
            # フォールバック: MOSConfigから新しいLLMインスタンスを作成
            from memos.llms.factory import LLMFactory
            from memos.configs.llm import LLMConfigFactory
            
            chat_model_config = self.config.mos_config["chat_model"]
            llm_config_factory = LLMConfigFactory(**chat_model_config)
            return LLMFactory.from_config(llm_config_factory)
            
    except Exception as e:
        self.logger.error(f"Failed to get chat LLM from MOS: {e}")
        raise
```

---

## 🧪 テスト実装

### test_scheduler_integration.py

```python
"""
テキストメモリスケジューラー統合テスト
"""

import pytest
import asyncio
from pathlib import Path

from src.config import CocoroCore2Config
from src.core.text_memory_scheduler import TextMemorySchedulerManager
from src.core.scheduler_config import validate_scheduler_config, create_scheduler_config_factory


class TestSchedulerIntegration:
    
    @pytest.fixture
    def sample_config(self):
        """テスト用設定を作成"""
        config_path = Path(__file__).parent.parent / "config" / "default_memos_config.json"
        return CocoroCore2Config.load(str(config_path), "development")
    
    def test_scheduler_config_validation(self, sample_config):
        """スケジューラー設定の検証テスト"""
        assert validate_scheduler_config(sample_config) == True
    
    def test_scheduler_config_factory_creation(self, sample_config):
        """スケジューラー設定ファクトリー作成テスト"""
        factory = create_scheduler_config_factory(sample_config)
        assert factory.backend == "general_scheduler"
        assert "top_k" in factory.config
    
    def test_scheduler_manager_initialization(self, sample_config):
        """スケジューラーマネージャー初期化テスト"""
        # スケジューラーを有効化
        sample_config.mem_scheduler.enabled = True
        
        manager = TextMemorySchedulerManager(sample_config)
        assert manager.is_initialized == False
        assert manager.is_running == False
    
    @pytest.mark.asyncio
    async def test_scheduler_lifecycle(self, sample_config):
        """スケジューラーライフサイクルテスト"""
        # 注意: このテストはMOSとLLMのモックが必要
        pass
```

---

## 📋 実装チェックリスト

### Step 1: 設定拡張
- [ ] `src/config.py`に`MemSchedulerConfig`クラスを追加
- [ ] `CocoroCore2Config`クラスに`mem_scheduler`フィールドを追加
- [ ] `config/default_memos_config.json`にスケジューラー設定を追加
- [ ] 設定の読み込み・検証をテスト

### Step 2: スケジューラー統合モジュール
- [ ] `src/core/scheduler_config.py`を作成
- [ ] `src/core/text_memory_scheduler.py`を作成
- [ ] 設定変換機能をテスト
- [ ] スケジューラー管理機能をテスト

### Step 3: CocoroCore2App統合
- [ ] `src/core_app.py`にスケジューラー統合を追加
- [ ] 初期化・ライフサイクル管理を実装
- [ ] MOSからLLMインスタンス取得を実装
- [ ] エラーハンドリングを実装

### Step 4: テスト・検証
- [ ] 基本的な単体テストを作成
- [ ] 設定読み込みの統合テストを作成
- [ ] スケジューラー初期化の統合テストを作成
- [ ] エラーケースのテストを作成

---

## 🔧 デバッグ・トラブルシューティング

### よくある問題

1. **MemOSインポートエラー**
   - MemOSライブラリが正しくインストールされているか確認
   - Pythonパスが正しく設定されているか確認

2. **設定読み込みエラー**
   - JSON構文エラーをチェック
   - 環境変数の設定を確認

3. **スケジューラー初期化エラー**
   - LLMインスタンスが正しく取得できているか確認
   - スケジューラー設定の妥当性を確認

4. **ライフサイクル管理エラー**
   - 非同期処理の順序を確認
   - リソースクリーンアップが適切に行われているか確認

---

*この実装ガイドはPhase 1の具体的な実装手順を示しています。実装時の参考として使用してください。*
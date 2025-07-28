# Phase 3: テキストメモリ最適化機能 - 詳細設計書

## 📅 作成日: 2025-01-28
## 🎯 目的: Phase 3実装の詳細設計とコード仕様

---

## 🏗️ アーキテクチャ設計

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                    CocoroCore2App                           │
│  ┌─────────────────────────────────────────────────────────┤
│  │            TextMemorySchedulerManager                   │
│  │  ┌─────────────────┬─────────────────┬─────────────────┤
│  │  │   Existing      │   Phase 3 New   │   MemOS Core    │
│  │  │                 │                 │                 │
│  │  │ • submit_*      │ • optimize_*    │ • Monitor       │
│  │  │ • lifecycle     │ • analyze_*     │ • Retriever     │
│  │  │ • status        │ • detect_*      │ • Dispatcher    │
│  │  └─────────────────┴─────────────────┴─────────────────┤
│  └─────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────┘
```

### Phase 3 新規コンポーネント

#### 1. **MemoryOptimizationEngine**
- **役割**: 記憶最適化の中核エンジン
- **責任**: 重複検出、品質評価、ワーキングメモリ最適化

#### 2. **OptimizationScheduler**  
- **役割**: 自動最適化のスケジューリング
- **責任**: トリガー監視、バックグラウンド実行

#### 3. **MemoryQualityAnalyzer**
- **役割**: 記憶品質の分析・評価
- **責任**: 品質スコア計算、改善提案

---

## 📋 詳細実装仕様

### Step 1: TextMemorySchedulerManager拡張

#### 1.1 新規メソッド実装

**ファイル**: `src/core/text_memory_scheduler.py`

```python
async def optimize_text_memory(
    self, 
    user_id: str, 
    force_optimization: bool = False,
    optimization_type: str = "full"
) -> Dict[str, Any]:
    """テキストメモリの手動最適化を実行
    
    Args:
        user_id: ユーザーID
        force_optimization: 強制最適化フラグ
        optimization_type: 最適化タイプ ("full", "dedup", "quality", "rerank")
        
    Returns:
        Dict[str, Any]: 最適化結果
        {
            "success": bool,
            "optimization_type": str,
            "before_stats": dict,
            "after_stats": dict,
            "improvements": dict,
            "duration_seconds": float
        }
    """
    if not self.is_running:
        return {"success": False, "error": "Scheduler not running"}
    
    try:
        start_time = datetime.now()
        
        # MemCube取得
        mem_cube = self._get_user_memcube(user_id)
        if not mem_cube:
            return {"success": False, "error": "MemCube not found"}
        
        # 最適化前の状態分析
        before_stats = await self._analyze_memory_state(user_id, mem_cube)
        
        # 最適化実行
        optimization_result = await self._run_optimization_process(
            user_id, mem_cube, optimization_type, force_optimization
        )
        
        # 最適化後の状態分析
        after_stats = await self._analyze_memory_state(user_id, mem_cube)
        
        # 改善度計算
        improvements = self._calculate_improvements(before_stats, after_stats)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            "success": True,
            "optimization_type": optimization_type,
            "before_stats": before_stats,
            "after_stats": after_stats,
            "improvements": improvements,
            "duration_seconds": duration
        }
        
        self.logger.info(f"Memory optimization completed for user {user_id}: {result}")
        return result
        
    except Exception as e:
        self.logger.error(f"Memory optimization failed for user {user_id}: {e}")
        return {"success": False, "error": str(e)}

def get_working_memory_status(self, user_id: str) -> Dict[str, Any]:
    """ワーキングメモリの現在状態を取得
    
    Args:
        user_id: ユーザーID
        
    Returns:
        Dict[str, Any]: ワーキングメモリ状態
        {
            "total_memories": int,
            "memory_types": dict,
            "quality_scores": dict,
            "similarity_analysis": dict,
            "recommendations": list
        }
    """
    try:
        mem_cube = self._get_user_memcube(user_id)
        if not mem_cube:
            return {"error": "MemCube not found"}
        
        text_mem = mem_cube.text_mem
        if not hasattr(text_mem, 'get_working_memory'):
            return {"error": "Working memory not supported"}
        
        working_memory = text_mem.get_working_memory()
        
        # 記憶数と種類分析
        total_memories = len(working_memory)
        memory_types = self._analyze_memory_types(working_memory)
        
        # 品質スコア分析
        quality_scores = self._analyze_quality_scores(working_memory)
        
        # 類似性分析
        similarity_analysis = self._analyze_memory_similarity(working_memory)
        
        # 改善提案
        recommendations = self._generate_memory_recommendations(
            working_memory, quality_scores, similarity_analysis
        )
        
        return {
            "total_memories": total_memories,
            "memory_types": memory_types,
            "quality_scores": quality_scores,
            "similarity_analysis": similarity_analysis,
            "recommendations": recommendations
        }
        
    except Exception as e:
        self.logger.error(f"Failed to get working memory status for user {user_id}: {e}")
        return {"error": str(e)}

def detect_duplicate_memories(
    self, 
    user_id: str, 
    similarity_threshold: float = 0.95
) -> Dict[str, Any]:
    """重複記憶の検出
    
    Args:
        user_id: ユーザーID
        similarity_threshold: 類似性閾値
        
    Returns:
        Dict[str, Any]: 重複検出結果
        {
            "total_memories": int,
            "duplicate_groups": list,
            "potential_savings": dict,
            "recommendations": list
        }
    """
    try:
        mem_cube = self._get_user_memcube(user_id)
        if not mem_cube:
            return {"error": "MemCube not found"}
        
        # 全ての記憶を取得
        all_memories = self._get_all_memories(mem_cube)
        memory_texts = [mem.memory for mem in all_memories]
        
        # MemOSのfilter_similar_memoriesを活用
        if self.scheduler and hasattr(self.scheduler, 'retriever'):
            filtered_memories = self.scheduler.retriever.filter_similar_memories(
                text_memories=memory_texts,
                similarity_threshold=similarity_threshold
            )
            
            # 重複グループの分析
            duplicate_groups = self._analyze_duplicate_groups(
                original_memories=memory_texts,
                filtered_memories=filtered_memories,
                similarity_threshold=similarity_threshold
            )
            
            # 削減効果計算
            potential_savings = self._calculate_deduplication_savings(
                original_count=len(memory_texts),
                filtered_count=len(filtered_memories),
                duplicate_groups=duplicate_groups
            )
            
            # 改善提案
            recommendations = self._generate_deduplication_recommendations(duplicate_groups)
            
            return {
                "total_memories": len(memory_texts),
                "duplicate_groups": duplicate_groups,
                "potential_savings": potential_savings,
                "recommendations": recommendations
            }
        else:
            return {"error": "Scheduler retriever not available"}
            
    except Exception as e:
        self.logger.error(f"Duplicate detection failed for user {user_id}: {e}")
        return {"error": str(e)}
```

#### 1.2 内部ヘルパーメソッド

```python
async def _run_optimization_process(
    self, 
    user_id: str, 
    mem_cube: "GeneralMemCube", 
    optimization_type: str,
    force_optimization: bool
) -> Dict[str, Any]:
    """最適化プロセスの実行"""
    
    if optimization_type == "full":
        # 全体最適化: 重複除去 → 品質フィルタ → 再ランキング
        result = {}
        result.update(await self._run_deduplication(user_id, mem_cube))
        result.update(await self._run_quality_filtering(user_id, mem_cube))
        result.update(await self._run_memory_reranking(user_id, mem_cube))
        return result
        
    elif optimization_type == "dedup":
        # 重複除去のみ
        return await self._run_deduplication(user_id, mem_cube)
        
    elif optimization_type == "quality":
        # 品質フィルタリングのみ
        return await self._run_quality_filtering(user_id, mem_cube)
        
    elif optimization_type == "rerank":
        # 再ランキングのみ
        return await self._run_memory_reranking(user_id, mem_cube)
        
    else:
        raise ValueError(f"Unknown optimization type: {optimization_type}")

async def _run_deduplication(self, user_id: str, mem_cube: "GeneralMemCube") -> Dict[str, Any]:
    """重複除去の実行"""
    try:
        working_memory = mem_cube.text_mem.get_working_memory()
        memory_texts = [mem.memory for mem in working_memory]
        
        # MemOSの重複検出を使用
        filtered_texts = self.scheduler.retriever.filter_similar_memories(
            text_memories=memory_texts,
            similarity_threshold=self.config.mem_scheduler.text_memory_optimization.get(
                "similarity_threshold", 0.95
            )
        )
        
        removed_count = len(memory_texts) - len(filtered_texts)
        
        self.logger.info(f"Deduplication removed {removed_count} duplicate memories for user {user_id}")
        
        return {
            "deduplication": {
                "original_count": len(memory_texts),
                "filtered_count": len(filtered_texts),
                "removed_count": removed_count,
                "reduction_percentage": (removed_count / len(memory_texts) * 100) if memory_texts else 0
            }
        }
        
    except Exception as e:
        self.logger.error(f"Deduplication failed for user {user_id}: {e}")
        return {"deduplication": {"error": str(e)}}

async def _run_quality_filtering(self, user_id: str, mem_cube: "GeneralMemCube") -> Dict[str, Any]:
    """品質フィルタリングの実行"""
    try:
        working_memory = mem_cube.text_mem.get_working_memory()
        memory_texts = [mem.memory for mem in working_memory]
        
        # MemOSの品質フィルタを使用
        min_length = self.config.mem_scheduler.text_memory_optimization.get(
            "min_memory_length", 10
        )
        
        filtered_texts = self.scheduler.retriever.filter_too_short_memories(
            text_memories=memory_texts,
            min_length_threshold=min_length
        )
        
        removed_count = len(memory_texts) - len(filtered_texts)
        
        self.logger.info(f"Quality filtering removed {removed_count} low-quality memories for user {user_id}")
        
        return {
            "quality_filtering": {
                "original_count": len(memory_texts),
                "filtered_count": len(filtered_texts),
                "removed_count": removed_count,
                "min_length_threshold": min_length
            }
        }
        
    except Exception as e:
        self.logger.error(f"Quality filtering failed for user {user_id}: {e}")
        return {"quality_filtering": {"error": str(e)}}

async def _run_memory_reranking(self, user_id: str, mem_cube: "GeneralMemCube") -> Dict[str, Any]:
    """記憶の再ランキング実行"""
    try:
        # 最近のクエリ履歴を取得
        recent_queries = self._get_recent_queries(user_id, limit=5)
        
        if not recent_queries:
            return {"reranking": {"skipped": "No recent queries available"}}
        
        working_memory = mem_cube.text_mem.get_working_memory()
        
        # MemOSのワーキングメモリ置換を使用
        new_memory = self.scheduler.retriever.replace_working_memory(
            queries=recent_queries,
            user_id=user_id,
            mem_cube_id=mem_cube.config.cube_id,
            mem_cube=mem_cube,
            original_memory=working_memory,
            new_memory=[],  # 既存記憶の再ランキングのみ
            top_k=self.config.mem_scheduler.text_memory_optimization.get(
                "working_memory_size", 20
            )
        )
        
        self.logger.info(f"Memory reranking completed for user {user_id}")
        
        return {
            "reranking": {
                "original_count": len(working_memory),
                "reranked_count": len(new_memory) if new_memory else len(working_memory),
                "query_context": len(recent_queries)
            }
        }
        
    except Exception as e:
        self.logger.error(f"Memory reranking failed for user {user_id}: {e}")
        return {"reranking": {"error": str(e)}}
```

### Step 2: 自動最適化スケジューラー

#### 2.1 OptimizationScheduler実装

**新規ファイル**: `src/core/optimization_scheduler.py`

```python
"""
テキストメモリ自動最適化スケジューラー
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass

from ..config import CocoroCore2Config


@dataclass
class OptimizationTask:
    """最適化タスクの定義"""
    user_id: str
    optimization_type: str
    priority: int = 0
    scheduled_time: Optional[datetime] = None
    created_time: datetime = None
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()


class OptimizationScheduler:
    """自動最適化スケジューラー"""
    
    def __init__(self, config: CocoroCore2Config, scheduler_manager):
        self.config = config
        self.scheduler_manager = scheduler_manager
        self.logger = logging.getLogger(__name__)
        
        # 状態管理
        self.is_running = False
        self.optimization_tasks: asyncio.Queue = asyncio.Queue()
        self.user_memory_counts: Dict[str, int] = {}
        self.last_optimization_times: Dict[str, datetime] = {}
        
        # 設定値
        self.auto_optimize_interval = config.mem_scheduler.text_memory_optimization.get(
            "auto_optimize_interval", 3600
        )
        self.auto_optimize_threshold = config.mem_scheduler.text_memory_optimization.get(
            "auto_optimize_threshold", 50
        )
        self.max_concurrent_optimizations = config.mem_scheduler.text_memory_optimization.get(
            "max_concurrent_optimizations", 3
        )
        
        # 実行中のタスク管理
        self.running_optimizations: Set[str] = set()
    
    async def start(self):
        """スケジューラー開始"""
        if self.is_running:
            return
        
        self.is_running = True
        self.logger.info("Optimization scheduler started")
        
        # バックグラウンドタスクを開始
        asyncio.create_task(self._optimization_worker())
        asyncio.create_task(self._periodic_scheduler())
    
    async def stop(self):
        """スケジューラー停止"""
        self.is_running = False
        self.logger.info("Optimization scheduler stopped")
    
    def notify_memory_added(self, user_id: str):
        """記憶追加通知"""
        self.user_memory_counts[user_id] = self.user_memory_counts.get(user_id, 0) + 1
        
        # 閾値チェック
        if self.user_memory_counts[user_id] >= self.auto_optimize_threshold:
            self._schedule_optimization(user_id, "threshold_triggered")
    
    def _schedule_optimization(self, user_id: str, optimization_type: str, priority: int = 0):
        """最適化タスクをスケジュール"""
        if user_id in self.running_optimizations:
            self.logger.debug(f"Optimization already running for user {user_id}, skipping")
            return
        
        task = OptimizationTask(
            user_id=user_id,
            optimization_type=optimization_type,
            priority=priority
        )
        
        try:
            self.optimization_tasks.put_nowait(task)
            self.logger.info(f"Scheduled optimization task for user {user_id}: {optimization_type}")
        except asyncio.QueueFull:
            self.logger.warning(f"Optimization queue full, dropping task for user {user_id}")
    
    async def _optimization_worker(self):
        """最適化ワーカー"""
        while self.is_running:
            try:
                # タスクを待機（最大1秒）
                task = await asyncio.wait_for(self.optimization_tasks.get(), timeout=1.0)
                
                # 同時実行制限チェック
                if len(self.running_optimizations) >= self.max_concurrent_optimizations:
                    # タスクを戻す
                    self.optimization_tasks.put_nowait(task)
                    await asyncio.sleep(1)
                    continue
                
                # 最適化実行
                await self._execute_optimization_task(task)
                
            except asyncio.TimeoutError:
                # タイムアウトは正常（継続）
                continue
            except Exception as e:
                self.logger.error(f"Optimization worker error: {e}")
                await asyncio.sleep(1)
    
    async def _execute_optimization_task(self, task: OptimizationTask):
        """最適化タスクの実行"""
        user_id = task.user_id
        
        try:
            self.running_optimizations.add(user_id)
            self.logger.info(f"Starting optimization for user {user_id}: {task.optimization_type}")
            
            # 最適化実行
            result = await self.scheduler_manager.optimize_text_memory(
                user_id=user_id,
                optimization_type=task.optimization_type
            )
            
            if result.get("success"):
                # 成功時の処理
                self.user_memory_counts[user_id] = 0  # カウンターリセット
                self.last_optimization_times[user_id] = datetime.now()
                
                self.logger.info(
                    f"Optimization completed for user {user_id}: "
                    f"{result.get('improvements', {})}"
                )
            else:
                # 失敗時の処理
                self.logger.warning(
                    f"Optimization failed for user {user_id}: {result.get('error', 'Unknown error')}"
                )
                
        except Exception as e:
            self.logger.error(f"Optimization execution failed for user {user_id}: {e}")
        finally:
            self.running_optimizations.discard(user_id)
    
    async def _periodic_scheduler(self):
        """定期的な最適化スケジューリング"""
        while self.is_running:
            try:
                await asyncio.sleep(self.auto_optimize_interval)
                
                # アクティブユーザーの定期最適化
                current_time = datetime.now()
                
                for user_id, last_time in self.last_optimization_times.items():
                    if current_time - last_time > timedelta(seconds=self.auto_optimize_interval * 2):
                        self._schedule_optimization(user_id, "periodic", priority=1)
                
            except Exception as e:
                self.logger.error(f"Periodic scheduler error: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """スケジューラー状態取得"""
        return {
            "is_running": self.is_running,
            "queue_size": self.optimization_tasks.qsize(),
            "running_optimizations": len(self.running_optimizations),
            "user_memory_counts": dict(self.user_memory_counts),
            "last_optimization_times": {
                user_id: time.isoformat() 
                for user_id, time in self.last_optimization_times.items()
            },
            "config": {
                "auto_optimize_interval": self.auto_optimize_interval,
                "auto_optimize_threshold": self.auto_optimize_threshold,
                "max_concurrent_optimizations": self.max_concurrent_optimizations
            }
        }
```

### Step 3: 設定拡張

#### 3.1 MemSchedulerConfig拡張

**ファイル**: `src/config.py`

```python
# MemSchedulerConfigクラスに追加
class MemSchedulerConfig(BaseModel):
    # 既存フィールド...
    
    # Phase 3: 最適化機能設定
    enable_auto_optimization: bool = True
    auto_optimize_interval: int = 3600  # 秒
    auto_optimize_threshold: int = 50   # 記憶数
    max_concurrent_optimizations: int = 3
    
    # テキストメモリ特化設定を拡張
    text_memory_optimization: Dict[str, Any] = Field(default_factory=lambda: {
        # 既存設定...
        "enable_deduplication": True,
        "similarity_threshold": 0.95,
        "working_memory_size": 20,
        "long_term_memory_capacity": 10000,
        "user_memory_capacity": 10000,
        "graceful_degradation": True,
        "log_scheduler_errors": True,
        
        # Phase 3 新規設定
        "auto_optimize_interval": 3600,
        "auto_optimize_threshold": 50,
        "max_concurrent_optimizations": 3,
        "min_memory_length": 10,
        "quality_score_threshold": 0.7,
        "enable_background_optimization": True,
        "optimization_batch_size": 100,
        "similarity_analysis_enabled": True,
        "reranking_enabled": True,
        "memory_lifecycle_management": True
    })
```

#### 3.2 デフォルト設定更新

**ファイル**: `config/default_memos_config.json`

```json
{
  "mem_scheduler": {
    "enabled": true,
    "enable_auto_optimization": true,
    "auto_optimize_interval": 3600,
    "auto_optimize_threshold": 50,
    "max_concurrent_optimizations": 3,
    "text_memory_optimization": {
      "enable_deduplication": true,
      "similarity_threshold": 0.95,
      "working_memory_size": 20,
      "auto_optimize_interval": 3600,
      "auto_optimize_threshold": 50,
      "max_concurrent_optimizations": 3,
      "min_memory_length": 10,
      "quality_score_threshold": 0.7,
      "enable_background_optimization": true,
      "optimization_batch_size": 100,
      "similarity_analysis_enabled": true,
      "reranking_enabled": true,
      "memory_lifecycle_management": true
    }
  }
}
```

---

## 🧪 テスト設計

### 単体テスト: `test_phase3_optimization.py`

```python
"""
Phase 3最適化機能のテスト
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.core.text_memory_scheduler import TextMemorySchedulerManager
from src.core.optimization_scheduler import OptimizationScheduler, OptimizationTask
from src.config import CocoroCore2Config


class TestTextMemoryOptimization:
    """テキストメモリ最適化テスト"""
    
    @pytest.fixture
    def sample_config_phase3(self):
        """Phase 3設定を作成"""
        config_data = {
            # ... 基本設定 ...
            "mem_scheduler": {
                "enabled": True,
                "enable_auto_optimization": True,
                "auto_optimize_interval": 60,  # テスト用短縮
                "auto_optimize_threshold": 5,   # テスト用短縮
                "text_memory_optimization": {
                    "similarity_threshold": 0.9,
                    "min_memory_length": 5,
                    "working_memory_size": 10
                }
            }
        }
        return CocoroCore2Config(**config_data)
    
    @patch('src.core.text_memory_scheduler.SchedulerFactory')
    def test_optimize_text_memory_success(self, mock_scheduler_factory, sample_config_phase3):
        """テキストメモリ最適化成功テスト"""
        # モックの設定
        mock_scheduler = Mock()
        mock_retriever = Mock()
        mock_scheduler.retriever = mock_retriever
        
        # 重複検出のモック
        mock_retriever.filter_similar_memories.return_value = ["memory1", "memory2"]
        mock_retriever.filter_too_short_memories.return_value = ["memory1", "memory2"]
        
        scheduler_manager = TextMemorySchedulerManager(sample_config_phase3)
        scheduler_manager.scheduler = mock_scheduler
        scheduler_manager.is_running = True
        
        # MemCubeのモック
        mock_memcube = Mock()
        mock_working_memory = [Mock(memory="test memory 1"), Mock(memory="test memory 2")]
        mock_memcube.text_mem.get_working_memory.return_value = mock_working_memory
        
        scheduler_manager._get_user_memcube = Mock(return_value=mock_memcube)
        
        # 最適化実行
        result = await scheduler_manager.optimize_text_memory("test_user")
        
        # 結果確認
        assert result["success"] is True
        assert "before_stats" in result
        assert "after_stats" in result
        assert "improvements" in result
    
    def test_optimization_scheduler_task_scheduling(self, sample_config_phase3):
        """最適化スケジューラーのタスクスケジューリングテスト"""
        scheduler_manager = Mock()
        opt_scheduler = OptimizationScheduler(sample_config_phase3, scheduler_manager)
        
        # 記憶追加通知
        opt_scheduler.notify_memory_added("test_user")
        opt_scheduler.notify_memory_added("test_user")
        opt_scheduler.notify_memory_added("test_user")
        opt_scheduler.notify_memory_added("test_user")
        opt_scheduler.notify_memory_added("test_user")  # 閾値到達
        
        # タスクがスケジュールされたことを確認
        assert opt_scheduler.optimization_tasks.qsize() == 1
    
    def test_duplicate_detection(self, sample_config_phase3):
        """重複検出テスト"""
        mock_scheduler = Mock()
        mock_retriever = Mock()
        mock_scheduler.retriever = mock_retriever
        
        # 重複検出のモック設定
        original_memories = ["memory1", "memory2", "memory1 duplicate", "memory3"]
        filtered_memories = ["memory1", "memory2", "memory3"]
        mock_retriever.filter_similar_memories.return_value = filtered_memories
        
        scheduler_manager = TextMemorySchedulerManager(sample_config_phase3)
        scheduler_manager.scheduler = mock_scheduler
        
        # MemCubeのモック
        mock_memcube = Mock()
        scheduler_manager._get_user_memcube = Mock(return_value=mock_memcube)
        scheduler_manager._get_all_memories = Mock(return_value=[
            Mock(memory=mem) for mem in original_memories
        ])
        
        # 重複検出実行
        result = scheduler_manager.detect_duplicate_memories("test_user")
        
        # 結果確認
        assert result["total_memories"] == 4
        assert "duplicate_groups" in result
        assert "potential_savings" in result
```

---

## 📊 パフォーマンス考慮事項

### 1. **計算複雑性**
- **重複検出**: O(n²) - TF-IDFとコサイン類似度計算
- **品質フィルタリング**: O(n) - 線形処理
- **再ランキング**: O(n log n) - LLMベースの比較

### 2. **メモリ使用量**
- **ワーキングメモリ**: 最大20-50記憶（設定可能）
- **類似度行列**: n×n（一時的使用）
- **LLMコンテキスト**: プロンプト+記憶テキスト

### 3. **最適化戦略**
- **バッチ処理**: 大量記憶の分割処理
- **非同期実行**: UI応答性確保
- **キャッシュ**: 計算結果の再利用
- **優先度制御**: 重要度に基づく処理順序

---

*この詳細設計書に基づいてPhase 3を実装することで、CocoroCore2は高度なテキストメモリ最適化機能を獲得し、MemOSの能力を最大限に活用できます。*
"""
テキストメモリ自動最適化スケジューラー

CocoroCore2のMemOSテキストメモリの自動最適化を管理するスケジューラー。
記憶蓄積量やタイミングに基づいて、バックグラウンドで最適化処理を実行する。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass

from ..config import CocoroCore2Config


@dataclass
class OptimizationTask:
    """最適化タスクの定義
    
    Attributes:
        user_id: 対象ユーザーID
        optimization_type: 最適化タイプ ("full", "dedup", "quality", "rerank", "threshold_triggered", "periodic")
        priority: タスク優先度 (0=低, 1=中, 2=高)
        scheduled_time: スケジュール実行時刻（None=即座実行）
        created_time: タスク作成時刻
    """
    user_id: str
    optimization_type: str
    priority: int = 0
    scheduled_time: Optional[datetime] = None
    created_time: datetime = None
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()


class OptimizationScheduler:
    """自動最適化スケジューラー
    
    記憶の蓄積量、時間経過、ユーザー活動に基づいて自動的に最適化を実行する。
    複数のユーザーに対して並列で最適化処理を行い、システムリソースを効率的に利用する。
    """
    
    def __init__(self, config: CocoroCore2Config, scheduler_manager):
        """初期化
        
        Args:
            config: CocoroCore2設定
            scheduler_manager: TextMemorySchedulerManagerインスタンス
        """
        self.config = config
        self.scheduler_manager = scheduler_manager
        self.logger = logging.getLogger(__name__)
        
        # 状態管理
        self.is_running = False
        self.optimization_tasks: asyncio.Queue = asyncio.Queue()
        self.user_memory_counts: Dict[str, int] = {}
        self.last_optimization_times: Dict[str, datetime] = {}
        
        # 設定値の取得（Phase 3用設定）
        optimization_config = config.mem_scheduler.text_memory_optimization
        self.auto_optimize_interval = optimization_config.get("auto_optimize_interval", 3600)
        self.auto_optimize_threshold = optimization_config.get("auto_optimize_threshold", 50)
        self.max_concurrent_optimizations = optimization_config.get("max_concurrent_optimizations", 3)
        self.enable_background_optimization = optimization_config.get("enable_background_optimization", True)
        
        # 実行中のタスク管理
        self.running_optimizations: Set[str] = set()
        self.worker_tasks: Set[asyncio.Task] = set()
        
        self.logger.info(
            f"OptimizationScheduler initialized - "
            f"interval: {self.auto_optimize_interval}s, "
            f"threshold: {self.auto_optimize_threshold}, "
            f"max_concurrent: {self.max_concurrent_optimizations}"
        )
    
    async def start(self):
        """スケジューラー開始"""
        if self.is_running:
            self.logger.warning("Optimization scheduler is already running")
            return
        
        if not self.enable_background_optimization:
            self.logger.info("Background optimization is disabled, scheduler not started")
            return
        
        self.is_running = True
        self.logger.info("Starting optimization scheduler...")
        
        # バックグラウンドタスクを開始
        worker_task = asyncio.create_task(self._optimization_worker())
        periodic_task = asyncio.create_task(self._periodic_scheduler())
        
        self.worker_tasks.add(worker_task)
        self.worker_tasks.add(periodic_task)
        
        # タスク完了時のクリーンアップ設定
        worker_task.add_done_callback(self.worker_tasks.discard)
        periodic_task.add_done_callback(self.worker_tasks.discard)
        
        self.logger.info("Optimization scheduler started successfully")
    
    async def stop(self):
        """スケジューラー停止"""
        if not self.is_running:
            self.logger.warning("Optimization scheduler is not running")
            return
        
        self.is_running = False
        self.logger.info("Stopping optimization scheduler...")
        
        # バックグラウンドタスクの停止
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()
        
        # タスクの完了を待機
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.worker_tasks.clear()
        
        # 実行中の最適化の完了を待機（最大30秒）
        if self.running_optimizations:
            self.logger.info(f"Waiting for {len(self.running_optimizations)} running optimizations to complete...")
            
            wait_count = 0
            while self.running_optimizations and wait_count < 30:
                await asyncio.sleep(1)
                wait_count += 1
            
            if self.running_optimizations:
                self.logger.warning(f"Forced shutdown with {len(self.running_optimizations)} optimizations still running")
        
        self.logger.info("Optimization scheduler stopped")
    
    def notify_memory_added(self, user_id: str):
        """記憶追加通知
        
        記憶が追加された際に呼び出され、蓄積量に基づく自動最適化をトリガーする。
        
        Args:
            user_id: 記憶を追加したユーザーID
        """
        if not self.is_running:
            return
        
        # ユーザーの記憶カウントを更新
        self.user_memory_counts[user_id] = self.user_memory_counts.get(user_id, 0) + 1
        current_count = self.user_memory_counts[user_id]
        
        self.logger.debug(f"Memory added for user {user_id}, current count: {current_count}")
        
        # 閾値チェック
        if current_count >= self.auto_optimize_threshold:
            self.logger.info(
                f"Auto-optimization threshold reached for user {user_id} "
                f"({current_count} >= {self.auto_optimize_threshold})"
            )
            self._schedule_optimization(user_id, "threshold_triggered", priority=1)
    
    def _schedule_optimization(self, user_id: str, optimization_type: str, priority: int = 0):
        """最適化タスクをスケジュール
        
        Args:
            user_id: 対象ユーザーID
            optimization_type: 最適化タイプ
            priority: タスク優先度
        """
        if not self.is_running:
            self.logger.debug(f"Scheduler not running, skipping optimization for user {user_id}")
            return
        
        # 既に実行中の場合はスキップ
        if user_id in self.running_optimizations:
            self.logger.debug(f"Optimization already running for user {user_id}, skipping")
            return
        
        # タスク作成
        task = OptimizationTask(
            user_id=user_id,
            optimization_type=optimization_type,
            priority=priority
        )
        
        try:
            self.optimization_tasks.put_nowait(task)
            self.logger.info(f"Scheduled optimization task for user {user_id}: {optimization_type} (priority: {priority})")
        except asyncio.QueueFull:
            self.logger.warning(f"Optimization queue full, dropping task for user {user_id}")
    
    async def _optimization_worker(self):
        """最適化ワーカー
        
        キューからタスクを取得して最適化を実行するバックグラウンドワーカー。
        同時実行数制限とエラーハンドリングを管理する。
        """
        self.logger.info("Optimization worker started")
        
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
                
                # 最適化実行（非同期で並列実行）
                asyncio.create_task(self._execute_optimization_task(task))
                
            except asyncio.TimeoutError:
                # タイムアウトは正常（継続）
                continue
            except asyncio.CancelledError:
                self.logger.info("Optimization worker cancelled")
                break
            except Exception as e:
                self.logger.error(f"Optimization worker error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        self.logger.info("Optimization worker stopped")
    
    async def _execute_optimization_task(self, task: OptimizationTask):
        """最適化タスクの実行
        
        Args:
            task: 実行する最適化タスク
        """
        user_id = task.user_id
        
        try:
            # 実行開始マーク
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
                
                improvements = result.get("improvements", {})
                duration = result.get("duration_seconds", 0)
                
                self.logger.info(
                    f"Optimization completed for user {user_id} in {duration:.2f}s: "
                    f"memory_reduction={improvements.get('memory_count', {}).get('reduction', 0)}, "
                    f"quality_improvement={improvements.get('quality', {}).get('improvement', 0):.3f}"
                )
            else:
                # 失敗時の処理
                error_msg = result.get("error", "Unknown error")
                self.logger.warning(f"Optimization failed for user {user_id}: {error_msg}")
                
                # 失敗時はカウンターを半分にリセット（完全にリセットしない）
                self.user_memory_counts[user_id] = max(0, self.user_memory_counts.get(user_id, 0) // 2)
                
        except Exception as e:
            self.logger.error(f"Optimization execution failed for user {user_id}: {e}", exc_info=True)
        finally:
            # 実行完了マーク
            self.running_optimizations.discard(user_id)
    
    async def _periodic_scheduler(self):
        """定期的な最適化スケジューリング
        
        長期間最適化されていないユーザーに対して定期最適化をスケジュールする。
        """
        self.logger.info("Periodic scheduler started")
        
        while self.is_running:
            try:
                await asyncio.sleep(self.auto_optimize_interval)
                
                if not self.is_running:
                    break
                
                # アクティブユーザーの定期最適化
                current_time = datetime.now()
                periodic_threshold = timedelta(seconds=self.auto_optimize_interval * 2)
                
                for user_id, last_time in list(self.last_optimization_times.items()):
                    if current_time - last_time > periodic_threshold:
                        self.logger.debug(f"Scheduling periodic optimization for user {user_id}")
                        self._schedule_optimization(user_id, "periodic", priority=1)
                
            except asyncio.CancelledError:
                self.logger.info("Periodic scheduler cancelled")
                break
            except Exception as e:
                self.logger.error(f"Periodic scheduler error: {e}", exc_info=True)
        
        self.logger.info("Periodic scheduler stopped")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """スケジューラー状態取得
        
        Returns:
            Dict[str, Any]: スケジューラーの現在状態
        """
        return {
            "is_running": self.is_running,
            "queue_size": self.optimization_tasks.qsize(),
            "running_optimizations": len(self.running_optimizations),
            "running_optimization_users": list(self.running_optimizations),
            "user_memory_counts": dict(self.user_memory_counts),
            "last_optimization_times": {
                user_id: time.isoformat() 
                for user_id, time in self.last_optimization_times.items()
            },
            "worker_tasks_count": len(self.worker_tasks),
            "config": {
                "auto_optimize_interval": self.auto_optimize_interval,
                "auto_optimize_threshold": self.auto_optimize_threshold,
                "max_concurrent_optimizations": self.max_concurrent_optimizations,
                "enable_background_optimization": self.enable_background_optimization
            }
        }
    
    def force_optimization(self, user_id: str, optimization_type: str = "full"):
        """手動最適化のトリガー
        
        Args:
            user_id: 対象ユーザーID
            optimization_type: 最適化タイプ
        """
        self.logger.info(f"Force optimization requested for user {user_id}: {optimization_type}")
        self._schedule_optimization(user_id, optimization_type, priority=2)  # 最高優先度
    
    def reset_user_memory_count(self, user_id: str):
        """ユーザーの記憶カウントをリセット
        
        Args:
            user_id: 対象ユーザーID
        """
        if user_id in self.user_memory_counts:
            old_count = self.user_memory_counts[user_id]
            self.user_memory_counts[user_id] = 0
            self.logger.debug(f"Reset memory count for user {user_id}: {old_count} -> 0")
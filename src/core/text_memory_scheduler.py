"""
CocoroCore2 テキストメモリスケジューラー統合モジュール

MemOSのGeneralSchedulerをCocoroCore2に統合するためのレイヤー
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

# MemOS関連のインポート（遅延インポートで対応）
try:
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
except ImportError as e:
    # MemOSが利用できない場合の対応
    SchedulerFactory = None
    GeneralScheduler = None
    ScheduleMessageItem = None
    QUERY_LABEL = "query"
    ANSWER_LABEL = "answer"
    ADD_LABEL = "add"
    BaseLLM = None
    GeneralMemCube = None
    _memos_import_error = e
else:
    _memos_import_error = None

from ..config import CocoroCore2Config
from .scheduler_config import create_scheduler_config_factory, validate_scheduler_config


class TextMemorySchedulerManager:
    """テキストメモリスケジューラー管理クラス"""
    
    def __init__(self, config: CocoroCore2Config):
        """初期化
        
        Args:
            config: CocoroCore2設定
            
        Raises:
            ImportError: MemOSライブラリが利用できない場合
            ValueError: 設定が無効な場合
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.scheduler: Optional["GeneralScheduler"] = None
        self.is_initialized = False
        self.is_running = False
        
        # MemOSライブラリの利用可能性をチェック
        if _memos_import_error is not None:
            raise ImportError(f"MemOSライブラリが利用できません: {_memos_import_error}")
        
        # 設定検証
        if not validate_scheduler_config(config):
            raise ValueError("Invalid scheduler configuration")
        
        self.logger.info("TextMemorySchedulerManager initialized with config validation passed")
    
    def initialize(self, chat_llm: "BaseLLM", process_llm: Optional["BaseLLM"] = None):
        """スケジューラーを初期化
        
        Args:
            chat_llm: チャット用LLM
            process_llm: 処理用LLM（Noneの場合はchat_llmを使用）
            
        Raises:
            RuntimeError: 初期化に失敗した場合
        """
        try:
            self.logger.info("Initializing text memory scheduler...")
            
            # MemOSライブラリの利用可能性を再チェック
            if _memos_import_error is not None:
                raise RuntimeError(f"MemOSライブラリが利用できません: {_memos_import_error}")
            
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
            self.is_initialized = False
            raise RuntimeError(f"スケジューラーの初期化に失敗しました: {e}")
    
    async def start(self):
        """スケジューラーを開始
        
        Raises:
            RuntimeError: 開始に失敗した場合
        """
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
            self.is_running = False
            raise RuntimeError(f"スケジューラーの開始に失敗しました: {e}")
    
    async def stop(self):
        """スケジューラーを停止"""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        try:
            self.logger.info("Stopping text memory scheduler...")
            if self.scheduler:
                self.scheduler.stop()
            self.is_running = False
            self.logger.info("Text memory scheduler stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop text memory scheduler: {e}")
            # 停止エラーでも状態は停止扱いにする
            self.is_running = False
            raise RuntimeError(f"スケジューラーの停止に失敗しました: {e}")
    
    def submit_query_message(self, user_id: str, content: str, mem_cube: "GeneralMemCube"):
        """クエリメッセージを送信
        
        Args:
            user_id: ユーザーID
            content: クエリ内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping query message")
            return
        
        if ScheduleMessageItem is None:
            self.logger.error("MemOS library not available, cannot submit message")
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
    
    def submit_answer_message(self, user_id: str, content: str, mem_cube: "GeneralMemCube"):
        """応答メッセージを送信
        
        Args:
            user_id: ユーザーID
            content: 応答内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping answer message")
            return
        
        if ScheduleMessageItem is None:
            self.logger.error("MemOS library not available, cannot submit message")
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
    
    def submit_add_message(self, user_id: str, content: str, mem_cube: "GeneralMemCube"):
        """記憶追加メッセージを送信
        
        Args:
            user_id: ユーザーID
            content: 記憶内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping add message")
            return
        
        if ScheduleMessageItem is None:
            self.logger.error("MemOS library not available, cannot submit message")
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
            "memos_available": _memos_import_error is None,
            "configuration": {
                "top_k": self.config.mem_scheduler.top_k,
                "context_window_size": self.config.mem_scheduler.context_window_size,
                "enable_act_memory_update": self.config.mem_scheduler.enable_act_memory_update,
                "enable_parallel_dispatch": self.config.mem_scheduler.enable_parallel_dispatch,
                "thread_pool_max_workers": self.config.mem_scheduler.thread_pool_max_workers,
                "consume_interval_seconds": self.config.mem_scheduler.consume_interval_seconds,
                "text_memory_optimization": self.config.mem_scheduler.text_memory_optimization
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
    
    def is_available(self) -> bool:
        """スケジューラーが利用可能かどうかを確認
        
        Returns:
            bool: 利用可能な場合True
        """
        return (_memos_import_error is None and 
                self.config.mem_scheduler.enabled and 
                validate_scheduler_config(self.config))
    
    def get_memory_optimization_config(self) -> Dict[str, Any]:
        """テキストメモリ最適化設定を取得
        
        Returns:
            Dict[str, Any]: 最適化設定
        """
        return self.config.mem_scheduler.text_memory_optimization
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            if self.is_running:
                # 非同期でstop()を呼び出す代わりに、同期的に停止処理を行う
                if self.scheduler:
                    self.scheduler.stop()
                self.is_running = False
                self.logger.info("Scheduler stopped during cleanup")
            
            self.scheduler = None
            self.is_initialized = False
            self.logger.info("TextMemorySchedulerManager cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            # クリーンアップエラーでも状態をリセット
            self.scheduler = None
            self.is_initialized = False
            self.is_running = False
"""
MemOSスケジューラー設定管理モジュール

CocoroCore2ConfigからMemOSスケジューラー設定への変換を担当
"""

import logging
from typing import Dict, Any

try:
    from memos.configs.mem_scheduler import SchedulerConfigFactory, GeneralSchedulerConfig
except ImportError as e:
    # MemOSが利用できない場合の対応
    SchedulerConfigFactory = None
    GeneralSchedulerConfig = None
    _memos_import_error = e
else:
    _memos_import_error = None

from ..config import CocoroCore2Config


logger = logging.getLogger(__name__)


def _check_memos_availability():
    """MemOSライブラリの利用可能性をチェック"""
    if _memos_import_error is not None:
        raise ImportError(f"MemOSライブラリが利用できません: {_memos_import_error}")


def create_scheduler_config_factory(config: CocoroCore2Config) -> "SchedulerConfigFactory":
    """CocoroCore2ConfigからSchedulerConfigFactoryを作成
    
    Args:
        config: CocoroCore2設定
        
    Returns:
        SchedulerConfigFactory: MemOSスケジューラー設定ファクトリー
        
    Raises:
        ImportError: MemOSライブラリが利用できない場合
        ValueError: 設定が無効な場合
    """
    _check_memos_availability()
    
    # スケジューラー設定辞書を作成
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
    
    try:
        return SchedulerConfigFactory(
            backend="general_scheduler",
            config=scheduler_config_dict
        )
    except Exception as e:
        logger.error(f"Failed to create SchedulerConfigFactory: {e}")
        raise ValueError(f"スケジューラー設定の作成に失敗しました: {e}")


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
    
    # MemOSライブラリの利用可能性をチェック
    try:
        _check_memos_availability()
    except ImportError as e:
        logger.error(f"MemOS library not available: {e}")
        return False
    
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


def get_scheduler_config_summary(config: CocoroCore2Config) -> Dict[str, Any]:
    """スケジューラー設定の要約を取得（デバッグ用）
    
    Args:
        config: CocoroCore2設定
        
    Returns:
        Dict[str, Any]: 設定要約
    """
    mem_sched_config = config.mem_scheduler
    
    return {
        "enabled": mem_sched_config.enabled,
        "top_k": mem_sched_config.top_k,
        "context_window_size": mem_sched_config.context_window_size,
        "enable_act_memory_update": mem_sched_config.enable_act_memory_update,
        "enable_parallel_dispatch": mem_sched_config.enable_parallel_dispatch,
        "thread_pool_max_workers": mem_sched_config.thread_pool_max_workers,
        "consume_interval_seconds": mem_sched_config.consume_interval_seconds,
        "act_mem_update_interval": mem_sched_config.act_mem_update_interval,
        "text_memory_optimization": mem_sched_config.text_memory_optimization,
        "memos_available": _memos_import_error is None
    }
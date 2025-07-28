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
    
    # Phase 3: 自動最適化設定の検証
    if not validate_auto_optimization_config(mem_sched_config):
        return False
    
    # Phase 3: テキストメモリ最適化設定の検証
    if not validate_text_memory_optimization_config(mem_sched_config.text_memory_optimization):
        return False
    
    # Phase 3: 互換性チェック
    if not validate_phase3_compatibility(config):
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


# ===========================================
# Phase 3: 設定検証機能
# ===========================================

def validate_auto_optimization_config(mem_scheduler) -> bool:
    """自動最適化設定の検証
    
    Args:
        mem_scheduler: MemSchedulerConfig
        
    Returns:
        bool: 設定が有効な場合True
    """
    try:
        # enable_auto_optimization
        if not isinstance(mem_scheduler.enable_auto_optimization, bool):
            logger.error("enable_auto_optimization must be a boolean")
            return False
        
        # auto_optimize_interval
        interval = mem_scheduler.auto_optimize_interval
        if not isinstance(interval, int) or not (60 <= interval <= 86400):
            logger.error("auto_optimize_interval must be an integer between 60 and 86400 seconds")
            return False
        
        # auto_optimize_threshold
        threshold = mem_scheduler.auto_optimize_threshold
        if not isinstance(threshold, int) or not (1 <= threshold <= 1000):
            logger.error("auto_optimize_threshold must be an integer between 1 and 1000")
            return False
        
        # max_concurrent_optimizations
        max_concurrent = mem_scheduler.max_concurrent_optimizations
        if not isinstance(max_concurrent, int) or not (1 <= max_concurrent <= 10):
            logger.error("max_concurrent_optimizations must be an integer between 1 and 10")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Auto optimization config validation failed: {e}")
        return False


def validate_text_memory_optimization_config(text_opt: Dict[str, Any]) -> bool:
    """テキストメモリ最適化設定の検証
    
    Args:
        text_opt: テキストメモリ最適化設定辞書
        
    Returns:
        bool: 設定が有効な場合True
    """
    try:
        if not isinstance(text_opt, dict):
            logger.error("text_memory_optimization must be a dictionary")
            return False
        
        # Phase 3設定項目の検証
        validations = [
            ("similarity_threshold", float, 0.0, 1.0),
            ("working_memory_size", int, 1, 100),
            ("auto_optimize_interval", int, 60, 86400),
            ("auto_optimize_threshold", int, 1, 1000),
            ("max_concurrent_optimizations", int, 1, 10),
            ("min_memory_length", int, 1, 1000),
            ("quality_score_threshold", float, 0.0, 1.0),
            ("optimization_batch_size", int, 1, 1000),
        ]
        
        for key, expected_type, min_val, max_val in validations:
            if key in text_opt:
                value = text_opt[key]
                if not isinstance(value, expected_type):
                    logger.error(f"{key} must be of type {expected_type.__name__}")
                    return False
                if not (min_val <= value <= max_val):
                    logger.error(f"{key} must be between {min_val} and {max_val}")
                    return False
        
        # Boolean設定項目の検証
        boolean_configs = [
            "enable_deduplication",
            "graceful_degradation", 
            "log_scheduler_errors",
            "enable_background_optimization",
            "similarity_analysis_enabled",
            "reranking_enabled",
            "memory_lifecycle_management"
        ]
        
        for key in boolean_configs:
            if key in text_opt and not isinstance(text_opt[key], bool):
                logger.error(f"{key} must be a boolean")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Text memory optimization config validation failed: {e}")
        return False


def validate_phase3_compatibility(config: CocoroCore2Config) -> bool:
    """Phase 3機能の互換性チェック
    
    Args:
        config: CocoroCore2設定
        
    Returns:
        bool: 互換性がある場合True
    """
    try:
        mem_scheduler = config.mem_scheduler
        
        # 自動最適化が有効な場合、スケジューラーも有効である必要がある
        if mem_scheduler.enable_auto_optimization and not mem_scheduler.enabled:
            logger.error("Scheduler must be enabled when auto_optimization is enabled")
            return False
        
        # 自動最適化の間隔と閾値の整合性チェック
        interval = mem_scheduler.auto_optimize_interval
        threshold = mem_scheduler.auto_optimize_threshold
        
        # 閾値が大きすぎる場合、実用的でない設定として警告
        if threshold > 500:
            logger.warning(f"auto_optimize_threshold ({threshold}) is quite large, consider reducing it")
        
        # 間隔が短すぎる場合、システム負荷の懸念として警告
        if interval < 300:  # 5分未満
            logger.warning(f"auto_optimize_interval ({interval}s) is quite short, may increase system load")
        
        # text_memory_optimization内の重複設定の整合性チェック
        text_opt = mem_scheduler.text_memory_optimization
        if "auto_optimize_interval" in text_opt and text_opt["auto_optimize_interval"] != interval:
            logger.warning("auto_optimize_interval mismatch between main config and text_memory_optimization")
        
        if "auto_optimize_threshold" in text_opt and text_opt["auto_optimize_threshold"] != threshold:
            logger.warning("auto_optimize_threshold mismatch between main config and text_memory_optimization")
        
        return True
        
    except Exception as e:
        logger.error(f"Phase 3 compatibility check failed: {e}")
        return False
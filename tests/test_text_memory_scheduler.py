"""
テキストメモリスケジューラー統合テスト

スケジューラーモジュールの単体テストと統合テスト
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.config import CocoroCore2Config
from src.core.text_memory_scheduler import TextMemorySchedulerManager
from src.core.scheduler_config import (
    validate_scheduler_config, 
    create_scheduler_config_factory, 
    get_text_memory_optimization_config,
    get_scheduler_config_summary
)


class TestSchedulerConfig:
    """スケジューラー設定テストクラス"""
    
    @pytest.fixture
    def sample_config(self):
        """テスト用設定を作成"""
        config_data = {
            "version": "2.0.0",
            "environment": "test",
            "mos_config": {
                "chat_model": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "gpt-4o-mini",
                        "api_key": "test-key"
                    }
                },
                "mem_reader": {
                    "backend": "simple_struct",
                    "config": {
                        "llm": {
                            "backend": "openai",
                            "config": {
                                "model_name_or_path": "gpt-4o-mini",
                                "api_key": "test-key"
                            }
                        },
                        "embedder": {
                            "backend": "openai",
                            "config": {
                                "model_name_or_path": "text-embedding-3-small",
                                "api_key": "test-key"
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
                }
            },
            "mem_scheduler": {
                "enabled": True,
                "top_k": 8,
                "context_window_size": 6,
                "enable_act_memory_update": False,
                "enable_parallel_dispatch": True,
                "thread_pool_max_workers": 4,
                "consume_interval_seconds": 1,
                "act_mem_update_interval": 600,
                "text_memory_optimization": {
                    "enable_deduplication": True,
                    "similarity_threshold": 0.9,
                    "working_memory_size": 25,
                    "long_term_memory_capacity": 15000,
                    "user_memory_capacity": 12000
                }
            }
        }
        return CocoroCore2Config(**config_data)
    
    def test_validate_scheduler_config_valid(self, sample_config):
        """有効なスケジューラー設定の検証テスト"""
        assert validate_scheduler_config(sample_config) == True
    
    def test_validate_scheduler_config_invalid_values(self, sample_config):
        """無効な値を持つスケジューラー設定の検証テスト"""
        # 負のtop_k
        sample_config.mem_scheduler.top_k = -1
        assert validate_scheduler_config(sample_config) == False
        
        # 0のcontext_window_size
        sample_config.mem_scheduler.top_k = 5  # 復元
        sample_config.mem_scheduler.context_window_size = 0
        assert validate_scheduler_config(sample_config) == False
        
        # 負のthread_pool_max_workers
        sample_config.mem_scheduler.context_window_size = 5  # 復元
        sample_config.mem_scheduler.thread_pool_max_workers = -1
        assert validate_scheduler_config(sample_config) == False
    
    def test_get_text_memory_optimization_config(self, sample_config):
        """テキストメモリ最適化設定取得テスト"""
        optimization_config = get_text_memory_optimization_config(sample_config)
        
        assert optimization_config["enable_deduplication"] == True
        assert optimization_config["similarity_threshold"] == 0.9
        assert optimization_config["working_memory_size"] == 25
        assert optimization_config["long_term_memory_capacity"] == 15000
        assert optimization_config["user_memory_capacity"] == 12000
    
    def test_get_scheduler_config_summary(self, sample_config):
        """スケジューラー設定要約取得テスト"""
        summary = get_scheduler_config_summary(sample_config)
        
        assert summary["enabled"] == True
        assert summary["top_k"] == 8
        assert summary["context_window_size"] == 6
        assert summary["enable_act_memory_update"] == False
        assert summary["enable_parallel_dispatch"] == True
        assert summary["thread_pool_max_workers"] == 4
        assert "memos_available" in summary
        assert "text_memory_optimization" in summary
    
    @patch('src.core.scheduler_config._memos_import_error', None)
    @patch('src.core.scheduler_config.SchedulerConfigFactory')
    def test_create_scheduler_config_factory_success(self, mock_factory_class, sample_config):
        """SchedulerConfigFactory作成成功テスト"""
        mock_factory = Mock()
        mock_factory_class.return_value = mock_factory
        
        result = create_scheduler_config_factory(sample_config)
        
        # SchedulerConfigFactoryが正しい引数で呼び出されることを確認
        mock_factory_class.assert_called_once()
        call_args = mock_factory_class.call_args
        assert call_args[1]["backend"] == "general_scheduler"
        assert "top_k" in call_args[1]["config"]
        assert call_args[1]["config"]["top_k"] == 8
        
        assert result == mock_factory
    
    @patch('src.core.scheduler_config._memos_import_error', ImportError("test error"))
    def test_create_scheduler_config_factory_import_error(self, sample_config):
        """MemOSインポートエラー時のテスト"""
        with pytest.raises(ImportError):
            create_scheduler_config_factory(sample_config)


class TestTextMemorySchedulerManager:
    """TextMemorySchedulerManagerテストクラス"""
    
    @pytest.fixture
    def sample_config(self):
        """テスト用設定を作成"""
        config_data = {
            "version": "2.0.0",
            "environment": "test",
            "mos_config": {
                "chat_model": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "gpt-4o-mini",
                        "api_key": "test-key"
                    }
                },
                "mem_reader": {
                    "backend": "simple_struct",
                    "config": {
                        "llm": {
                            "backend": "openai",
                            "config": {
                                "model_name_or_path": "gpt-4o-mini",
                                "api_key": "test-key"
                            }
                        },
                        "embedder": {
                            "backend": "openai",
                            "config": {
                                "model_name_or_path": "text-embedding-3-small",
                                "api_key": "test-key"
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
                }
            },
            "mem_scheduler": {
                "enabled": True,
                "top_k": 5,
                "context_window_size": 5,
                "enable_act_memory_update": False,
                "enable_parallel_dispatch": False,
                "thread_pool_max_workers": 3,
                "consume_interval_seconds": 2,
                "act_mem_update_interval": 300,
                "text_memory_optimization": {
                    "enable_deduplication": True,
                    "similarity_threshold": 0.95,
                    "working_memory_size": 20,
                    "long_term_memory_capacity": 10000,
                    "user_memory_capacity": 10000
                }
            }
        }
        return CocoroCore2Config(**config_data)
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    def test_scheduler_manager_initialization_success(self, sample_config):
        """スケジューラーマネージャー初期化成功テスト"""
        manager = TextMemorySchedulerManager(sample_config)
        
        assert manager.config == sample_config
        assert manager.is_initialized == False
        assert manager.is_running == False
        assert manager.scheduler is None
    
    @patch('src.core.text_memory_scheduler._memos_import_error', ImportError("test error"))
    def test_scheduler_manager_initialization_import_error(self, sample_config):
        """MemOSインポートエラー時の初期化テスト"""
        with pytest.raises(ImportError):
            TextMemorySchedulerManager(sample_config)
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    def test_scheduler_manager_initialization_invalid_config(self, sample_config):
        """無効な設定での初期化テスト"""
        # 無効な設定にする
        sample_config.mem_scheduler.top_k = -1
        
        with pytest.raises(ValueError):
            TextMemorySchedulerManager(sample_config)
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    def test_get_scheduler_status(self, sample_config):
        """スケジューラーステータス取得テスト"""
        manager = TextMemorySchedulerManager(sample_config)
        status = manager.get_scheduler_status()
        
        assert status["initialized"] == False
        assert status["running"] == False
        assert status["enabled"] == True
        assert status["memos_available"] == True
        assert "configuration" in status
        assert status["configuration"]["top_k"] == 5
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    def test_is_available(self, sample_config):
        """利用可能性チェックテスト"""
        manager = TextMemorySchedulerManager(sample_config)
        assert manager.is_available() == True
        
        # 無効な設定にする
        sample_config.mem_scheduler.enabled = False
        manager_disabled = TextMemorySchedulerManager(sample_config)
        assert manager_disabled.is_available() == False
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    def test_get_memory_optimization_config(self, sample_config):
        """メモリ最適化設定取得テスト"""
        manager = TextMemorySchedulerManager(sample_config)
        optimization_config = manager.get_memory_optimization_config()
        
        assert optimization_config["enable_deduplication"] == True
        assert optimization_config["similarity_threshold"] == 0.95
        assert optimization_config["working_memory_size"] == 20
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    def test_cleanup(self, sample_config):
        """クリーンアップテスト"""
        manager = TextMemorySchedulerManager(sample_config)
        
        # クリーンアップ実行
        manager.cleanup()
        
        assert manager.scheduler is None
        assert manager.is_initialized == False
        assert manager.is_running == False
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    @patch('src.core.text_memory_scheduler.SchedulerFactory')
    def test_initialize_success(self, mock_scheduler_factory, sample_config):
        """スケジューラー初期化成功テスト"""
        # モックスケジューラーを設定
        mock_scheduler = Mock()
        mock_scheduler_factory.from_config.return_value = mock_scheduler
        
        # モックLLMを作成
        mock_chat_llm = Mock()
        
        manager = TextMemorySchedulerManager(sample_config)
        manager.initialize(mock_chat_llm)
        
        assert manager.is_initialized == True
        assert manager.scheduler == mock_scheduler
        
        # initialize_modulesが呼び出されることを確認
        mock_scheduler.initialize_modules.assert_called_once_with(mock_chat_llm, mock_chat_llm)
    
    @patch('src.core.text_memory_scheduler._memos_import_error', None)
    def test_submit_message_not_running(self, sample_config):
        """スケジューラー未実行時のメッセージ送信テスト"""
        manager = TextMemorySchedulerManager(sample_config)
        
        # スケジューラーが実行されていない状態でメッセージ送信
        mock_mem_cube = Mock()
        mock_mem_cube.config.cube_id = "test_cube"
        
        # 警告ログが出力されることを確認（例外は発生しない）
        manager.submit_query_message("test_user", "test content", mock_mem_cube)
        manager.submit_answer_message("test_user", "test answer", mock_mem_cube)
        manager.submit_add_message("test_user", "test memory", mock_mem_cube)
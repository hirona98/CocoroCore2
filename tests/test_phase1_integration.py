"""
Phase 1統合テスト

CocoroCore2Appとテキストメモリスケジューラーの統合をテスト
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.config import CocoroCore2Config
from src.core_app import CocoroCore2App


class TestPhase1Integration:
    """Phase 1統合テストクラス"""
    
    @pytest.fixture
    def sample_config_with_scheduler_enabled(self):
        """スケジューラー有効の設定を作成"""
        config_data = {
            "version": "2.0.0",
            "environment": "test",
            "mos_config": {
                "user_id": "test_user",
                "chat_model": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "gpt-4o-mini",
                        "api_key": "test-key",
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
    
    @pytest.fixture
    def sample_config_with_scheduler_disabled(self):
        """スケジューラー無効の設定を作成"""
        config_data = {
            "version": "2.0.0",
            "environment": "test",
            "mos_config": {
                "user_id": "test_user",
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
                "enabled": False,
                "top_k": 5,
                "context_window_size": 5,
                "enable_act_memory_update": False,
                "enable_parallel_dispatch": False,
                "thread_pool_max_workers": 3,
                "consume_interval_seconds": 2,
                "act_mem_update_interval": 300
            }
        }
        return CocoroCore2Config(**config_data)
    
    @patch('src.core_app.MOS')
    def test_app_initialization_with_scheduler_enabled(self, mock_mos_class, sample_config_with_scheduler_enabled):
        """スケジューラー有効時のアプリケーション初期化テスト"""
        # MOSインスタンスをモック
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        with patch('src.core.text_memory_scheduler._memos_import_error', None):
            app = CocoroCore2App(sample_config_with_scheduler_enabled)
            
            # アプリケーションが正常に初期化される
            assert app.config == sample_config_with_scheduler_enabled
            assert app.mos == mock_mos
            assert app.text_memory_scheduler is not None
            assert app.is_running == False
    
    @patch('src.core_app.MOS')
    def test_app_initialization_with_scheduler_disabled(self, mock_mos_class, sample_config_with_scheduler_disabled):
        """スケジューラー無効時のアプリケーション初期化テスト"""
        # MOSインスタンスをモック
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config_with_scheduler_disabled)
        
        # アプリケーションが正常に初期化される
        assert app.config == sample_config_with_scheduler_disabled
        assert app.mos == mock_mos
        assert app.text_memory_scheduler is None
        assert app.is_running == False
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler._memos_import_error', ImportError("test error"))
    def test_app_initialization_with_scheduler_import_error(self, mock_mos_class, sample_config_with_scheduler_enabled):
        """MemOSインポートエラー時のアプリケーション初期化テスト"""
        # MOSインスタンスをモック
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config_with_scheduler_enabled)
        
        # スケジューラーエラーでもアプリケーションは初期化される
        assert app.config == sample_config_with_scheduler_enabled
        assert app.mos == mock_mos
        assert app.text_memory_scheduler is None  # エラーのため作成されない
        assert app.is_running == False
    
    @patch('src.core_app.MOS')
    def test_get_chat_llm_from_mos_success(self, mock_mos_class, sample_config_with_scheduler_enabled):
        """MOSからLLM取得成功テスト"""
        # MOSインスタンスとchat_llmをモック
        mock_mos = Mock()
        mock_chat_llm = Mock()
        mock_mos.chat_llm = mock_chat_llm
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config_with_scheduler_enabled)
        
        # chat_llmが正常に取得される
        result_llm = app._get_chat_llm_from_mos()
        assert result_llm == mock_chat_llm
    
    @patch('src.core_app.MOS')
    @patch('src.core_app.LLMFactory')
    @patch('src.core_app.LLMConfigFactory')
    def test_get_chat_llm_from_mos_fallback(self, mock_llm_config_factory, mock_llm_factory, mock_mos_class, sample_config_with_scheduler_enabled):
        """MOSからLLM取得フォールバックテスト"""
        # MOSインスタンスでchat_llmが存在しない場合をモック
        mock_mos = Mock()
        mock_mos.chat_llm = None
        mock_mos_class.return_value = mock_mos
        
        # フォールバック用のLLMをモック
        mock_llm_config = Mock()
        mock_llm_config_factory.return_value = mock_llm_config
        mock_fallback_llm = Mock()
        mock_llm_factory.from_config.return_value = mock_fallback_llm
        
        app = CocoroCore2App(sample_config_with_scheduler_enabled)
        
        # フォールバックでLLMが取得される
        result_llm = app._get_chat_llm_from_mos()
        assert result_llm == mock_fallback_llm
        mock_llm_factory.from_config.assert_called_once_with(mock_llm_config)
    
    @patch('src.core_app.MOS')
    def test_app_status_with_scheduler_enabled(self, mock_mos_class, sample_config_with_scheduler_enabled):
        """スケジューラー有効時のアプリケーション状態取得テスト"""
        # MOSインスタンスをモック
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        with patch('src.core.text_memory_scheduler._memos_import_error', None):
            app = CocoroCore2App(sample_config_with_scheduler_enabled)
            status = app.get_app_status()
            
            # スケジューラー情報が含まれる
            assert "scheduler_status" in status
            assert status["features"]["text_memory_scheduler_enabled"] == True
            assert status["scheduler_status"]["enabled"] == True
            assert status["scheduler_status"]["initialized"] == False  # まだ初期化されていない
            assert status["scheduler_status"]["running"] == False
    
    @patch('src.core_app.MOS')
    def test_app_status_with_scheduler_disabled(self, mock_mos_class, sample_config_with_scheduler_disabled):
        """スケジューラー無効時のアプリケーション状態取得テスト"""
        # MOSインスタンスをモック
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config_with_scheduler_disabled)
        status = app.get_app_status()
        
        # スケジューラー情報が含まれる（無効状態）
        assert "scheduler_status" in status
        assert status["features"]["text_memory_scheduler_enabled"] == False
        assert status["scheduler_status"]["enabled"] == False
        assert status["scheduler_status"]["available"] == False
        assert status["scheduler_status"]["reason"] == "scheduler not created"
    
    @patch('src.core_app.MOS')
    @pytest.mark.asyncio
    async def test_app_startup_and_shutdown_with_scheduler(self, mock_mos_class, sample_config_with_scheduler_enabled):
        """スケジューラー付きアプリケーションの起動・終了テスト"""
        # MOSインスタンスをモック
        mock_mos = Mock()
        mock_mos.create_user = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        with patch('src.core.text_memory_scheduler._memos_import_error', None):
            with patch('src.core.text_memory_scheduler.SchedulerFactory') as mock_scheduler_factory:
                # スケジューラーをモック
                mock_scheduler = Mock()
                mock_scheduler.initialize_modules = Mock()
                mock_scheduler.start = Mock()
                mock_scheduler.stop = Mock()
                mock_scheduler_factory.from_config.return_value = mock_scheduler
                
                # chat_llmをモック
                mock_chat_llm = Mock()
                mock_mos.chat_llm = mock_chat_llm
                
                app = CocoroCore2App(sample_config_with_scheduler_enabled)
                
                # 起動テスト
                await app.startup()
                assert app.is_running == True
                
                # スケジューラーが初期化・開始される
                if app.text_memory_scheduler:
                    mock_scheduler.initialize_modules.assert_called_once_with(mock_chat_llm)
                    mock_scheduler.start.assert_called_once()
                
                # 終了テスト
                await app.shutdown()
                assert app.is_running == False
                
                # スケジューラーが停止される
                if app.text_memory_scheduler and hasattr(app.text_memory_scheduler, 'scheduler'):
                    mock_scheduler.stop.assert_called_once()
    
    def test_backward_compatibility(self, sample_config_with_scheduler_disabled):
        """既存機能との後方互換性テスト"""
        with patch('src.core_app.MOS') as mock_mos_class:
            mock_mos = Mock()
            mock_mos_class.return_value = mock_mos
            
            app = CocoroCore2App(sample_config_with_scheduler_disabled)
            
            # 既存のメソッドが正常に動作する
            assert hasattr(app, 'memos_chat')
            assert hasattr(app, 'add_memory')
            assert hasattr(app, 'search_memory')
            assert hasattr(app, 'get_user_memories')
            assert hasattr(app, 'ensure_user')
            assert hasattr(app, 'get_app_status')
            
            # スケジューラー無効でも既存機能に影響がない
            assert app.text_memory_scheduler is None
            status = app.get_app_status()
            assert status["status"] == "stopped"  # まだ起動していない
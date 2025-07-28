"""
テキストメモリスケジューラー設定テスト

スケジューラー設定の読み込み、検証機能をテストする
"""

import pytest
import json
import tempfile
from pathlib import Path

from src.config import CocoroCore2Config, MemSchedulerConfig, ConfigurationError


class TestSchedulerConfig:
    """スケジューラー設定テストクラス"""
    
    def test_mem_scheduler_config_default(self):
        """MemSchedulerConfigのデフォルト値テスト"""
        config = MemSchedulerConfig()
        
        # デフォルト値の確認
        assert config.enabled == False
        assert config.top_k == 5
        assert config.context_window_size == 5
        assert config.enable_act_memory_update == False
        assert config.enable_parallel_dispatch == False
        assert config.thread_pool_max_workers == 3
        assert config.consume_interval_seconds == 2
        assert config.act_mem_update_interval == 300
        
        # テキストメモリ最適化設定の確認
        assert config.text_memory_optimization["enable_deduplication"] == True
        assert config.text_memory_optimization["similarity_threshold"] == 0.95
        assert config.text_memory_optimization["working_memory_size"] == 20
        assert config.text_memory_optimization["long_term_memory_capacity"] == 10000
        assert config.text_memory_optimization["user_memory_capacity"] == 10000
    
    def test_mem_scheduler_config_custom_values(self):
        """MemSchedulerConfigのカスタム値テスト"""
        custom_optimization = {
            "enable_deduplication": False,
            "similarity_threshold": 0.8,
            "working_memory_size": 15,
            "long_term_memory_capacity": 5000,
            "user_memory_capacity": 5000
        }
        
        config = MemSchedulerConfig(
            enabled=True,
            top_k=10,
            context_window_size=8,
            thread_pool_max_workers=5,
            consume_interval_seconds=1,
            text_memory_optimization=custom_optimization
        )
        
        assert config.enabled == True
        assert config.top_k == 10
        assert config.context_window_size == 8
        assert config.thread_pool_max_workers == 5
        assert config.consume_interval_seconds == 1
        assert config.text_memory_optimization == custom_optimization
    
    def test_cocoro_core2_config_with_scheduler(self):
        """CocoroCore2Configにスケジューラー設定が含まれることをテスト"""
        config = CocoroCore2Config()
        
        # mem_schedulerフィールドが存在し、デフォルトのMemSchedulerConfigが設定されている
        assert hasattr(config, 'mem_scheduler')
        assert isinstance(config.mem_scheduler, MemSchedulerConfig)
        assert config.mem_scheduler.enabled == False
    
    def test_config_load_with_scheduler_settings(self):
        """スケジューラー設定を含む設定ファイルの読み込みテスト"""
        test_config = {
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
        
        # 一時ファイルに設定を書き込み
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f, indent=2)
            temp_path = f.name
        
        try:
            # 設定ファイルから読み込み
            config = CocoroCore2Config.load(temp_path, "test")
            
            # スケジューラー設定の確認
            assert config.mem_scheduler.enabled == True
            assert config.mem_scheduler.top_k == 8
            assert config.mem_scheduler.context_window_size == 6
            assert config.mem_scheduler.enable_parallel_dispatch == True
            assert config.mem_scheduler.thread_pool_max_workers == 4
            assert config.mem_scheduler.consume_interval_seconds == 1
            assert config.mem_scheduler.act_mem_update_interval == 600
            
            # テキストメモリ最適化設定の確認
            assert config.mem_scheduler.text_memory_optimization["similarity_threshold"] == 0.9
            assert config.mem_scheduler.text_memory_optimization["working_memory_size"] == 25
            assert config.mem_scheduler.text_memory_optimization["long_term_memory_capacity"] == 15000
            
        finally:
            # 一時ファイルを削除
            Path(temp_path).unlink()
    
    def test_config_load_without_scheduler_settings(self):
        """スケジューラー設定がない設定ファイルの読み込みテスト（デフォルト値が使用される）"""
        test_config = {
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
            }
            # mem_scheduler設定を意図的に省略
        }
        
        # 一時ファイルに設定を書き込み
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_config, f, indent=2)
            temp_path = f.name
        
        try:
            # 設定ファイルから読み込み
            config = CocoroCore2Config.load(temp_path, "test")
            
            # デフォルトのスケジューラー設定が使用されることを確認
            assert config.mem_scheduler.enabled == False
            assert config.mem_scheduler.top_k == 5
            assert config.mem_scheduler.context_window_size == 5
            assert config.mem_scheduler.enable_act_memory_update == False
            
        finally:
            # 一時ファイルを削除
            Path(temp_path).unlink()
    
    def test_invalid_scheduler_config_validation(self):
        """無効なスケジューラー設定のバリデーションテスト"""
        # 負の値のテスト
        with pytest.raises(ValueError):
            MemSchedulerConfig(top_k=-1)
        
        with pytest.raises(ValueError):
            MemSchedulerConfig(context_window_size=0)
        
        with pytest.raises(ValueError):
            MemSchedulerConfig(thread_pool_max_workers=-1)
        
        with pytest.raises(ValueError):
            MemSchedulerConfig(consume_interval_seconds=0)
    
    def test_default_config_file_loading(self):
        """デフォルト設定ファイル（default_memos_config.json）の読み込みテスト"""
        config_path = Path(__file__).parent.parent / "config" / "default_memos_config.json"
        
        if config_path.exists():
            # 設定ファイルから読み込み
            config = CocoroCore2Config.load(str(config_path), "development")
            
            # mem_scheduler設定が正しく読み込まれることを確認
            assert hasattr(config, 'mem_scheduler')
            assert isinstance(config.mem_scheduler, MemSchedulerConfig)
            
            # デフォルト設定ファイルにmem_scheduler設定が追加されていることを確認
            assert config.mem_scheduler.enabled == True  # default_memos_config.jsonではenabledがtrueに設定されている
            assert config.mem_scheduler.enable_act_memory_update == False  # テキストメモリ特化のためfalse
"""
Phase 2: ヘルパーメソッドのテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.config import CocoroCore2Config
from src.core_app import CocoroCore2App


class TestPhase2Helpers:
    """Phase 2ヘルパーメソッドのテストクラス"""
    
    @pytest.fixture
    def sample_config(self):
        """テスト用設定を作成"""
        config_data = {
            "version": "1.0.0",
            "character": {
                "name": "ココロ",
                "description": "テストキャラクター"
            },
            "mos_config": {
                "user_id": "test_user",
                "chat_model": {
                    "backend": "openai",
                    "config": {
                        "model_name_or_path": "gpt-4",
                        "temperature": 0.7,
                        "api_key": "test-api-key"
                    }
                },
                "mem_reader": {
                    "backend": "simple_struct",
                    "config": {
                        "llm": {
                            "backend": "openai",
                            "config": {
                                "model_name_or_path": "gpt-4",
                                "temperature": 0.0,
                                "api_key": "test-api-key"
                            }
                        },
                        "embedder": {
                            "backend": "openai",
                            "config": {
                                "model_name_or_path": "text-embedding-3-large",
                                "api_key": "test-api-key"
                            }
                        }
                    }
                }
            },
            "mem_scheduler": {
                "enabled": True,
                "text_memory_optimization": {
                    "graceful_degradation": True
                }
            }
        }
        return CocoroCore2Config(**config_data)
    
    @patch('src.core_app.get_mos_config')
    @patch('src.core_app.MOS')
    def test_get_user_memcube_success(self, mock_mos_class, mock_get_mos_config, sample_config):
        """MemCube取得成功テスト"""
        # MOSとMemCubeをモック
        mock_mos = Mock()
        mock_user_manager = Mock()
        mock_cube_info = Mock()
        mock_cube_info.cube_id = "test_cube_id"
        mock_cube = Mock()
        
        mock_user_manager.get_user_cubes.return_value = [mock_cube_info]
        mock_mos.user_manager = mock_user_manager
        mock_mos.mem_cubes = {"test_cube_id": mock_cube}
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # MemCube取得テスト
        result = app._get_user_memcube("test_user")
        assert result == mock_cube
        mock_user_manager.get_user_cubes.assert_called_with(user_id="test_user")
    
    @patch('src.core_app.MOS')
    def test_get_user_memcube_not_found(self, mock_mos_class, sample_config):
        """MemCubeが見つからない場合のテスト"""
        # MOSをモック
        mock_mos = Mock()
        mock_user_manager = Mock()
        mock_user_manager.get_user_cubes.return_value = []
        mock_mos.user_manager = mock_user_manager
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # MemCube取得テスト（見つからない）
        result = app._get_user_memcube("test_user")
        assert result is None
    
    @patch('src.core_app.MOS')
    def test_get_user_memcube_not_registered(self, mock_mos_class, sample_config):
        """MemCubeがMOSに登録されていない場合のテスト"""
        # MOSをモック
        mock_mos = Mock()
        mock_user_manager = Mock()
        mock_cube_info = Mock()
        mock_cube_info.cube_id = "test_cube_id"
        
        mock_user_manager.get_user_cubes.return_value = [mock_cube_info]
        mock_mos.user_manager = mock_user_manager
        mock_mos.mem_cubes = {}  # 空の辞書（登録されていない）
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # MemCube取得テスト（登録されていない）
        result = app._get_user_memcube("test_user")
        assert result is None
    
    @patch('src.core_app.MOS')
    def test_get_user_memcube_exception(self, mock_mos_class, sample_config):
        """MemCube取得時の例外処理テスト"""
        # MOSをモック
        mock_mos = Mock()
        mock_user_manager = Mock()
        mock_user_manager.get_user_cubes.side_effect = Exception("Test error")
        mock_mos.user_manager = mock_user_manager
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # MemCube取得テスト（例外発生）
        result = app._get_user_memcube("test_user")
        assert result is None
    
    @patch('src.core_app.MOS')
    def test_get_user_memcube_id_success(self, mock_mos_class, sample_config):
        """MemCube ID取得成功テスト"""
        # MOSをモック
        mock_mos = Mock()
        mock_user_manager = Mock()
        mock_cube_info = Mock()
        mock_cube_info.cube_id = "test_cube_id"
        
        mock_user_manager.get_user_cubes.return_value = [mock_cube_info]
        mock_mos.user_manager = mock_user_manager
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # MemCube ID取得テスト
        result = app._get_user_memcube_id("test_user")
        assert result == "test_cube_id"
    
    @patch('src.core_app.MOS')
    def test_get_user_memcube_id_not_found(self, mock_mos_class, sample_config):
        """MemCube IDが見つからない場合のテスト"""
        # MOSをモック
        mock_mos = Mock()
        mock_user_manager = Mock()
        mock_user_manager.get_user_cubes.return_value = []
        mock_mos.user_manager = mock_user_manager
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # MemCube ID取得テスト（見つからない）
        result = app._get_user_memcube_id("test_user")
        assert result is None
    
    @patch('src.core_app.MOS')
    def test_safely_submit_to_scheduler_success(self, mock_mos_class, sample_config):
        """スケジューラーへの安全な送信成功テスト"""
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        app.text_memory_scheduler = mock_scheduler
        
        # 送信関数をモック
        mock_submit_func = Mock()
        
        # 送信テスト
        result = app._safely_submit_to_scheduler(
            "test_action",
            mock_submit_func,
            "arg1", "arg2",
            kwarg1="value1"
        )
        
        assert result is True
        mock_submit_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    
    @patch('src.core_app.MOS')
    def test_safely_submit_to_scheduler_not_available(self, mock_mos_class, sample_config):
        """スケジューラーが利用不可の場合のテスト"""
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # スケジューラーなし
        app.text_memory_scheduler = None
        
        # 送信関数をモック
        mock_submit_func = Mock()
        
        # 送信テスト
        result = app._safely_submit_to_scheduler(
            "test_action",
            mock_submit_func
        )
        
        assert result is False
        mock_submit_func.assert_not_called()
    
    @patch('src.core_app.MOS')
    def test_safely_submit_to_scheduler_not_running(self, mock_mos_class, sample_config):
        """スケジューラーが実行中でない場合のテスト"""
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # スケジューラーをモック（実行中でない）
        mock_scheduler = Mock()
        mock_scheduler.is_running = False
        app.text_memory_scheduler = mock_scheduler
        
        # 送信関数をモック
        mock_submit_func = Mock()
        
        # 送信テスト
        result = app._safely_submit_to_scheduler(
            "test_action",
            mock_submit_func
        )
        
        assert result is False
        mock_submit_func.assert_not_called()
    
    @patch('src.core_app.MOS')
    def test_safely_submit_to_scheduler_exception_graceful(self, mock_mos_class, sample_config):
        """送信時の例外処理（グレースフルデグラデーション）テスト"""
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        app.text_memory_scheduler = mock_scheduler
        
        # 送信関数をモック（例外発生）
        mock_submit_func = Mock(side_effect=Exception("Test error"))
        
        # 送信テスト
        result = app._safely_submit_to_scheduler(
            "test_action",
            mock_submit_func
        )
        
        assert result is False
    
    @patch('src.core_app.MOS')
    def test_safely_submit_to_scheduler_exception_raise(self, mock_mos_class, sample_config):
        """送信時の例外処理（例外再発生）テスト"""
        # グレースフルデグラデーションを無効化
        sample_config.mem_scheduler.text_memory_optimization["graceful_degradation"] = False
        
        mock_mos = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config)
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        app.text_memory_scheduler = mock_scheduler
        
        # 送信関数をモック（例外発生）
        mock_submit_func = Mock(side_effect=Exception("Test error"))
        
        # 送信テスト（例外が再発生することを確認）
        with pytest.raises(Exception, match="Test error"):
            app._safely_submit_to_scheduler(
                "test_action",
                mock_submit_func
            )
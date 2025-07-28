"""
Phase 2: 記憶追加スケジューラー連携のテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from src.config import CocoroCore2Config
from src.core_app import CocoroCore2App


class TestPhase2MemoryIntegration:
    """Phase 2記憶統合テストクラス"""
    
    @pytest.fixture
    def sample_config_phase2(self):
        """Phase 2設定を作成"""
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
                "enable_chat_integration": True,
                "enable_memory_integration": True,
                "text_memory_optimization": {
                    "graceful_degradation": True,
                    "log_scheduler_errors": True
                }
            }
        }
        return CocoroCore2Config(**config_data)
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_add_memory_with_scheduler_integration(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """スケジューラー連携付き記憶追加テスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_add_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # 記憶追加実行
        test_content = "This is a test memory"
        app.add_memory(test_content, "test_user")
        
        # MOS.addが呼ばれたことを確認
        mock_mos.add.assert_called_once()
        add_call_args = mock_mos.add.call_args
        assert add_call_args[1]['memory_content'] == test_content
        assert add_call_args[1]['user_id'] == "test_user"
        
        # スケジューラーに記憶追加メッセージが送信されたことを確認
        app._get_user_memcube.assert_called_once_with("test_user")
        mock_scheduler.submit_add_message.assert_called_once_with(
            user_id="test_user",
            content=test_content,
            mem_cube=mock_cube
        )
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_add_memory_with_context(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """コンテキスト付き記憶追加テスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_add_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # コンテキスト付き記憶追加実行
        test_content = "This is a test memory"
        test_context = {"source": "test", "importance": "high"}
        app.add_memory(test_content, "test_user", **test_context)
        
        # MOS.addに渡された内容を確認（コンテキスト情報を含む）
        add_call_args = mock_mos.add.call_args
        memory_content = add_call_args[1]['memory_content']
        assert test_content in memory_content
        assert "Context:" in memory_content
        assert "source" in memory_content
        assert "importance" in memory_content
        
        # スケジューラーには元のコンテンツのみが送信されることを確認
        mock_scheduler.submit_add_message.assert_called_once_with(
            user_id="test_user",
            content=test_content,  # コンテキスト情報は含まない
            mem_cube=mock_cube
        )
    
    @patch('src.core_app.MOS')
    def test_add_memory_without_scheduler(self, mock_mos_class, sample_config_phase2):
        """スケジューラー無効時の記憶追加テスト"""
        # スケジューラーを無効化
        sample_config_phase2.mem_scheduler.enabled = False
        
        # MOSをモック
        mock_mos = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config_phase2)
        
        # 記憶追加実行
        test_content = "This is a test memory"
        app.add_memory(test_content, "test_user")
        
        # MOS.addが呼ばれたことを確認
        mock_mos.add.assert_called_once()
        
        # スケジューラーが作成されていないことを確認
        assert app.text_memory_scheduler is None
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_add_memory_with_integration_disabled(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """記憶統合無効時の記憶追加テスト"""
        # 記憶統合を無効化
        sample_config_phase2.mem_scheduler.enable_memory_integration = False
        
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_add_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # 記憶追加実行
        test_content = "This is a test memory"
        app.add_memory(test_content, "test_user")
        
        # MOS.addが呼ばれたことを確認
        mock_mos.add.assert_called_once()
        
        # スケジューラーのメソッドが呼ばれていないことを確認
        app._get_user_memcube.assert_not_called()
        mock_scheduler.submit_add_message.assert_not_called()
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_add_memory_with_memcube_not_found(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """MemCubeが見つからない場合の記憶追加テスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_add_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeが見つからない
        app._get_user_memcube = Mock(return_value=None)
        
        # 記憶追加実行
        test_content = "This is a test memory"
        app.add_memory(test_content, "test_user")
        
        # MOS.addが呼ばれたことを確認
        mock_mos.add.assert_called_once()
        
        # スケジューラーのメソッドが呼ばれていないことを確認
        mock_scheduler.submit_add_message.assert_not_called()
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_add_memory_with_scheduler_error(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """スケジューラーエラー時の記憶追加テスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック（エラーを発生させる）
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_add_message = Mock(side_effect=Exception("Scheduler error"))
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # 記憶追加実行（スケジューラーエラーでも正常に動作することを確認）
        test_content = "This is a test memory"
        app.add_memory(test_content, "test_user")
        
        # MOS.addが呼ばれたことを確認
        mock_mos.add.assert_called_once()
        
        # スケジューラーメソッドが呼ばれたことを確認（エラーは処理される）
        mock_scheduler.submit_add_message.assert_called_once()
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_add_memory_with_mos_error(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """MOS記憶追加エラー時のテスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.add = Mock(side_effect=Exception("MOS error"))
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_add_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # 記憶追加実行（例外は発生しない）
        test_content = "This is a test memory"
        app.add_memory(test_content, "test_user")
        
        # MOS.addが呼ばれたことを確認
        mock_mos.add.assert_called_once()
        
        # スケジューラーメソッドが呼ばれていないことを確認（MOSエラーのため）
        app._get_user_memcube.assert_not_called()
        mock_scheduler.submit_add_message.assert_not_called()
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_add_memory_with_default_user(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """デフォルトユーザーでの記憶追加テスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.add = Mock()
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_add_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # 記憶追加実行（user_idを指定しない）
        test_content = "This is a test memory"
        app.add_memory(test_content)
        
        # デフォルトユーザーIDが使用されることを確認
        expected_user_id = app.default_user_id
        
        # MOS.addが呼ばれたことを確認
        add_call_args = mock_mos.add.call_args
        assert add_call_args[1]['user_id'] == expected_user_id
        
        # スケジューラーメソッドが呼ばれたことを確認
        app._get_user_memcube.assert_called_once_with(expected_user_id)
        mock_scheduler.submit_add_message.assert_called_once_with(
            user_id=expected_user_id,
            content=test_content,
            mem_cube=mock_cube
        )
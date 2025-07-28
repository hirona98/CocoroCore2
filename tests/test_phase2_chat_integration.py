"""
Phase 2: チャット処理スケジューラー連携のテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call

from src.config import CocoroCore2Config
from src.core_app import CocoroCore2App


class TestPhase2ChatIntegration:
    """Phase 2チャット統合テストクラス"""
    
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
                "auto_submit_query": True,
                "auto_submit_answer": True,
                "text_memory_optimization": {
                    "graceful_degradation": True,
                    "log_scheduler_errors": True
                }
            }
        }
        return CocoroCore2Config(**config_data)
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_memos_chat_with_scheduler_integration(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """スケジューラー連携付きチャットテスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_query_message = Mock()
        mock_scheduler.submit_answer_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # チャット実行
        response = app.memos_chat("Test query", "test_user")
        
        # 結果確認
        assert response == "Test response"
        
        # クエリメッセージ送信の確認
        assert app._get_user_memcube.call_count == 2  # クエリと応答で2回
        mock_scheduler.submit_query_message.assert_called_once_with(
            user_id="test_user",
            content="Test query",
            mem_cube=mock_cube
        )
        
        # 応答メッセージ送信の確認
        mock_scheduler.submit_answer_message.assert_called_once_with(
            user_id="test_user",
            content="Test response",
            mem_cube=mock_cube
        )
    
    @patch('src.core_app.MOS')
    def test_memos_chat_without_scheduler(self, mock_mos_class, sample_config_phase2):
        """スケジューラー無効時のチャットテスト"""
        # スケジューラーを無効化
        sample_config_phase2.mem_scheduler.enabled = False
        
        # MOSをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config_phase2)
        
        # チャット実行
        response = app.memos_chat("Test query", "test_user")
        
        # 結果確認
        assert response == "Test response"
        assert app.text_memory_scheduler is None  # スケジューラーが作成されていない
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_memos_chat_with_memcube_not_found(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """MemCubeが見つからない場合のチャットテスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_query_message = Mock()
        mock_scheduler.submit_answer_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeが見つからない
        app._get_user_memcube = Mock(return_value=None)
        
        # チャット実行
        response = app.memos_chat("Test query", "test_user")
        
        # 結果確認
        assert response == "Test response"
        
        # スケジューラーのメソッドが呼ばれていないことを確認
        mock_scheduler.submit_query_message.assert_not_called()
        mock_scheduler.submit_answer_message.assert_not_called()
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_memos_chat_with_submit_query_disabled(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """クエリ送信無効時のチャットテスト"""
        # クエリ送信を無効化
        sample_config_phase2.mem_scheduler.auto_submit_query = False
        
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_query_message = Mock()
        mock_scheduler.submit_answer_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # チャット実行
        response = app.memos_chat("Test query", "test_user")
        
        # 結果確認
        assert response == "Test response"
        
        # クエリメッセージが送信されていないことを確認
        mock_scheduler.submit_query_message.assert_not_called()
        
        # 応答メッセージは送信されることを確認
        mock_scheduler.submit_answer_message.assert_called_once()
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_memos_chat_with_submit_answer_disabled(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """応答送信無効時のチャットテスト"""
        # 応答送信を無効化
        sample_config_phase2.mem_scheduler.auto_submit_answer = False
        
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_query_message = Mock()
        mock_scheduler.submit_answer_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # チャット実行
        response = app.memos_chat("Test query", "test_user")
        
        # 結果確認
        assert response == "Test response"
        
        # クエリメッセージは送信されることを確認
        mock_scheduler.submit_query_message.assert_called_once()
        
        # 応答メッセージが送信されていないことを確認
        mock_scheduler.submit_answer_message.assert_not_called()
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_memos_chat_with_system_prompt(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """システムプロンプト付きチャットテスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_query_message = Mock()
        mock_scheduler.submit_answer_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # チャット実行（カスタムシステムプロンプト付き）
        custom_prompt = "You are a helpful assistant."
        response = app.memos_chat("Test query", "test_user", system_prompt=custom_prompt)
        
        # 結果確認
        assert response == "Test response"
        
        # MOSに渡されたクエリを確認（システムプロンプト含む）
        expected_full_query = f"{custom_prompt}\n\nTest query"
        mock_mos.chat.assert_called_once_with(query=expected_full_query, user_id="test_user")
        
        # スケジューラーには元のクエリのみが送信されることを確認
        mock_scheduler.submit_query_message.assert_called_once_with(
            user_id="test_user",
            content="Test query",  # システムプロンプトは含まない
            mem_cube=mock_cube
        )
    
    @patch('src.core_app.MOS')
    @patch('src.core.text_memory_scheduler.TextMemorySchedulerManager')
    def test_memos_chat_with_scheduler_error(self, mock_scheduler_class, mock_mos_class, sample_config_phase2):
        """スケジューラーエラー時のチャットテスト（グレースフルデグラデーション）"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        # スケジューラーをモック（エラーを発生させる）
        mock_scheduler = Mock()
        mock_scheduler.is_running = True
        mock_scheduler.submit_query_message = Mock(side_effect=Exception("Scheduler error"))
        mock_scheduler.submit_answer_message = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        app = CocoroCore2App(sample_config_phase2)
        app.text_memory_scheduler = mock_scheduler
        
        # MemCubeをモック
        mock_cube = Mock()
        app._get_user_memcube = Mock(return_value=mock_cube)
        
        # チャット実行（スケジューラーエラーでも正常に動作することを確認）
        response = app.memos_chat("Test query", "test_user")
        
        # 結果確認
        assert response == "Test response"
        
        # クエリメッセージ送信でエラーが発生
        mock_scheduler.submit_query_message.assert_called_once()
        
        # 応答メッセージは送信される（エラーは独立して処理される）
        mock_scheduler.submit_answer_message.assert_called_once()
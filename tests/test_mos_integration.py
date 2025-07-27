"""
CocoroCore2 MemOS統合テスト

正規版MOS移行後の基本機能確認
"""

import pytest
import sys
import os
from pathlib import Path

# テスト用にsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import CocoroCore2Config, get_mos_config, ConfigurationError


class TestMOSIntegration:
    """MemOS統合テスト"""
    
    def test_config_loading(self):
        """設定ファイル読み込みテスト"""
        # 環境変数にダミーのAPIキーを設定
        os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
        
        try:
            # 設定読み込み
            config = CocoroCore2Config.load()
            
            # 基本フィールドの存在確認
            assert config.mos_config is not None
            assert "chat_model" in config.mos_config
            assert "mem_reader" in config.mos_config
            
            # MOSConfig作成テスト
            mos_config = get_mos_config(config)
            assert mos_config is not None
            
            print("✅ 設定読み込みテスト: 成功")
            
        except Exception as e:
            print(f"❌ 設定読み込みテスト: 失敗 - {e}")
            raise
    
    def test_mos_config_creation(self):
        """MOSConfig作成テスト"""
        # 環境変数にダミーのAPIキーを設定
        os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
        
        try:
            # 設定読み込み
            config = CocoroCore2Config.load()
            
            # MOSConfig作成
            mos_config = get_mos_config(config)
            
            # 必須フィールドの確認
            assert hasattr(mos_config, 'user_id')
            assert hasattr(mos_config, 'chat_model')
            assert hasattr(mos_config, 'mem_reader')
            
            print("✅ MOSConfig作成テスト: 成功")
            
        except Exception as e:
            print(f"❌ MOSConfig作成テスト: 失敗 - {e}")
            raise
    
    @pytest.mark.skipif(
        "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"].startswith("sk-"),
        reason="実際のOpenAI APIキーが必要です"
    )
    def test_core_app_initialization(self):
        """CocoroCore2App初期化テスト（実際のAPIキー必要）"""
        try:
            from core_app import CocoroCore2App
            
            # 設定読み込み
            config = CocoroCore2Config.load()
            
            # アプリケーション初期化
            app = CocoroCore2App(config)
            
            # 基本フィールドの確認
            assert app.mos is not None
            assert app.default_user_id is not None
            assert app.config == config
            
            print("✅ CocoroCore2App初期化テスト: 成功")
            print(f"  - Default User ID: {app.default_user_id}")
            
        except Exception as e:
            print(f"❌ CocoroCore2App初期化テスト: 失敗 - {e}")
            raise
    
    @pytest.mark.skipif(
        "OPENAI_API_KEY" not in os.environ or not os.environ["OPENAI_API_KEY"].startswith("sk-"),
        reason="実際のOpenAI APIキーが必要です"
    )
    async def test_startup_and_user_creation(self):
        """起動とユーザー作成テスト（実際のAPIキー必要）"""
        try:
            from core_app import CocoroCore2App
            
            # 設定読み込み
            config = CocoroCore2Config.load()
            
            # アプリケーション初期化
            app = CocoroCore2App(config)
            
            # 起動処理
            await app.startup()
            
            # 起動状態確認
            assert app.is_running is True
            
            # シャットダウン
            await app.shutdown()
            
            print("✅ 起動とユーザー作成テスト: 成功")
            
        except Exception as e:
            print(f"❌ 起動とユーザー作成テスト: 失敗 - {e}")
            raise
    
    def test_invalid_config(self):
        """不正な設定でのエラーハンドリングテスト"""
        try:
            # 不正な設定辞書
            invalid_config_dict = {
                "mos_config": {
                    "invalid_field": "invalid_value"
                }
            }
            
            # ConfigurationErrorが発生することを確認
            with pytest.raises(ConfigurationError):
                from config import create_mos_config_from_dict
                create_mos_config_from_dict(invalid_config_dict["mos_config"])
            
            print("✅ 不正設定エラーハンドリングテスト: 成功")
            
        except Exception as e:
            print(f"❌ 不正設定エラーハンドリングテスト: 失敗 - {e}")
            raise


if __name__ == "__main__":
    """テストを直接実行する場合"""
    import asyncio
    
    print("=== CocoroCore2 MemOS統合テスト開始 ===\n")
    
    test = TestMOSIntegration()
    
    # 基本テスト実行
    try:
        test.test_config_loading()
        test.test_mos_config_creation()
        test.test_invalid_config()
        print("\n✅ 基本テスト: 全て成功")
    except Exception as e:
        print(f"\n❌ 基本テスト: 失敗 - {e}")
        sys.exit(1)
    
    # APIキーがある場合のみ統合テスト実行
    if "OPENAI_API_KEY" in os.environ and os.environ["OPENAI_API_KEY"].startswith("sk-"):
        try:
            test.test_core_app_initialization()
            asyncio.run(test.test_startup_and_user_creation())
            print("\n✅ 統合テスト: 全て成功")
        except Exception as e:
            print(f"\n❌ 統合テスト: 失敗 - {e}")
            print("注意: 実際のMemOS接続が必要です")
    else:
        print("\n⚠️  統合テスト: スキップ（実際のOpenAI APIキーが必要）")
    
    print("\n=== CocoroCore2 MemOS統合テスト完了 ===")
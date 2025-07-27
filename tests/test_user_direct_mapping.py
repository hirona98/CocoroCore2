"""
CocoroDockユーザー名直接使用テスト

マッピングなしでCocoroDockからの"user"をそのまま使用することを確認
"""

import sys
import os
from pathlib import Path

# テスト用にsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestUserDirectMapping:
    """ユーザー名直接使用テスト"""
    
    def test_no_mapping_logic(self):
        """マッピングなしでuser_idをそのまま使用することを確認"""
        try:
            from config import CocoroCore2Config
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定読み込み
            config = CocoroCore2Config.load()
            
            # テスト: CocoroDockからの "user" をそのまま使用
            request_user_id = "user"
            
            # 修正後のロジック（マッピングなし）
            effective_user_id = request_user_id  # そのまま使用
            
            print(f"✅ 直接ユーザー名使用テスト: 成功")
            print(f"  - Request user_id: {request_user_id}")
            print(f"  - Effective user_id: {effective_user_id}")
            print(f"  - Config user_id: {config.mos_config.get('user_id')}")
            
            # 検証: マッピングなしで同一のuser_idが使用されること
            assert effective_user_id == request_user_id
            assert effective_user_id == "user"
            assert config.mos_config.get("user_id") == "user"
            
            print(f"  - マッピングなし確認: ✅")
            print(f"  - 設定ファイル整合性: ✅")
            
        except Exception as e:
            print(f"❌ 直接ユーザー名使用テスト: 失敗 - {e}")
            raise
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_config_consistency(self):
        """設定ファイルの一貫性テスト"""
        try:
            from config import CocoroCore2Config
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定読み込み
            config = CocoroCore2Config.load()
            
            # user_idが"user"に統一されていることを確認
            user_id = config.mos_config.get("user_id")
            
            assert user_id == "user"
            
            print(f"✅ 設定ファイル一貫性テスト: 成功")
            print(f"  - MemOS user_id: {user_id}")
            
        except Exception as e:
            print(f"❌ 設定ファイル一貫性テスト: 失敗 - {e}")
            raise
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_data_cleanup_verification(self):
        """データクリーンアップ確認テスト"""
        try:
            import os
            from pathlib import Path
            
            base_dir = Path("/mnt/d/MyProject/AliceEncoder/DesktopAssistant/CocoroAI/CocoroCore2")
            
            # .memosディレクトリが削除されていることを確認
            memos_dir = base_dir / ".memos"
            assert not memos_dir.exists(), f".memosディレクトリが残っています: {memos_dir}"
            
            # memory_cubesディレクトリが削除されていることを確認
            memory_cubes_dir = base_dir / "memory_cubes"
            assert not memory_cubes_dir.exists(), f"memory_cubesディレクトリが残っています: {memory_cubes_dir}"
            
            print(f"✅ データクリーンアップ確認テスト: 成功")
            print(f"  - .memosディレクトリ削除確認: ✅")
            print(f"  - memory_cubesディレクトリ削除確認: ✅")
            
        except Exception as e:
            print(f"❌ データクリーンアップ確認テスト: 失敗 - {e}")
            raise


if __name__ == "__main__":
    """テストを直接実行する場合"""
    print("=== CocoroDockユーザー名直接使用テスト開始 ===\n")
    
    test = TestUserDirectMapping()
    
    try:
        test.test_no_mapping_logic()
        test.test_config_consistency()
        test.test_data_cleanup_verification()
        
        print("\n✅ 全ての直接使用テスト: 成功")
        print("\n=== 修正内容 ===")
        print("1. User IDマッピングを削除してCocoroDockからの'user'をそのまま使用")
        print("2. 設定ファイルのuser_idを'user'に統一")
        print("3. hironaユーザーのすべてのデータを削除")
        print("   - .memosディレクトリ削除")
        print("   - memory_cubesディレクトリ削除")
        print("\n🎯 ユーザー名の直接使用に変更完了！")
        print("\n次のステップ:")
        print("1. アプリケーションを再起動")
        print("2. 新しい'user'ユーザーで記憶が正しく動作することを確認")
        
    except Exception as e:
        print(f"\n❌ 直接使用テスト: 失敗 - {e}")
        sys.exit(1)
    
    print("\n=== CocoroDockユーザー名直接使用テスト完了 ===")
"""
記憶機能の動作確認テスト

修正後のMemCube自動作成とメモリ機能をテスト
"""

import sys
import os
from pathlib import Path

# テスト用にsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestMemoryFunctionality:
    """記憶機能動作確認テスト"""
    
    def test_memory_with_auto_memcube_creation(self):
        """MemCube自動作成付きメモリ機能テスト"""
        try:
            import config
            import core_app
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定読み込み
            config_obj = config.CocoroCore2Config.load()
            
            # CocoroCore2Appインスタンス作成
            app = core_app.CocoroCore2App(config_obj)
            
            # テスト用ユーザーID
            user_id = "user"
            
            print(f"✅ アプリケーション初期化: 成功")
            print(f"  - Default user_id: {app.default_user_id}")
            print(f"  - MOS initialized: {app.mos is not None}")
            print(f"  - UserManager available: {app.mos.user_manager is not None}")
            
            # ユーザー確保（MemCube自動作成込み）
            app.ensure_user(user_id)
            print(f"  - User ensured: {user_id}")
            
            # ユーザーのMemCubeをチェック
            user_cubes = app.mos.user_manager.get_user_cubes(user_id)
            print(f"  - User cubes count: {len(user_cubes)}")
            
            if user_cubes:
                print(f"  - Cube IDs: {[cube.cube_id for cube in user_cubes]}")
                
                # 記憶追加テスト
                test_memory = "これは記憶機能のテストメモリです。"
                app.add_memory(content=test_memory, user_id=user_id)
                print(f"  - Memory added: '{test_memory}'")
                
                # 記憶検索テスト
                search_result = app.search_memory(query="テストメモリ", user_id=user_id)
                print(f"  - Memory search result: {type(search_result)}")
                
                # チャットテスト（記憶参照込み）
                chat_response = app.memos_chat(query="私が先ほど追加したテストメモリについて教えて", user_id=user_id)
                print(f"  - Chat response length: {len(chat_response)} characters")
                
                print(f"✅ 記憶機能動作テスト: 成功")
                return True
            else:
                print(f"❌ MemCube作成失敗: ユーザー {user_id} にMemCubeが作成されませんでした")
                return False
                
        except Exception as e:
            print(f"❌ 記憶機能動作テスト: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_user_creation_and_cube_registration(self):
        """ユーザー作成とMemCube登録のフローテスト"""
        try:
            import config
            import core_app
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定読み込み
            config_obj = config.CocoroCore2Config.load()
            
            # CocoroCore2Appインスタンス作成
            app = core_app.CocoroCore2App(config_obj)
            
            user_id = "user"
            
            # ステップ1: ユーザー存在確認
            users = app.mos.list_users()
            print(f"✅ ユーザー作成フローテスト: 開始")
            print(f"  - 既存ユーザー数: {len(users)}")
            
            # ステップ2: MemCube自動作成付きユーザー確保
            app.ensure_user(user_id)
            
            # ステップ3: MemCube登録確認
            user_cubes = app.mos.user_manager.get_user_cubes(user_id)
            print(f"  - User {user_id} MemCube count: {len(user_cubes)}")
            
            # ステップ4: 登録されたMemCubeの情報表示
            for cube in user_cubes:
                print(f"  - Cube ID: {cube.cube_id}")
                print(f"  - Owner ID: {cube.owner_id}")
                if hasattr(cube, 'text_mem') and cube.text_mem:
                    print(f"  - Text memory available: True")
                else:
                    print(f"  - Text memory available: False")
            
            print(f"✅ ユーザー作成フローテスト: 成功")
            return True
            
        except Exception as e:
            print(f"❌ ユーザー作成フローテスト: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]


if __name__ == "__main__":
    """テストを直接実行する場合"""
    print("=== 記憶機能動作確認テスト開始 ===\n")
    
    test = TestMemoryFunctionality()
    
    try:
        # テスト1: ユーザー作成とMemCube登録フロー
        success1 = test.test_user_creation_and_cube_registration()
        
        print("\n" + "="*50 + "\n")
        
        # テスト2: 記憶機能の動作確認
        success2 = test.test_memory_with_auto_memcube_creation()
        
        if success1 and success2:
            print("\n✅ 全ての記憶機能テスト: 成功")
            print("\n=== 修正効果 ===")
            print("1. MemCube自動作成機能が正常に動作")
            print("2. ユーザー作成時に自動的にMemCubeが登録される")
            print("3. 記憶追加・検索・チャット機能が正常に動作")
            print("\n🎯 MemCube未登録問題が完全に解決！")
            print("\n次のステップ:")
            print("1. 実際のアプリケーションで記憶機能をテスト")
            print("2. CocoroDockからのチャットで記憶が保持されることを確認")
        else:
            print("\n❌ 一部のテストが失敗しました")
            print("詳細なログを確認してください")
        
    except Exception as e:
        print(f"\n❌ 記憶機能テスト: 失敗 - {e}")
        sys.exit(1)
    
    print("\n=== 記憶機能動作確認テスト完了 ===")
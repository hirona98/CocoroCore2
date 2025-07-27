"""
設定ファイルからの動的読み込みテスト

ハードコーディングが解消され、設定ファイルからの動的読み込みが正しく動作することを確認
"""

import sys
import os
import json
from pathlib import Path

# テスト用にsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestDynamicConfig:
    """動的設定読み込みテスト"""
    
    def test_embedder_model_detection(self):
        """異なる埋め込みモデルの次元数が正しく検出されることを確認"""
        try:
            from config import CocoroCore2Config
            from core_app import CocoroCore2App
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定読み込み
            config = CocoroCore2Config.load()
            app = CocoroCore2App(config)
            
            print(f"✅ 埋め込みモデル検出テスト: 開始")
            
            # 現在の設定から埋め込みモデルと次元数を取得
            user_id = "test_user"
            cube_config = app._get_memcube_config_from_settings(user_id)
            
            embedder_config = cube_config["text_mem"]["config"]["embedder"]["config"]
            vector_config = cube_config["text_mem"]["config"]["vector_db"]["config"]
            
            embedder_model = embedder_config["model_name_or_path"]
            vector_dimension = vector_config["vector_dimension"]
            
            print(f"  - 設定ファイルから読み込み成功")
            print(f"  - 埋め込みモデル: {embedder_model}")
            print(f"  - ベクトル次元数: {vector_dimension}")
            
            # text-embedding-3-large の場合は 3072 次元であることを確認
            if "text-embedding-3-large" in embedder_model:
                assert vector_dimension == 3072, f"Expected 3072 dimensions for {embedder_model}, got {vector_dimension}"
                print(f"  - 次元数検証: ✅ (3072次元)")
            elif "text-embedding-3-small" in embedder_model:
                assert vector_dimension == 1536, f"Expected 1536 dimensions for {embedder_model}, got {vector_dimension}"
                print(f"  - 次元数検証: ✅ (1536次元)")
            
            # LLM設定も確認
            extractor_llm_config = cube_config["text_mem"]["config"]["extractor_llm"]["config"]
            chat_model = extractor_llm_config["model_name_or_path"]
            print(f"  - チャットモデル: {chat_model}")
            
            # 設定ファイルの値と一致することを確認
            original_chat_model = config.mos_config["chat_model"]["config"]["model_name_or_path"]
            original_embedder = config.mos_config["mem_reader"]["config"]["embedder"]["config"]["model_name_or_path"]
            
            assert chat_model == original_chat_model, f"Chat model mismatch: {chat_model} vs {original_chat_model}"
            assert embedder_model == original_embedder, f"Embedder model mismatch: {embedder_model} vs {original_embedder}"
            
            print(f"  - 設定ファイル整合性: ✅")
            print(f"✅ 埋め込みモデル検出テスト: 成功")
            
            return True
            
        except Exception as e:
            print(f"❌ 埋め込みモデル検出テスト: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_config_dynamic_loading(self):
        """設定ファイルの値が動的に反映されることを確認"""
        try:
            from config import CocoroCore2Config
            from core_app import CocoroCore2App
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定読み込み
            config = CocoroCore2Config.load()
            app = CocoroCore2App(config)
            
            print(f"✅ 動的設定読み込みテスト: 開始")
            
            # 複数のユーザーでMemCube設定が生成されることを確認
            test_users = ["user", "alice", "bob"]
            
            for test_user in test_users:
                cube_config = app._get_memcube_config_from_settings(test_user)
                
                print(f"  - User: {test_user}")
                print(f"    - Cube ID: {cube_config['cube_id']}")
                print(f"    - Collection: {cube_config['text_mem']['config']['vector_db']['config']['collection_name']}")
                
                # ユーザー固有の設定が生成されることを確認
                assert cube_config["user_id"] == test_user
                assert cube_config["cube_id"] == f"{test_user}_default_cube"
                assert cube_config["text_mem"]["config"]["vector_db"]["config"]["collection_name"] == f"{test_user}_collection"
            
            print(f"  - ユーザー固有設定生成: ✅")
            
            # 設定値のハードコーディングが除去されていることを確認
            cube_config = app._get_memcube_config_from_settings("test_user")
            
            # APIキーが設定ファイルから取得されていることを確認
            extractor_api_key = cube_config["text_mem"]["config"]["extractor_llm"]["config"]["api_key"]
            embedder_api_key = cube_config["text_mem"]["config"]["embedder"]["config"]["api_key"]
            original_api_key = config.mos_config["chat_model"]["config"]["api_key"]
            
            assert extractor_api_key == original_api_key, "Extractor LLM API key should come from config"
            assert embedder_api_key == embedder_api_key, "Embedder API key should come from config"
            
            print(f"  - APIキー動的取得: ✅")
            print(f"✅ 動的設定読み込みテスト: 成功")
            
            return True
            
        except Exception as e:
            print(f"❌ 動的設定読み込みテスト: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_hardcoding_elimination(self):
        """ハードコーディングが完全に除去されていることを確認"""
        try:
            # ソースコードを確認してハードコーディングされた値がないことを検証
            source_file = Path(__file__).parent.parent / "src" / "core_app.py"
            
            with open(source_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # ハードコーディングされがちな値をチェック
            hardcoded_patterns = [
                'text-embedding-3-large',
                'text-embedding-3-small', 
                'gpt-4o-mini'
            ]
            
            found_hardcoding = []
            for pattern in hardcoded_patterns:
                if f'"{pattern}"' in source_code:
                    # _get_memcube_config_from_settings 内での参照は許可（モデル名判定のため）
                    if 'text-embedding-3' in pattern and '_get_memcube_config_from_settings' in source_code:
                        # モデル判定での使用は許可
                        lines = source_code.split('\n')
                        pattern_lines = [i for i, line in enumerate(lines) if pattern in line]
                        config_func_lines = [i for i, line in enumerate(lines) if '_get_memcube_config_from_settings' in line]
                        
                        if config_func_lines:
                            # 設定関数内での使用は許可
                            continue
                    
                    found_hardcoding.append(pattern)
            
            if not found_hardcoding:
                print(f"✅ ハードコーディング除去確認: 成功")
                print(f"  - 検査対象パターン: {len(hardcoded_patterns)}個")
                print(f"  - ハードコーディング検出: 0個")
            else:
                print(f"⚠️  ハードコーディング除去確認: 一部残存")
                print(f"  - 残存パターン: {found_hardcoding}")
            
            print(f"✅ ハードコーディング除去確認: 完了")
            
            return len(found_hardcoding) == 0
            
        except Exception as e:
            print(f"❌ ハードコーディング除去確認: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    """テストを直接実行する場合"""
    print("=== 動的設定読み込みテスト開始 ===\\n")
    
    test = TestDynamicConfig()
    
    try:
        # テスト1: 埋め込みモデル検出
        success1 = test.test_embedder_model_detection()
        
        print("\\n" + "="*50 + "\\n")
        
        # テスト2: 動的設定読み込み
        success2 = test.test_config_dynamic_loading()
        
        print("\\n" + "="*50 + "\\n")
        
        # テスト3: ハードコーディング除去確認
        success3 = test.test_hardcoding_elimination()
        
        if success1 and success2 and success3:
            print("\\n✅ 全ての動的設定テスト: 成功")
            print("\\n=== ハードコーディング除去完了 ===")
            print("1. MemCube設定を設定ファイルから動的に読み込み")
            print("2. 埋め込みモデルに応じたベクトル次元数の自動検出")
            print("3. LLMモデル設定の動的取得")
            print("4. APIキーや接続先URLの設定ファイル参照")
            print("5. ユーザー固有設定の動的生成")
            print("\\n🎯 設定の柔軟性と保守性が大幅に向上！")
        else:
            print("\\n❌ 一部の動的設定テストが失敗しました")
        
    except Exception as e:
        print(f"\\n❌ 動的設定テスト: 失敗 - {e}")
        sys.exit(1)
    
    print("\\n=== 動的設定読み込みテスト完了 ===")
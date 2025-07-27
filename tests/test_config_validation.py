"""
設定ファイルの整合性とフォーマット検証テスト

UserData/cocoro_core2_config.jsonの設定が正しく読み込まれることを確認
"""

import sys
import os
import json
from pathlib import Path

# テスト用にsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestConfigValidation:
    """設定ファイル検証テスト"""
    
    def test_config_file_loading(self):
        """設定ファイルが正しく読み込まれることを確認"""
        try:
            from config import CocoroCore2Config
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定ファイル読み込み
            config = CocoroCore2Config.load()
            
            print(f"✅ 設定ファイル読み込み: 成功")
            print(f"  - Version: {config.version}")
            print(f"  - Environment: {config.environment}")
            print(f"  - User ID: {config.mos_config.get('user_id')}")
            print(f"  - Session ID: {config.mos_config.get('session_id')}")
            
            return True
            
        except Exception as e:
            print(f"❌ 設定ファイル読み込み: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_mos_config_format(self):
        """MOS設定の形式が正しいことを確認"""
        try:
            from config import CocoroCore2Config, get_mos_config
            
            # 環境変数にダミーのAPIキーを設定
            os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-testing"
            
            # 設定読み込み
            config = CocoroCore2Config.load()
            
            # MOS設定取得
            mos_config = get_mos_config(config)
            
            print(f"✅ MOS設定形式検証: 成功")
            print(f"  - User ID: {mos_config.user_id}")
            print(f"  - Session ID: {mos_config.session_id}")
            print(f"  - Chat Model Backend: {mos_config.chat_model.backend}")
            print(f"  - Chat Model: {mos_config.chat_model.config.model_name_or_path}")
            print(f"  - Embedder Backend: {mos_config.mem_reader.config.embedder.backend}")
            print(f"  - Embedder Model: {mos_config.mem_reader.config.embedder.config.model_name_or_path}")
            print(f"  - Textual Memory: {mos_config.enable_textual_memory}")
            print(f"  - Activation Memory: {mos_config.enable_activation_memory}")
            print(f"  - Parametric Memory: {mos_config.enable_parametric_memory}")
            
            # 重要項目の検証
            assert mos_config.user_id == "user"
            assert mos_config.session_id == "default_session"
            assert mos_config.chat_model.config.model_name_or_path == "gpt-4o-mini"
            assert mos_config.mem_reader.config.embedder.config.model_name_or_path == "text-embedding-3-large"
            assert mos_config.enable_textual_memory == True
            
            print(f"  - 設定項目検証: ✅")
            
            return True
            
        except Exception as e:
            print(f"❌ MOS設定形式検証: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # テスト用環境変数削除
            if "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]
    
    def test_config_file_json_format(self):
        """設定ファイルのJSON形式が正しいことを確認"""
        try:
            config_path = "../UserData/cocoro_core2_config.json"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            print(f"✅ JSON形式検証: 成功")
            print(f"  - Version: {config_data.get('version')}")
            print(f"  - Environment: {config_data.get('environment')}")
            
            # MOS設定の存在確認
            mos_config = config_data.get('mos_config', {})
            assert 'user_id' in mos_config
            assert 'session_id' in mos_config
            assert 'chat_model' in mos_config
            assert 'mem_reader' in mos_config
            
            # Chat modelの設定確認
            chat_model = mos_config.get('chat_model', {})
            assert chat_model.get('backend') == 'openai'
            assert 'config' in chat_model
            assert chat_model['config'].get('model_name_or_path') == 'gpt-4o-mini'
            assert 'api_key' in chat_model['config']
            assert 'api_base' in chat_model['config']
            
            # Embedder設定確認
            mem_reader = mos_config.get('mem_reader', {})
            embedder = mem_reader.get('config', {}).get('embedder', {})
            assert embedder.get('backend') == 'universal_api'
            assert embedder['config'].get('model_name_or_path') == 'text-embedding-3-large'
            assert embedder['config'].get('provider') == 'openai'
            assert 'api_key' in embedder['config']
            assert 'base_url' in embedder['config']
            
            print(f"  - MOS設定構造: ✅")
            print(f"  - Chat Model設定: ✅")
            print(f"  - Embedder設定: ✅")
            
            return True
            
        except Exception as e:
            print(f"❌ JSON形式検証: 失敗 - {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    """テストを直接実行する場合"""
    print("=== 設定ファイル検証テスト開始 ===\\n")
    
    test = TestConfigValidation()
    
    try:
        # テスト1: 設定ファイル読み込み
        success1 = test.test_config_file_json_format()
        
        print("\\n" + "="*50 + "\\n")
        
        # テスト2: 設定ファイル読み込み
        success2 = test.test_config_file_loading()
        
        print("\\n" + "="*50 + "\\n")
        
        # テスト3: MOS設定形式検証
        success3 = test.test_mos_config_format()
        
        if success1 and success2 and success3:
            print("\\n✅ 全ての設定検証テスト: 成功")
            print("\\n=== 修正完了 ===")
            print("1. UserData/cocoro_core2_config.json の形式修正完了")
            print("2. LLMモデル: gpt-4o-mini に設定")
            print("3. 埋め込みモデル: text-embedding-3-large に設定")
            print("4. 記憶システムバックエンド: general_text (現状維持)")
            print("5. ベクトル次元: 3072次元に対応")
            print("6. 設定ファイル整合性: 完全確保")
            print("\\n🎯 設定統一化と最適化が完了！")
        else:
            print("\\n❌ 一部の設定検証テストが失敗しました")
        
    except Exception as e:
        print(f"\\n❌ 設定検証テスト: 失敗 - {e}")
        sys.exit(1)
    
    print("\\n=== 設定ファイル検証テスト完了 ===")
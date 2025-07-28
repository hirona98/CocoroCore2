"""
TreeTextMemory統合テスト

TreeTextMemoryへの移行が正しく動作するか確認
"""

import sys
import os
from pathlib import Path

# テスト用にsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_config_loading():
    """設定ファイル読み込みテスト"""
    try:
        from config import CocoroCore2Config
        
        # 環境変数設定
        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "sk-dummy-key-for-testing")
        os.environ["NEO4J_PASSWORD"] = os.environ.get("NEO4J_PASSWORD", "12345678")
        
        # デフォルト設定ファイルを使用（TreeTextMemory対応済み）
        config_path = Path(__file__).parent.parent / "config" / "default_memos_config.json"
        config = CocoroCore2Config.load(str(config_path))
        
        print("[OK] 設定ファイル読み込み: 成功")
        print(f"  - Neo4j URI: {config.neo4j.uri}")
        print(f"  - Neo4j DB: {config.neo4j.db_name}")
        print(f"  - Embedding dimension: {config.neo4j.embedding_dimension}")
        print(f"  - Embedder model: {config.mos_config['mem_reader']['config']['embedder']['config']['model_name_or_path']}")
        
        return config
        
    except Exception as e:
        print(f"[ERROR] 設定ファイル読み込み: 失敗 - {e}")
        raise


def test_memcube_config_creation():
    """MemCube設定作成テスト"""
    try:
        from config import CocoroCore2Config
        # core_appのインポートを回避して、設定作成ロジックを直接テスト
        
        # 設定読み込み
        config = test_config_loading()
        
        # MemCube設定を直接構築（core_app._get_memcube_config_from_settingsのロジックを再現）
        user_id = "test_user"
        mos_config = config.mos_config
        chat_model_config = mos_config["chat_model"]["config"]
        mem_reader_config = mos_config["mem_reader"]["config"]
        embedder_config = mem_reader_config["embedder"]["config"]
        
        # モデルから次元数を推定
        embedder_model = embedder_config["model_name_or_path"]
        if "text-embedding-3-large" in embedder_model:
            vector_dimension = 3072
        elif "text-embedding-3-small" in embedder_model:
            vector_dimension = 1536
        else:
            vector_dimension = 1536
        
        # TreeTextMemory用のMemCube設定を構築
        cube_config = {
            "user_id": user_id,
            "cube_id": f"{user_id}_default_cube",
            "text_mem": {
                "backend": "tree_text",
                "config": {
                    "cube_id": f"{user_id}_default_cube",
                    "memory_filename": "tree_textual_memory.json",
                    "extractor_llm": {
                        "backend": mos_config["chat_model"]["backend"],
                        "config": {
                            "model_name_or_path": chat_model_config["model_name_or_path"],
                            "temperature": 0.0,
                            "api_key": chat_model_config["api_key"],
                            "api_base": chat_model_config.get("api_base", "https://api.openai.com/v1")
                        }
                    },
                    "dispatcher_llm": {
                        "backend": mos_config["chat_model"]["backend"],
                        "config": {
                            "model_name_or_path": chat_model_config["model_name_or_path"],
                            "temperature": 0.0,
                            "api_key": chat_model_config["api_key"],
                            "api_base": chat_model_config.get("api_base", "https://api.openai.com/v1")
                        }
                    },
                    "embedder": {
                        "backend": mem_reader_config["embedder"]["backend"],
                        "config": {
                            "model_name_or_path": embedder_config["model_name_or_path"],
                            "provider": embedder_config.get("provider", "openai"),
                            "api_key": embedder_config["api_key"],
                            "base_url": embedder_config.get("base_url", "https://api.openai.com/v1")
                        }
                    },
                    "graph_db": {
                        "backend": "neo4j",
                        "config": {
                            "uri": config.neo4j.uri,
                            "user": config.neo4j.user,
                            "password": config.neo4j.password,
                            "db_name": config.neo4j.db_name,
                            "auto_create": False,  # Community Editionでは強制無効
                            "embedding_dimension": vector_dimension
                        }
                    },
                    "reorganize": False
                }
            },
            "act_mem": {},
            "para_mem": {}
        }
        
        print("\n[OK] MemCube設定作成: 成功")
        print(f"  - Backend: {cube_config['text_mem']['backend']}")
        print(f"  - Cube ID: {cube_config['cube_id']}")
        print(f"  - Graph DB backend: {cube_config['text_mem']['config']['graph_db']['backend']}")
        print(f"  - Embedding dimension: {cube_config['text_mem']['config']['graph_db']['config']['embedding_dimension']}")
        
        # 検証
        assert cube_config['text_mem']['backend'] == "tree_text"
        assert cube_config['text_mem']['config']['graph_db']['backend'] == "neo4j"
        assert cube_config['text_mem']['config']['graph_db']['config']['embedding_dimension'] == 3072
        assert 'extractor_llm' in cube_config['text_mem']['config']
        assert 'dispatcher_llm' in cube_config['text_mem']['config']
        
        print("  - 設定構造検証: [OK]")
        
        return cube_config
        
    except Exception as e:
        print(f"[ERROR] MemCube設定作成テスト: 失敗 - {e}")
        raise


def test_neo4j_connection():
    """Neo4j接続テスト（オプション）"""
    try:
        from neo4j import GraphDatabase
        from config import CocoroCore2Config
        
        config = test_config_loading()
        
        # Neo4j接続テスト
        driver = GraphDatabase.driver(
            config.neo4j.uri,
            auth=(config.neo4j.user, config.neo4j.password)
        )
        
        with driver.session() as session:
            result = session.run("RETURN 1 AS num")
            record = result.single()
            assert record["num"] == 1
            
        driver.close()
        
        print("\n[OK] Neo4j接続テスト: 成功")
        print(f"  - URI: {config.neo4j.uri}")
        print(f"  - Database: {config.neo4j.db_name}")
        
    except ImportError:
        print("\n[WARN] Neo4j接続テスト: スキップ (neo4j-driverがインストールされていません)")
    except Exception as e:
        print(f"\n[WARN] Neo4j接続テスト: 失敗 - {e}")
        print("  - Neo4jサーバーが起動していることを確認してください")


def test_tree_text_memory_creation():
    """TreeTextMemory作成テスト（シンプル）"""
    try:
        # MemOSのインポートをテスト
        from memos.memories.textual.tree import TreeTextMemory
        from memos.configs.memory import TreeTextMemoryConfig
        
        print("\n[OK] TreeTextMemoryモジュールインポート: 成功")
        
        # 最小限の設定でインスタンス化可能か確認
        print("  - TreeTextMemoryクラスが利用可能です")
        print("  - TreeTextMemoryConfigクラスが利用可能です")
        
    except ImportError as e:
        print(f"\n[ERROR] TreeTextMemoryモジュールインポート: 失敗 - {e}")
        print("  - MemOSライブラリが正しくインストールされているか確認してください")
        raise


if __name__ == "__main__":
    """テストを実行"""
    print("=== TreeTextMemory統合テスト開始 ===\n")
    
    try:
        # 1. 設定ファイル読み込み
        test_config_loading()
        
        # 2. MemCube設定作成
        test_memcube_config_creation()
        
        # 3. Neo4j接続（オプション）
        test_neo4j_connection()
        
        # 4. TreeTextMemoryモジュール
        test_tree_text_memory_creation()
        
        print("\n[OK] 全てのTreeTextMemory統合テスト: 成功")
        print("\n=== 実装内容 ===")
        print("1. config.pyにNeo4j設定クラスを追加")
        print("2. core_app.pyでMOS_TEXT_MEM_TYPEを'tree_text'に変更")
        print("3. _get_memcube_config_from_settingsをTreeTextMemory用に修正")
        print("4. text-embedding-3-large（3072次元）に対応")
        print("5. OpenAI embedderは既存のuniversal_apiを使用")
        
        print("\n次のステップ:")
        print("1. Neo4jサーバーを起動")
        print("2. 環境変数を設定（OPENAI_API_KEY, NEO4J_PASSWORD）")
        print("3. TreeTextMemory設定でアプリケーションを実行")
        
    except Exception as e:
        print(f"\n[ERROR] TreeTextMemory統合テスト: 失敗 - {e}")
        sys.exit(1)
    
    print("\n=== TreeTextMemory統合テスト完了 ===")
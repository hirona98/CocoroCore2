"""
Neo4j組み込みサービス管理

PyInstaller実行ファイル内でNeo4jを自動起動・管理するためのモジュール
"""

import os
import sys
import time
import socket
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio

try:
    from neo4j import GraphDatabase
    NEO4J_DRIVER_AVAILABLE = True
except ImportError:
    NEO4J_DRIVER_AVAILABLE = False
    GraphDatabase = None


logger = logging.getLogger(__name__)


class Neo4jManager:
    """組み込みNeo4jサービス管理クラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Neo4j設定辞書
                - uri: Neo4j接続URI
                - user: ユーザー名
                - password: パスワード
                - db_name: データベース名
                - embedded_enabled: 組み込みモード有効
                - java_home: JREホームディレクトリ（相対パス）
                - neo4j_home: Neo4jホームディレクトリ（相対パス）
                - startup_timeout: 起動タイムアウト（秒）
        """
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.driver = None
        self.shutdown_event = threading.Event()
        
        # パス設定
        if getattr(sys, 'frozen', False):
            # PyInstaller実行時
            self.base_dir = Path(sys.executable).parent
        else:
            # 開発時
            self.base_dir = Path(__file__).parent.parent.parent
            
        self.java_home = self.base_dir / config.get("java_home", "jre")
        self.neo4j_home = self.base_dir / config.get("neo4j_home", "neo4j")
        
        # 接続設定（IPv4固定）
        original_uri = config.get("uri", "bolt://localhost:7687")
        self.uri = original_uri.replace("localhost", "127.0.0.1")  # IPv4に固定
        self.user = config.get("user", "neo4j")
        self.password = config.get("password", "neo4j")
        self.db_name = config.get("db_name", "neo4j")
        self.startup_timeout = config.get("startup_timeout", 60)
        
        # 組み込みモード設定
        self.embedded_enabled = config.get("embedded_enabled", True)
        
    async def start(self) -> bool:
        """Neo4jサービスを起動
        
        Returns:
            bool: 起動成功時True
        """
        if not self.embedded_enabled:
            logger.info("組み込みNeo4jは無効です。外部Neo4jに接続します。")
            return await self._test_connection()
            
        logger.info("組み込みNeo4jサービスを起動中...")
        
        try:
            # 1. 環境設定
            if not self._setup_environment():
                return False
            
            # 2. ポート確認
            if not self._check_port_available():
                logger.warning("Neo4jポートは既に使用中です。既存のインスタンスに接続を試行します。")
                return await self._test_connection()
            
            # 3. Neo4jプロセス起動
            if not await self._start_neo4j_process():
                return False
            
            # 4. 起動待機とヘルスチェック
            if not await self._wait_for_startup():
                await self._stop_process()
                return False
            
            logger.info("組み込みNeo4jサービスの起動が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"Neo4jサービス起動エラー: {e}")
            await self._stop_process()
            return False
    
    async def stop(self):
        """Neo4jサービスを停止"""
        logger.info("Neo4jサービスを停止中...")
        
        self.shutdown_event.set()
        
        # ドライバー切断
        if self.driver:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self.driver.close
                )
                self.driver = None
                logger.info("Neo4jドライバーを切断しました")
            except Exception as e:
                logger.warning(f"ドライバー切断エラー: {e}")
        
        # プロセス停止
        await self._stop_process()
        
        logger.info("Neo4jサービスの停止が完了しました")
    
    async def get_driver(self):
        """Neo4jドライバーを取得
        
        Returns:
            neo4j.GraphDatabase.driver: Neo4jドライバー
        """
        if not NEO4J_DRIVER_AVAILABLE:
            raise ImportError("neo4j-driver not available")
            
        if not self.driver:
            try:
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=None  # 認証無効化（neo4j.confと一致）
                )
                # 接続テスト
                await asyncio.get_event_loop().run_in_executor(
                    None, self.driver.verify_connectivity
                )
            except Exception as e:
                logger.error(f"Neo4jドライバー作成エラー: {e}")
                raise
                
        return self.driver
    
    async def health_check(self) -> bool:
        """ヘルスチェック
        
        Returns:
            bool: 正常時True
        """
        try:
            if not NEO4J_DRIVER_AVAILABLE:
                return False
                
            driver = await self.get_driver()
            
            def _run_query():
                with driver.session() as session:
                    result = session.run("RETURN 1 AS num")
                    record = result.single()
                    return record["num"] == 1
            
            return await asyncio.get_event_loop().run_in_executor(
                None, _run_query
            )
            
        except Exception as e:
            logger.warning(f"Neo4jヘルスチェック失敗: {e}")
            return False
    
    def _setup_environment(self) -> bool:
        """JRE環境を設定
        
        Returns:
            bool: 設定成功時True
        """
        try:
            # JREディレクトリ確認
            if not self.java_home.exists():
                logger.error(f"JREディレクトリが見つかりません: {self.java_home}")
                return False
                
            # Neo4jディレクトリ確認
            if not self.neo4j_home.exists():
                logger.error(f"Neo4jディレクトリが見つかりません: {self.neo4j_home}")
                return False
            
            # JAVA_HOME設定
            os.environ["JAVA_HOME"] = str(self.java_home)
            os.environ["PATH"] = str(self.java_home / "bin") + os.pathsep + os.environ.get("PATH", "")
            
            # Neo4j設定
            os.environ["NEO4J_HOME"] = str(self.neo4j_home)
            
            logger.info(f"Java環境を設定: JAVA_HOME={self.java_home}")
            logger.info(f"Neo4j環境を設定: NEO4J_HOME={self.neo4j_home}")
            
            return True
            
        except Exception as e:
            logger.error(f"環境設定エラー: {e}")
            return False
    
    def _check_port_available(self) -> bool:
        """Neo4jポートの可用性確認
        
        Returns:
            bool: ポートが利用可能時True
        """
        try:
            # URIからポート番号を抽出
            port = 7687  # デフォルト
            if ":" in self.uri:
                port_str = self.uri.split(":")[-1]
                if "/" in port_str:
                    port_str = port_str.split("/")[0]
                port = int(port_str)
            
            # ポート確認
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0  # 接続失敗 = ポート利用可能
                
        except Exception as e:
            logger.warning(f"ポート確認エラー: {e}")
            return True  # エラー時は起動を試行
    
    async def _start_neo4j_process(self) -> bool:
        """Neo4jをconsoleモードで起動
        
        Returns:
            bool: 起動成功時True
        """
        try:
            # Neo4jスクリプト確認（Windows専用）
            neo4j_cmd = self.neo4j_home / "bin" / "neo4j.bat"
                
            if not neo4j_cmd.exists():
                logger.error(f"Neo4jスクリプトが見つかりません: {neo4j_cmd}")
                return False
            
            # Neo4j console起動
            console_cmd = [str(neo4j_cmd), "console"]
            logger.info(f"Neo4j console起動: {' '.join(console_cmd)}")
            
            env = os.environ.copy()
            
            self.process = subprocess.Popen(
                console_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(self.neo4j_home),
                env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            logger.info(f"Neo4j console起動: PID={self.process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Neo4j console起動エラー: {e}")
            return False
    
    async def _wait_for_startup(self) -> bool:
        """Neo4j起動完了を待機
        
        Returns:
            bool: 起動完了時True
        """
        logger.info(f"Neo4j起動完了を待機中（最大{self.startup_timeout}秒）...")
        
        start_time = time.time()
        
        while time.time() - start_time < self.startup_timeout:
            if self.shutdown_event.is_set():
                logger.info("シャットダウン要求により起動待機を中止")
                return False
            
            # プロセス生存確認
            if self.process and self.process.poll() is not None:
                return_code = self.process.returncode
                logger.error(f"Neo4jプロセスが予期せず終了しました (exit code: {return_code})")
                return False
            
            # 接続テスト
            if await self._test_connection():
                elapsed = time.time() - start_time
                logger.info(f"Neo4j起動完了（{elapsed:.1f}秒）")
                return True
            
            await asyncio.sleep(2)
        
        logger.error(f"Neo4j起動タイムアウト（{self.startup_timeout}秒）")
        return False
    
    async def _test_connection(self) -> bool:
        """Neo4j接続テスト
        
        Returns:
            bool: 接続成功時True
        """
        try:
            if not NEO4J_DRIVER_AVAILABLE:
                logger.warning("neo4j-driverが利用できません")
                return False
            
            # 認証なしで接続テスト（neo4j.confで無効化済み）
            test_driver = GraphDatabase.driver(
                self.uri,
                auth=None  # 認証無効化
            )
            
            def _test():
                with test_driver.session() as session:
                    result = session.run("RETURN 1 AS num")
                    record = result.single()
                    return record["num"] == 1
            
            success = await asyncio.get_event_loop().run_in_executor(
                None, _test
            )
            
            test_driver.close()
            return success
            
        except Exception as e:
            logger.debug(f"Neo4j接続テスト失敗: {e}")
            return False
    
    async def _stop_process(self):
        """Neo4jプロセスを停止（1秒待機後に強制終了）"""
        logger.info("Neo4jプロセスを停止中...")
        
        try:
            # bat経由の起動なので通常終了は不可正常終了の方法はすべて試したがNG仕方なく強制終了する
            # バッファフラッシュのため1秒待機（根拠はない。高速化が必要なら消してもOK）
            logger.info("データベースのバッファフラッシュを待機中...")
            await asyncio.sleep(2)
            
            # 強制終了で確実に停止
            logger.info("java.exeプロセスを強制終了中...")
            
            kill_cmd = ["taskkill", "/F", "/IM", "java.exe"]
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(kill_cmd, capture_output=True, text=True, encoding='cp932', check=False)
            )
            
            if result.returncode == 0:
                logger.info("java.exeプロセスの強制終了が成功しました")
            else:
                logger.debug(f"java.exe強制終了警告 (exit code: {result.returncode})")
            
            logger.info("Neo4jプロセス強制終了が完了しました")
            
        except Exception as e:
            logger.error(f"強制終了エラー: {e}")
        finally:
            self.process = None
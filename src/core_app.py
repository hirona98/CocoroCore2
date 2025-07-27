"""
CocoroCore2 Core Application - MOS.simple() Version

MemOS.simple()を使用したシンプルで確実な実装
"""

import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from memos.mem_os.main import MOS

from config import CocoroCore2Config


class CocoroCore2App:
    """MOS.simple()を使用したCocoroCore2メインアプリケーション"""
    
    def __init__(self, config: CocoroCore2Config):
        """初期化
        
        Args:
            config: CocoroCore2設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # MOS.simple()用の環境変数設定
        self._setup_memos_environment()
        
        # MOS.simple()で簡単な統合
        try:
            self.mos = MOS.simple()
            self.logger.info("MOS.simple() initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MOS.simple(): {e}")
            raise
        
        # セッション管理（session_id -> user_id マッピング）
        self.session_mapping: Dict[str, str] = {}
        
        # アプリケーション状態
        self.is_running = False
        self.startup_time = datetime.now()
        
        self.logger.info("CocoroCore2App initialized with MOS.simple() integration")
    
    def _setup_memos_environment(self):
        """MOS.simple()用の環境変数を設定する"""
        try:
            # 設定ファイルからAPIキーを取得
            api_key = self.config.mos_config["chat_model"]["config"]["api_key"]
            
            # 環境変数設定
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["MOS_TEXT_MEM_TYPE"] = "general_text"
            
            # 必要に応じて他の環境変数も設定
            if "OPENAI_API_BASE" not in os.environ:
                # デフォルトのOpenAI API base URLを使用
                pass
            
            self.logger.info("MemOS environment variables configured")
            
        except Exception as e:
            self.logger.error(f"Failed to setup MemOS environment: {e}")
            raise
    
    async def startup(self):
        """アプリケーション起動処理"""
        try:
            self.logger.info("Starting CocoroCore2App...")
            
            # MemOSは既に初期化済み（MOS.simple()）
            # テスト用のメモリ追加で動作確認
            try:
                test_content = f"System startup at {datetime.now().isoformat()}"
                self.mos.add(memory_content=test_content)
                self.logger.info("MemOS functionality verified")
            except Exception as e:
                self.logger.warning(f"MemOS test failed: {e}")
            
            # 音声処理パイプラインの初期化（将来実装）
            if self.config.speech.enabled:
                self.logger.info("Speech processing is enabled")
                # await self.voice_pipeline.initialize()
            
            # MCP統合の初期化（将来実装）
            if self.config.mcp.enabled:
                self.logger.info("MCP integration is enabled")
                # await self.mcp_tools.initialize()
            
            self.is_running = True
            self.logger.info("CocoroCore2App startup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to start CocoroCore2App: {e}")
            raise
    
    async def shutdown(self):
        """アプリケーション終了処理"""
        try:
            self.logger.info("Shutting down CocoroCore2App...")
            
            # 各コンポーネントのクリーンアップ
            # MOS.simple()は特別なクリーンアップ不要
            
            # 音声処理パイプラインのクリーンアップ（将来実装）
            # await self.voice_pipeline.cleanup()
            
            # MCP統合のクリーンアップ（将来実装）
            # await self.mcp_tools.cleanup()
            
            self.is_running = False
            self.logger.info("CocoroCore2App shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def get_user_from_session(self, session_id: str, default_user_id: Optional[str] = None) -> str:
        """セッションIDからユーザーIDを取得する
        
        Args:
            session_id: セッションID
            default_user_id: デフォルトユーザーID
            
        Returns:
            str: ユーザーID
        """
        if session_id in self.session_mapping:
            return self.session_mapping[session_id]
        
        # セッションIDが未登録の場合、デフォルトユーザーIDを使用
        if default_user_id is None:
            # MemOS設定からdefault user_idを取得
            default_user_id = self.config.mos_config.get("user_id", "default_user")
        
        user_id = default_user_id
        self.session_mapping[session_id] = user_id
        
        self.logger.info(f"Mapped session {session_id} to user {user_id}")
        return user_id
    
    def memos_chat(self, query: str, user_id: Optional[str] = None, context: Optional[Dict] = None) -> str:
        """MemOS純正チャット処理（同期）
        
        Args:
            query: ユーザーの質問
            user_id: ユーザーID（MOS.simple()では無視される）
            context: 追加コンテキスト情報
            
        Returns:
            str: AIの応答
        """
        try:
            # MOS.simple()は単一ユーザーモードなので、user_idは使用しない
            response = self.mos.chat(query=query)
            
            # コンテキスト情報を必要に応じて記憶に追加
            if context:
                context_content = f"Context for query '{query}': {context}"
                self.add_memory(content=context_content)
            
            self.logger.debug(f"Chat response: {len(response)} characters")
            return response
            
        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            raise
    
    def add_memory(self, content: str, user_id: Optional[str] = None, **context) -> None:
        """記憶追加（同期）
        
        Args:
            content: 記憶内容
            user_id: ユーザーID（MOS.simple()では無視される）
            **context: 追加コンテキスト情報
        """
        try:
            # コンテキスト情報を本文に含める
            memory_content = content
            if context:
                import json
                context_info = {
                    "character": self.config.character.name,
                    "timestamp": datetime.now().isoformat(),
                    **context
                }
                memory_content += f" | Context: {json.dumps(context_info)}"
            
            # MOS.simple()APIで記憶追加
            self.mos.add(memory_content=memory_content)
            self.logger.debug(f"Memory added: {len(content)} characters")
            
        except Exception as e:
            self.logger.error(f"Failed to add memory: {e}")
            # メモリ保存の失敗はチャット機能全体を停止させない
            self.logger.warning("Memory features may be temporarily disabled")
    
    def search_memory(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """記憶検索（同期）
        
        Args:
            query: 検索クエリ
            user_id: ユーザーID（MOS.simple()では無視される）
            
        Returns:
            Dict[str, Any]: 検索結果
        """
        try:
            # MOS.simple()APIで検索
            result = self.mos.search(query=query)
            
            self.logger.debug(f"Memory search completed: {len(str(result))} characters")
            return result
            
        except Exception as e:
            self.logger.error(f"Memory search failed: {e}")
            raise
    
    def get_user_memories(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """ユーザーの全記憶を取得
        
        Args:
            user_id: ユーザーID（MOS.simple()では無視される）
            
        Returns:
            Dict[str, Any]: 全記憶データ
        """
        try:
            # MOS.simple()APIで全記憶取得
            result = self.mos.get_all()
            
            self.logger.debug("Retrieved all memories")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get memories: {e}")
            raise
    
    def get_app_status(self) -> Dict[str, Any]:
        """アプリケーション状態を取得
        
        Returns:
            Dict[str, Any]: 状態情報
        """
        try:
            # セッション情報
            active_sessions = len(self.session_mapping)
            
            status = {
                "status": "healthy" if self.is_running else "stopped",
                "version": self.config.version,
                "character": self.config.character.name,
                "memory_enabled": True,
                "memory_type": "MemOS.simple()",
                "startup_time": self.startup_time.isoformat(),
                "active_sessions": active_sessions,
                "memos_status": {
                    "type": "simple",
                    "backend": "general_text + qdrant_local",
                    "sessions": active_sessions,
                },
                "features": {
                    "speech_enabled": self.config.speech.enabled,
                    "mcp_enabled": self.config.mcp.enabled,
                    "shell_integration": self.config.shell_integration.enabled,
                }
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get app status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "version": self.config.version,
            }
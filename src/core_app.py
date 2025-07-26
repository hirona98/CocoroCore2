"""
CocoroCore2 Core Application

MemOS統合による統一アプリケーション
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from memos.configs.mem_os import MOSConfig
from memos.mem_os.main import MOS

from .config import CocoroCore2Config


class CocoroCore2App:
    """MemOSを直接統合したCocoroCore2メインアプリケーション"""
    
    def __init__(self, config: CocoroCore2Config):
        """初期化
        
        Args:
            config: CocoroCore2設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # MemOSを直接統合
        mos_config = MOSConfig.from_dict(config.mos_config)
        self.mos = MOS(mos_config)
        
        # セッション管理（session_id -> user_id マッピング）
        self.session_mapping: Dict[str, str] = {}
        
        # アプリケーション状態
        self.is_running = False
        self.startup_time = datetime.now()
        
        self.logger.info("CocoroCore2App initialized with MemOS integration")
    
    async def startup(self):
        """アプリケーション起動処理"""
        try:
            self.logger.info("Starting CocoroCore2App...")
            
            # MemOSの初期化（必要に応じて）
            # MemOSは自動的に初期化されるため、特別な処理は不要
            
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
            # MemOSは特別なクリーンアップ不要
            
            # 音声処理パイプラインのクリーンアップ（将来実装）
            # await self.voice_pipeline.cleanup()
            
            # MCP統合のクリーンアップ（将来実装）
            # await self.mcp_tools.cleanup()
            
            self.is_running = False
            self.logger.info("CocoroCore2App shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def ensure_user(self, user_id: str) -> str:
        """ユーザーの存在を確保する
        
        Args:
            user_id: ユーザーID
            
        Returns:
            str: 確保されたユーザーID
        """
        try:
            # MemOSでユーザーが存在するかチェック
            users = self.mos.list_users()
            existing_user_ids = [user['user_id'] for user in users]
            
            if user_id not in existing_user_ids:
                self.logger.info(f"Creating new user: {user_id}")
                self.mos.create_user(user_id=user_id)
            
            return user_id
            
        except Exception as e:
            self.logger.error(f"Failed to ensure user {user_id}: {e}")
            raise
    
    def get_user_from_session(self, session_id: str, default_user_id: str = "hirona") -> str:
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
        user_id = default_user_id
        self.session_mapping[session_id] = user_id
        
        # ユーザーの存在を確保
        self.ensure_user(user_id)
        
        return user_id
    
    def memos_chat(self, query: str, user_id: str, context: Optional[Dict] = None) -> str:
        """MemOS純正チャット処理（同期）
        
        Args:
            query: ユーザーの質問
            user_id: ユーザーID
            context: 追加コンテキスト情報
            
        Returns:
            str: AIの応答
        """
        try:
            # ユーザーの存在を確保
            self.ensure_user(user_id)
            
            # MemOS純正API: 同期処理、完全なレスポンス返却
            response = self.mos.chat(query=query, user_id=user_id)
            
            # コンテキスト情報を必要に応じて記憶に追加
            if context:
                self.add_contextual_memory(
                    content=f"Context for query '{query}': {json.dumps(context)}",
                    user_id=user_id
                )
            
            self.logger.debug(f"Chat response for user {user_id}: {len(response)} characters")
            return response
            
        except Exception as e:
            self.logger.error(f"Chat failed for user {user_id}: {e}")
            raise
    
    def add_memory(self, content: str, user_id: str, **context) -> None:
        """記憶追加（同期、metadata非対応のため統合）
        
        Args:
            content: 記憶内容
            user_id: ユーザーID
            **context: 追加コンテキスト情報
        """
        try:
            # ユーザーの存在を確保
            self.ensure_user(user_id)
            
            # MemOSはmetadataパラメータ未サポート、コンテキストを本文に含める
            memory_content = content
            if context:
                context_info = {
                    "character": self.config.character.name,
                    "timestamp": datetime.now().isoformat(),
                    **context
                }
                memory_content += f" | Context: {json.dumps(context_info)}"
            
            # MemOS純正API: 同期処理
            self.mos.add(memory_content=memory_content, user_id=user_id)
            
            self.logger.debug(f"Memory added for user {user_id}: {len(content)} characters")
            
        except Exception as e:
            self.logger.error(f"Failed to add memory for user {user_id}: {e}")
            raise
    
    def add_contextual_memory(self, content: str, user_id: str, **context) -> None:
        """コンテキスト付き記憶追加
        
        Args:
            content: 記憶内容
            user_id: ユーザーID
            **context: コンテキスト情報
        """
        self.add_memory(content, user_id, **context)
    
    def search_memory(self, query: str, user_id: str) -> Dict[str, Any]:
        """記憶検索（同期、辞書形式返却）
        
        Args:
            query: 検索クエリ
            user_id: ユーザーID
            
        Returns:
            Dict[str, Any]: 検索結果
            Format: {"text_mem": [{"cube_id": "...", "memories": [...]}], "act_mem": [], "para_mem": []}
        """
        try:
            # ユーザーの存在を確保
            self.ensure_user(user_id)
            
            # MemOS純正API: 同期処理、辞書形式返却
            result = self.mos.search(query=query, user_id=user_id)
            
            self.logger.debug(f"Memory search for user {user_id}: {len(str(result))} characters")
            return result
            
        except Exception as e:
            self.logger.error(f"Memory search failed for user {user_id}: {e}")
            raise
    
    def get_user_memories(self, user_id: str) -> Dict[str, Any]:
        """ユーザーの全記憶を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            Dict[str, Any]: 全記憶データ
        """
        try:
            # ユーザーの存在を確保
            self.ensure_user(user_id)
            
            # MemOS純正API: 全記憶取得
            result = self.mos.get_all(user_id=user_id)
            
            self.logger.debug(f"Retrieved all memories for user {user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get memories for user {user_id}: {e}")
            raise
    
    def get_app_status(self) -> Dict[str, Any]:
        """アプリケーション状態を取得
        
        Returns:
            Dict[str, Any]: 状態情報
        """
        try:
            # MemOS状態情報の取得
            users = self.mos.list_users()
            
            # セッション情報
            active_sessions = len(self.session_mapping)
            
            status = {
                "status": "healthy" if self.is_running else "stopped",
                "version": self.config.version,
                "character": self.config.character.name,
                "memory_enabled": True,
                "startup_time": self.startup_time.isoformat(),
                "active_sessions": active_sessions,
                "memos_status": {
                    "users": len(users),
                    "total_sessions": active_sessions,
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
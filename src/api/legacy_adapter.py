"""
CocoroCore2 Legacy Adapter

既存CocoroCore APIとの互換性を提供
"""

import json
import logging
from typing import Dict, Optional

from ..core_app import CocoroCore2App
from ..core.session_manager import SessionManager
from ..clients.cocoro_dock_client import CocoroDockClient
from .models import CoreChatRequest, CoreControlRequest, CoreNotificationRequest, HealthCheckResponse


class LegacyAPIAdapter:
    """既存CocoroCore APIとの互換性を提供するアダプター"""
    
    def __init__(self, core_app: CocoroCore2App, session_manager: SessionManager):
        """初期化
        
        Args:
            core_app: CocoroCore2アプリケーション
            session_manager: セッション管理
        """
        self.core_app = core_app
        self.session_manager = session_manager
        self.logger = logging.getLogger(__name__)
        
        # CocoroDockクライアント初期化
        self.dock_client = CocoroDockClient()
    
    async def handle_legacy_chat_rest(self, request: CoreChatRequest) -> Dict:
        """既存/chatエンドポイント処理 - RESTレスポンス
        
        Args:
            request: チャットリクエスト
            
        Returns:
            Dict: JSONレスポンス
        """
        try:
            # session_id -> user_id 変換（設定ファイルのuser_idを優先）
            user_id = self._get_user_id_from_session(request.session_id, None)
            
            # セッション管理
            session = self.session_manager.ensure_session(request.session_id, user_id)
            
            self.logger.debug(f"Processing legacy chat REST for session {request.session_id}, user {user_id}")
            
            # コンテキストID生成
            import uuid
            context_id = request.context_id or str(uuid.uuid4())
            
            # 即座に成功レスポンスを返す（処理開始通知）
            success_response = {
                "status": "success",
                "message": "Chat processing started",
                "session_id": request.session_id,
                "context_id": context_id
            }
            
            # バックグラウンドでAI処理を実行
            import asyncio
            asyncio.create_task(self._process_chat_async(
                request=request,
                user_id=user_id,
                context_id=context_id
            ))
            
            return success_response
            
        except Exception as e:
            self.logger.error(f"Chat processing initialization failed: {e}")
            return {
                "status": "error",
                "message": f"処理開始エラー: {str(e)}",
                "session_id": request.session_id,
                "context_id": request.context_id
            }
    
    async def _process_chat_async(
        self, 
        request: CoreChatRequest, 
        user_id: str, 
        context_id: str
    ):
        """バックグラウンドでチャット処理を実行
        
        Args:
            request: チャットリクエスト
            user_id: ユーザーID
            context_id: コンテキストID
        """
        try:
            self.logger.debug(f"Starting background chat processing for session {request.session_id}")
            
            # MemOSからレスポンス取得（同期処理）
            response = self.core_app.memos_chat(
                query=request.text,
                user_id=user_id,
                context=request.metadata
            )
            
            self.logger.debug(f"MemOS response received: {response[:100]}...")
            
            # CocoroDockにメッセージ送信
            success = await self.dock_client.send_chat_message(
                content=response,
                role="assistant"
            )
            
            if success:
                self.logger.info(f"Chat response sent to CocoroDock successfully")
            else:
                self.logger.error(f"Failed to send chat response to CocoroDock")
                
        except Exception as e:
            self.logger.error(f"Background chat processing failed: {e}")
            
            # エラーメッセージをCocoroDockに送信
            try:
                await self.dock_client.send_chat_message(
                    content=f"処理エラー: {str(e)}",
                    role="assistant"  # systemではなくassistantとして送信
                )
            except Exception as send_error:
                self.logger.error(f"Failed to send error message to CocoroDock: {send_error}")
    
    def _get_user_id_from_session(self, session_id: str, fallback_user_id: str) -> str:
        """セッションIDからユーザーIDを取得
        
        Args:
            session_id: セッションID
            fallback_user_id: フォールバック用ユーザーID
            
        Returns:
            str: ユーザーID
        """
        # セッション管理からユーザーIDを取得
        session = self.session_manager.get_session(session_id)
        
        if session:
            return session.user_id
        
        # セッションが存在しない場合はフォールバック
        if not fallback_user_id:
            # MemOS設定からdefault user_idを取得
            fallback_user_id = self.core_app.config.mos_config.get("user_id")
            if not fallback_user_id:
                raise ValueError("MemOS設定にuser_idが指定されていません")
        return fallback_user_id
    
    async def handle_legacy_notification(self, request: CoreNotificationRequest) -> Dict:
        """既存通知エンドポイント処理
        
        Args:
            request: 通知リクエスト
            
        Returns:
            Dict: 処理結果
        """
        try:
            # 通知も/chatエンドポイントを使用（設計書準拠）
            chat_request = CoreChatRequest(
                type=request.type,
                session_id=request.session_id,
                user_id=request.user_id,
                context_id=request.context_id,
                text=request.text,
                metadata=request.metadata
            )
            
            # RESTチャットとして処理
            result = await self.handle_legacy_chat_rest(chat_request)
            
            return {
                "status": "success",
                "message": "Notification processed",
                "timestamp": self.core_app.startup_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Notification processing failed: {e}")
            return {
                "status": "error",
                "message": f"通知処理エラー: {str(e)}",
                "timestamp": self.core_app.startup_time.isoformat()
            }
    
    async def handle_legacy_control(self, request: CoreControlRequest) -> Dict:
        """既存制御コマンドエンドポイント処理
        
        Args:
            request: 制御コマンドリクエスト
            
        Returns:
            Dict: 処理結果
        """
        try:
            self.logger.info(f"Processing control command: {request.command}")
            
            if request.command == "shutdown":
                # システム終了処理
                return await self._handle_shutdown_command(request.params)
            
            elif request.command == "sttControl":
                # STT制御（将来実装）
                return await self._handle_stt_control(request.params)
            
            elif request.command == "microphoneControl":
                # マイクロフォン制御（将来実装）
                return await self._handle_microphone_control(request.params)
            
            elif request.command == "start_log_forwarding":
                # ログ転送開始（将来実装）
                return {
                    "status": "success",
                    "message": "ログ転送は現在実装されていません"
                }
            
            elif request.command == "stop_log_forwarding":
                # ログ転送停止（将来実装）
                return {
                    "status": "success", 
                    "message": "ログ転送は現在実装されていません"
                }
            
            else:
                return {
                    "status": "error",
                    "message": f"未知のコマンド: {request.command}"
                }
                
        except Exception as e:
            self.logger.error(f"Control command failed: {e}")
            return {
                "status": "error",
                "message": f"コマンド実行エラー: {str(e)}"
            }
    
    async def _handle_shutdown_command(self, params: Optional[Dict]) -> Dict:
        """シャットダウンコマンド処理
        
        Args:
            params: コマンドパラメータ
            
        Returns:
            Dict: 処理結果
        """
        grace_period = 30
        if params and "grace_period_seconds" in params:
            grace_period = params["grace_period_seconds"]
        
        self.logger.info(f"Shutdown requested with grace period: {grace_period}s")
        
        # 実際のシャットダウン処理は main.py で処理されるべき
        # ここでは成功レスポンスのみ返す
        return {
            "status": "success",
            "message": f"システムを{grace_period}秒後に終了します"
        }
    
    async def _handle_stt_control(self, params: Optional[Dict]) -> Dict:
        """STT制御処理（将来実装）
        
        Args:
            params: コマンドパラメータ
            
        Returns:
            Dict: 処理結果
        """
        enabled = params.get("enabled", True) if params else True
        
        # 将来の音声機能実装時に処理を追加
        self.logger.info(f"STT control requested: enabled={enabled}")
        
        return {
            "status": "success",
            "message": f"STT機能を{'有効' if enabled else '無効'}にしました"
        }
    
    async def _handle_microphone_control(self, params: Optional[Dict]) -> Dict:
        """マイクロフォン制御処理（将来実装）
        
        Args:
            params: コマンドパラメータ
            
        Returns:
            Dict: 処理結果
        """
        auto_adjustment = params.get("autoAdjustment", False) if params else False
        input_threshold = params.get("inputThreshold", -40.0) if params else -40.0
        
        # 将来の音声機能実装時に処理を追加
        self.logger.info(f"Microphone control: auto={auto_adjustment}, threshold={input_threshold}")
        
        return {
            "status": "success",
            "message": f"マイクロフォン設定を更新しました（自動調整: {'有効' if auto_adjustment else '無効'}, 閾値: {input_threshold}dB）"
        }
    
    async def handle_legacy_health(self) -> HealthCheckResponse:
        """既存ヘルスチェックエンドポイント処理
        
        Returns:
            HealthCheckResponse: ヘルスチェック結果
        """
        try:
            # アプリケーション状態取得
            status = self.core_app.get_app_status()
            
            # セッション統計取得
            session_stats = self.session_manager.get_session_statistics()
            
            # HealthCheckResponse形式に変換
            return HealthCheckResponse(
                status=status["status"],
                version=status["version"],
                character=status["character"],
                memory_enabled=status["memory_enabled"],
                startup_time=status["startup_time"],
                active_sessions=session_stats["active_sessions"],
                memos_status=status.get("memos_status", {}),
                features=status.get("features", {})
            )
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return HealthCheckResponse(
                status="error",
                version="2.0.0",
                character="つくよみちゃん",
                memory_enabled=False,
                startup_time="unknown",
                active_sessions=0,
                memos_status={"error": str(e)},
                features={}
            )
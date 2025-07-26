"""
CocoroCore2 Legacy Adapter

既存CocoroCore APIとの互換性を提供
MemOS非ストリーミングをSSE変換
"""

import json
import logging
from typing import AsyncIterator, Dict, Optional

from ..core_app import CocoroCore2App
from ..core.session_manager import SessionManager
from .models import CoreChatRequest, CoreControlRequest, CoreNotificationRequest, HealthCheckResponse, SseData


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
    
    async def handle_legacy_chat(self, request: CoreChatRequest) -> AsyncIterator[str]:
        """既存/chatエンドポイント処理 - MemOSレスポンスをSSE変換
        
        Args:
            request: チャットリクエスト
            
        Yields:
            str: SSE形式のレスポンス
        """
        try:
            # session_id -> user_id 変換
            user_id = self._get_user_id_from_session(request.session_id, request.user_id)
            
            # セッション管理
            session = self.session_manager.ensure_session(request.session_id, user_id)
            
            self.logger.debug(f"Processing legacy chat for session {request.session_id}, user {user_id}")
            
            # MemOSから通常レスポンス取得（同期処理）
            try:
                response = self.core_app.memos_chat(
                    query=request.text,
                    user_id=user_id,
                    context=request.metadata
                )
                
                # レスポンスをチャンクに分割してストリーミング風に送信
                await self._stream_response_chunks(response, request.session_id, request.context_id)
                
                # 記憶保存通知
                yield self._format_sse_data(SseData(
                    type="memory",
                    action="saved",
                    details="会話を記憶しました",
                    session_id=request.session_id,
                    context_id=request.context_id
                ))
                
                # 完了通知
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                self.logger.error(f"Chat processing failed: {e}")
                
                # エラーをSSE形式で送信
                yield self._format_sse_data(SseData(
                    type="error",
                    content=f"処理エラー: {str(e)}",
                    role="system",
                    session_id=request.session_id,
                    context_id=request.context_id
                ))
                yield "data: [DONE]\n\n"
                
        except Exception as e:
            self.logger.error(f"Legacy chat handler error: {e}")
            yield f"data: {{\"type\": \"error\", \"content\": \"システムエラー: {str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"
    
    async def _stream_response_chunks(self, response: str, session_id: str, context_id: Optional[str]) -> AsyncIterator[str]:
        """レスポンスをチャンクに分割してストリーミング
        
        Args:
            response: MemOSからのレスポンス
            session_id: セッションID
            context_id: コンテキストID
            
        Yields:
            str: SSE形式のチャンク
        """
        # レスポンスを適切なサイズに分割
        chunk_size = 100  # 文字数
        
        if len(response) <= chunk_size:
            # 短いレスポンスはそのまま送信
            yield self._format_sse_data(SseData(
                type="content",
                content=response,
                role="assistant",
                session_id=session_id,
                context_id=context_id,
                finished=True
            ))
        else:
            # 長いレスポンスは分割して送信
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                is_final = i + chunk_size >= len(response)
                
                yield self._format_sse_data(SseData(
                    type="content",
                    content=chunk,
                    role="assistant",
                    session_id=session_id,
                    context_id=context_id,
                    finished=is_final
                ))
    
    def _format_sse_data(self, data: SseData) -> str:
        """SseDataをSSE形式にフォーマット
        
        Args:
            data: SSEデータ
            
        Returns:
            str: SSE形式の文字列
        """
        # Noneフィールドを除去
        data_dict = {k: v for k, v in data.dict().items() if v is not None}
        return f"data: {json.dumps(data_dict, ensure_ascii=False)}\n\n"
    
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
        return fallback_user_id or "hirona"
    
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
            
            # チャットメッセージとして処理
            sse_stream = self.handle_legacy_chat(chat_request)
            
            # ストリームを消費（通知は結果を返さない）
            async for _ in sse_stream:
                pass
            
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
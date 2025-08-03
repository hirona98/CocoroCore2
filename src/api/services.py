"""
CocoroCore2 API Services

各エンドポイントのビジネスロジックを提供
"""

import asyncio
import logging
from typing import Dict, Optional
from ..core_app import CocoroCore2App
from ..core.session_manager import SessionManager
from ..clients.cocoro_dock_client import CocoroDockClient
from .models import CoreControlRequest, CoreNotificationRequest, HealthCheckResponse
from ..log_handler import get_dock_log_handler


logger = logging.getLogger(__name__)


class HealthService:
    """ヘルスチェック関連サービス"""
    
    def __init__(self, core_app: CocoroCore2App, session_manager: SessionManager):
        self.core_app = core_app
        self.session_manager = session_manager
    
    async def get_health_status(self) -> HealthCheckResponse:
        """ヘルスチェック処理"""
        try:
            # アプリケーション状態取得
            status = self.core_app.get_app_status()
            
            # セッション統計取得
            session_stats = self.session_manager.get_session_statistics()
            
            # HealthCheckResponse形式に変換
            return HealthCheckResponse(
                status=status["status"],
                startup_time=status["startup_time"],
                active_sessions=session_stats["active_sessions"],
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheckResponse(
                status="error",
                startup_time="",
                active_sessions=0
            )


class ControlService:
    """制御コマンド関連サービス"""
    
    def __init__(self, core_app: CocoroCore2App):
        self.core_app = core_app
        self.logger = logging.getLogger(__name__)
    
    async def handle_control_command(self, request: CoreControlRequest) -> Dict:
        """制御コマンド処理"""
        try:
            self.logger.info(f"Processing control command: {request.command}")
            
            if request.command == "shutdown":
                # システム終了処理
                return await self._handle_shutdown_command(request.params)

            elif request.command == "start_log_forwarding":
                # ログ転送開始
                return self._handle_start_log_forwarding()
            
            elif request.command == "stop_log_forwarding":
                # ログ転送停止
                return self._handle_stop_log_forwarding()
            
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
        """システム終了コマンド処理"""
        try:
            # システム終了ログ
            self.logger.info("Shutdown command received")
            
            # バックグラウンドでシャットダウン処理を開始
            asyncio.create_task(self._execute_shutdown())
            
            # 即座に受付確認を返す
            return {
                "status": "success",
                "message": "システム終了要求を受け付けました。"
            }
            
        except Exception as e:
            self.logger.error(f"Shutdown command failed: {e}")
            return {
                "status": "error",
                "message": f"終了処理エラー: {str(e)}"
            }
    
    async def _execute_shutdown(self):
        """バックグラウンドでシャットダウン処理を実行"""
        try:
            self.logger.info("Starting background shutdown process...")
            
            # アプリケーションのシャットダウン
            await self.core_app.shutdown()
            self.logger.info("Application shutdown completed")
            
            # サーバー停止のためのシグナル送信
            import os
            import signal
            self.logger.info("Sending shutdown signal to server...")
            os.kill(os.getpid(), signal.SIGTERM)
            
        except Exception as e:
            self.logger.error(f"Background shutdown failed: {e}")
    
    def _handle_start_log_forwarding(self) -> Dict:
        """ログ転送開始処理"""
        try:
            dock_log_handler = get_dock_log_handler()
            if dock_log_handler is not None:
                dock_log_handler.set_enabled(True)
                self.logger.info("ログ転送を開始しました")
                return {
                    "status": "success",
                    "message": "ログ転送を開始しました"
                }
            else:
                self.logger.warning("ログハンドラーが初期化されていません")
                return {
                    "status": "error",
                    "message": "ログハンドラーが初期化されていません"
                }
        except Exception as e:
            self.logger.error(f"ログ転送開始エラー: {e}")
            return {
                "status": "error",
                "message": f"ログ転送開始エラー: {str(e)}"
            }
    
    def _handle_stop_log_forwarding(self) -> Dict:
        """ログ転送停止処理"""
        try:
            dock_log_handler = get_dock_log_handler()
            if dock_log_handler is not None:
                dock_log_handler.set_enabled(False)
                self.logger.info("ログ転送を停止しました")
                return {
                    "status": "success",
                    "message": "ログ転送を停止しました"
                }
            else:
                self.logger.warning("ログハンドラーが初期化されていません")
                return {
                    "status": "error",
                    "message": "ログハンドラーが初期化されていません"
                }
        except Exception as e:
            self.logger.error(f"ログ転送停止エラー: {e}")
            return {
                "status": "error",
                "message": f"ログ転送停止エラー: {str(e)}"
            }


class NotificationService:
    """通知関連サービス"""
    
    def __init__(self, core_app: CocoroCore2App, session_manager: SessionManager):
        self.core_app = core_app
        self.session_manager = session_manager
        self.dock_client = CocoroDockClient()
        self.logger = logging.getLogger(__name__)
    
    async def handle_notification(self, request: CoreNotificationRequest) -> Dict:
        """通知処理"""
        try:
            # ユーザーの存在を確保
            self.core_app.ensure_user(request.user_id)
            
            # セッション管理
            session = self.session_manager.ensure_session(request.session_id, request.user_id)
            
            # MemOSに直接送信（非同期）
            response = await self.core_app.memos_chat(
                query=request.text,
                user_id=request.user_id,
                context=request.metadata
            )
            
            # CocoroDockにメッセージ送信
            await self.dock_client.send_chat_message(
                content=response,
                role="assistant"
            )
            
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
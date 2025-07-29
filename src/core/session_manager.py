"""
CocoroCore2 Session Manager

セッション管理とタイムアウト処理(MemOSのユーザー管理)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

class SessionInfo:
    """セッション情報"""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.request_count = 0
        self.is_active = True
    
    def update_activity(self):
        """アクティビティを更新"""
        self.last_activity = datetime.now()
        self.request_count += 1
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """セッションが期限切れかチェック"""
        expiry_time = self.last_activity + timedelta(seconds=timeout_seconds)
        return datetime.now() > expiry_time
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "request_count": self.request_count,
            "is_active": self.is_active,
        }


class SessionManager:
    """セッション管理"""
    
    def __init__(self, timeout_seconds: int = 300, max_sessions: int = 1000, cleanup_interval_seconds: int = 30):
        """初期化
        
        Args:
            timeout_seconds: セッションタイムアウト秒数
            max_sessions: 最大セッション数
            cleanup_interval_seconds: クリーンアップ間隔秒数
        """
        self.timeout_seconds = timeout_seconds
        self.max_sessions = max_sessions
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.logger = logging.getLogger(__name__)
        
        # セッション保存
        self.sessions: Dict[str, SessionInfo] = {}
        
        # ユーザー別セッション（ユーザーIDから逆引き）
        self.user_sessions: Dict[str, Set[str]] = {}
        
        # クリーンアップタスク
        self.cleanup_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    async def start(self):
        """セッション管理開始"""
        if self.is_running:
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("Session manager started")
    
    async def stop(self):
        """セッション管理停止"""
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Session manager stopped")
    
    def create_session(self, session_id: str, user_id: str) -> SessionInfo:
        """セッションを作成
        
        Args:
            session_id: セッションID
            user_id: ユーザーID
            
        Returns:
            SessionInfo: 作成されたセッション情報
        """
        # 既存セッションをクリーンアップ
        if session_id in self.sessions:
            self.remove_session(session_id)
        
        # 最大セッション数チェック
        if len(self.sessions) >= self.max_sessions:
            self._cleanup_oldest_sessions()
        
        # 新しいセッション作成
        session = SessionInfo(session_id, user_id)
        self.sessions[session_id] = session
        
        # ユーザー別セッション管理
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_id)
        
        self.logger.debug(f"Created session: {session_id} for user: {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """セッション情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            Optional[SessionInfo]: セッション情報（存在しない場合はNone）
        """
        session = self.sessions.get(session_id)
        
        if session and session.is_expired(self.timeout_seconds):
            self.remove_session(session_id)
            return None
        
        return session
    
    def update_session_activity(self, session_id: str) -> bool:
        """セッションのアクティビティを更新
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 更新成功可否
        """
        session = self.get_session(session_id)
        if session:
            session.update_activity()
            self.logger.debug(f"Updated activity for session: {session_id}")
            return True
        return False
    
    def remove_session(self, session_id: str) -> bool:
        """セッションを削除
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 削除成功可否
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # セッション削除
        del self.sessions[session_id]
        
        # ユーザー別セッションからも削除
        user_id = session.user_id
        if user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_id)
            # ユーザーのセッションが空になったら削除
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
        
        self.logger.debug(f"Removed session: {session_id}")
        return True
    
    def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """ユーザーの全セッションを取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            List[SessionInfo]: セッション情報のリスト
        """
        if user_id not in self.user_sessions:
            return []
        
        sessions = []
        for session_id in list(self.user_sessions[user_id]):  # コピーして反復
            session = self.get_session(session_id)
            if session:
                sessions.append(session)
        
        return sessions
    
    def get_session_statistics(self) -> Dict:
        """セッション統計を取得
        
        Returns:
            Dict: 統計情報
        """
        active_sessions = len(self.sessions)
        total_users = len(self.user_sessions)
        
        # アクティビティ統計
        total_requests = sum(session.request_count for session in self.sessions.values())
        
        # 期限切れセッション数
        expired_count = 0
        for session in self.sessions.values():
            if session.is_expired(self.timeout_seconds):
                expired_count += 1
        
        return {
            "active_sessions": active_sessions,
            "total_users": total_users,
            "total_requests": total_requests,
            "expired_sessions": expired_count,
            "max_sessions": self.max_sessions,
            "timeout_seconds": self.timeout_seconds,
        }
    
    def ensure_session(self, session_id: str, user_id: str) -> SessionInfo:
        """セッションの存在を確保（存在しない場合は作成）
        
        Args:
            session_id: セッションID
            user_id: ユーザーID
            
        Returns:
            SessionInfo: セッション情報
        """
        session = self.get_session(session_id)
        
        if session is None:
            session = self.create_session(session_id, user_id)
        else:
            # アクティビティ更新
            session.update_activity()
        
        return session
    
    def _cleanup_oldest_sessions(self):
        """最も古いセッションをクリーンアップ"""
        if not self.sessions:
            return
        
        # 最も古いセッションを特定
        oldest_session = min(self.sessions.values(), key=lambda s: s.last_activity)
        self.remove_session(oldest_session.session_id)
        self.logger.info(f"Cleaned up oldest session: {oldest_session.session_id}")
    
    async def _cleanup_loop(self):
        """期限切れセッションの定期クリーンアップ"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval_seconds)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired_sessions(self):
        """期限切れセッションをクリーンアップ"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired(self.timeout_seconds):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
        
        if expired_sessions:
            self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
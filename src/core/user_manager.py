"""
CocoroCore2 User Manager

MemOSのマルチユーザー機能をサポートするためのユーザー管理モジュール
"""

import logging
from typing import Dict, List, Optional

from memos.mem_os.main import MOS


class UserManager:
    """MemOS対応ユーザー管理"""
    
    def __init__(self, mos: MOS):
        """初期化
        
        Args:
            mos: MemOSインスタンス
        """
        self.mos = mos
        self.logger = logging.getLogger(__name__)
        
        # ユーザーキャッシュ（パフォーマンス向上のため）
        self._user_cache: Dict[str, Dict] = {}
    
    def create_user(self, user_id: str, user_name: Optional[str] = None, role: str = "user") -> bool:
        """ユーザーを作成する
        
        Args:
            user_id: ユーザーID
            user_name: ユーザー名（省略時はuser_idを使用）
            role: ユーザーロール
            
        Returns:
            bool: 作成成功可否
        """
        try:
            # 既存ユーザーかチェック
            if self.user_exists(user_id):
                self.logger.info(f"User {user_id} already exists")
                return True
            
            # MemOSでユーザー作成
            self.mos.create_user(user_id=user_id)
            
            # キャッシュに追加
            user_info = {
                "user_id": user_id,
                "user_name": user_name or user_id,
                "role": role,
                "created": True
            }
            self._user_cache[user_id] = user_info
            
            self.logger.info(f"Created user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create user {user_id}: {e}")
            return False
    
    def user_exists(self, user_id: str) -> bool:
        """ユーザーが存在するかチェック
        
        Args:
            user_id: ユーザーID
            
        Returns:
            bool: 存在可否
        """
        try:
            # キャッシュから確認
            if user_id in self._user_cache:
                return True
            
            # MemOSから確認
            users = self.mos.list_users()
            existing_user_ids = [user['user_id'] for user in users]
            
            exists = user_id in existing_user_ids
            
            # キャッシュを更新
            if exists:
                user_info = next((u for u in users if u['user_id'] == user_id), None)
                if user_info:
                    self._user_cache[user_id] = user_info
            
            return exists
            
        except Exception as e:
            self.logger.error(f"Failed to check user existence {user_id}: {e}")
            return False
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """ユーザー情報を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            Optional[Dict]: ユーザー情報（存在しない場合はNone）
        """
        try:
            # キャッシュから確認
            if user_id in self._user_cache:
                return self._user_cache[user_id]
            
            # MemOSから取得
            users = self.mos.list_users()
            user_info = next((u for u in users if u['user_id'] == user_id), None)
            
            # キャッシュを更新
            if user_info:
                self._user_cache[user_id] = user_info
            
            return user_info
            
        except Exception as e:
            self.logger.error(f"Failed to get user info {user_id}: {e}")
            return None
    
    def list_users(self) -> List[Dict]:
        """全ユーザーリストを取得
        
        Returns:
            List[Dict]: ユーザー情報のリスト
        """
        try:
            users = self.mos.list_users()
            
            # キャッシュを更新
            for user in users:
                self._user_cache[user['user_id']] = user
            
            return users
            
        except Exception as e:
            self.logger.error(f"Failed to list users: {e}")
            return []
    
    def ensure_user(self, user_id: str, user_name: Optional[str] = None) -> bool:
        """ユーザーの存在を確保（存在しない場合は作成）
        
        Args:
            user_id: ユーザーID
            user_name: ユーザー名
            
        Returns:
            bool: 確保成功可否
        """
        if self.user_exists(user_id):
            return True
        
        return self.create_user(user_id, user_name)
    
    def get_user_statistics(self, user_id: str) -> Dict:
        """ユーザーの統計情報を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            Dict: 統計情報
        """
        try:
            if not self.user_exists(user_id):
                return {"error": "User not found"}
            
            # MemOSから記憶情報を取得
            memories = self.mos.get_all(user_id=user_id)
            
            stats = {
                "user_id": user_id,
                "total_memories": 0,
                "textual_memories": 0,
                "activation_memories": 0,
                "parametric_memories": 0,
            }
            
            if "text_mem" in memories:
                for cube in memories["text_mem"]:
                    if "memories" in cube:
                        stats["textual_memories"] += len(cube["memories"])
            
            if "act_mem" in memories:
                stats["activation_memories"] = len(memories["act_mem"])
            
            if "para_mem" in memories:
                stats["parametric_memories"] = len(memories["para_mem"])
            
            stats["total_memories"] = (
                stats["textual_memories"] + 
                stats["activation_memories"] + 
                stats["parametric_memories"]
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get user statistics {user_id}: {e}")
            return {"error": str(e)}
    
    def clear_cache(self):
        """ユーザーキャッシュをクリア"""
        self._user_cache.clear()
        self.logger.debug("User cache cleared")
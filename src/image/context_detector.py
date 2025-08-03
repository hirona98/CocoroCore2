"""
CocoroCore2 コンテキスト判定システム

メッセージから画像のコンテキストタイプを判定します。
- 通常チャット
- 通知（<cocoro-notification>タグ）
- デスクトップ監視（<cocoro-desktop-monitoring>タグ）
"""

import json
import logging
import re
from typing import Dict, Optional

from ..api.models import UnifiedChatRequest
from .models import ImageContext

logger = logging.getLogger(__name__)


class ContextDetector:
    """コンテキスト判定システム"""
    
    def __init__(self):
        self.logger = logger
    
    def determine_image_context(self, request: UnifiedChatRequest) -> ImageContext:
        """
        リクエストから画像コンテキストを判定
        
        Args:
            request: 統一チャットリクエスト
            
        Returns:
            ImageContext: 判定されたコンテキスト
        """
        if not request.message:
            # メッセージが空の場合は通常チャット扱い
            return ImageContext(source_type="chat")
        
        # 通知タグの検出
        if "<cocoro-notification>" in request.message:
            notification_info = self._extract_notification_info(request.message)
            return ImageContext(
                source_type="notification",
                notification_from=notification_info.get("from", "不明なアプリ")
            )
        
        # デスクトップ監視タグの検出
        elif "<cocoro-desktop-monitoring>" in request.message:
            return ImageContext(source_type="desktop_monitoring")
        
        # 通常チャット
        else:
            return ImageContext(source_type="chat")
    
    def _extract_notification_info(self, message: str) -> Dict[str, str]:
        """
        通知メッセージから情報を抽出
        
        Args:
            message: メッセージテキスト
            
        Returns:
            Dict[str, str]: 抽出された通知情報
        """
        notification_info = {}
        
        try:
            # 通知タグのパターンマッチング
            notification_pattern = r"<cocoro-notification>\\s*({.*?})\\s*</cocoro-notification>"
            notification_match = re.search(notification_pattern, message, re.DOTALL)
            
            if notification_match:
                notification_json = notification_match.group(1)
                notification_data = json.loads(notification_json)
                
                notification_info["from"] = notification_data.get("from", "不明なアプリ")
                notification_info["message"] = notification_data.get("message", "")
                
                self.logger.info(f"通知情報を抽出: from={notification_info['from']}")
            
        except (json.JSONDecodeError, AttributeError) as e:
            self.logger.error(f"通知情報の抽出に失敗: {e}")
            notification_info["from"] = "不明なアプリ"
            notification_info["message"] = ""
        
        return notification_info
    
    def clean_message_tags(self, message: str) -> str:
        """
        メッセージからCocoroタグを除去
        
        Args:
            message: 元のメッセージ
            
        Returns:
            str: タグを除去したメッセージ
        """
        if not message:
            return ""
        
        # 通知タグを除去
        message = re.sub(r"<cocoro-notification>.*?</cocoro-notification>", "", message, flags=re.DOTALL)
        
        # デスクトップ監視タグを除去
        message = re.sub(r"<cocoro-desktop-monitoring>.*?</cocoro-desktop-monitoring>", "", message, flags=re.DOTALL)
        
        # 余分な空白を除去
        message = message.strip()
        
        return message
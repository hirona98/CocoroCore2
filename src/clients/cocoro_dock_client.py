"""
CocoroDock Client

CocoroCore2からCocoroDockのAPIにアクセスするためのクライアント
"""

import json
import logging
from typing import Dict, Optional

import httpx


class CocoroDockClient:
    """CocoroDockとの通信を行うクライアント"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 55600):
        """初期化
        
        Args:
            host: CocoroDockのホスト
            port: CocoroDockのポート
        """
        self.base_url = f"http://{host}:{port}"
        self.logger = logging.getLogger(__name__)
        
        # HTTP クライアント設定
        self.timeout = httpx.Timeout(10.0)  # 10秒タイムアウト
    
    async def send_chat_message(
        self,
        content: str,
        role: str = "assistant"
    ) -> bool:
        """CocoroDockにチャットメッセージを送信
        
        Args:
            content: メッセージ内容
            role: 役割（"assistant" または "user"）
            
        Returns:
            bool: 送信成功フラグ
        """
        try:
            # CocoroDockのChatRequestクラスに合わせてシンプルな形式で送信
            from datetime import datetime
            # 複数の形式を試すため、まずはcamelCaseで送信
            payload = {
                "content": content,     # camelCase (小文字で始まる)
                "role": role,          # camelCase
                "timestamp": datetime.utcnow().isoformat() + "Z"  # ISO 8601形式
            }
            
            # デバッグ用：送信するJSONをログ出力
            import json
            json_payload = json.dumps(payload, ensure_ascii=False)
            self.logger.debug(f"送信JSON: {json_payload}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/addChatUi",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    self.logger.debug(f"チャットメッセージをCocoroDockに送信成功: {content[:50]}...")
                    return True
                else:
                    self.logger.error(f"CocoroDockへのメッセージ送信失敗: {response.status_code} - {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            self.logger.error("CocoroDockへのメッセージ送信がタイムアウトしました")
            return False
        except httpx.ConnectError:
            self.logger.warning("CocoroDockに接続できません（未起動の可能性）")
            return False
        except Exception as e:
            self.logger.error(f"CocoroDockへのメッセージ送信エラー: {e}")
            return False
    

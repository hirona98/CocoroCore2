"""
CocoroCore2 AI主導メッセージ生成システム

通知やデスクトップ監視の際に、AIが主導的に会話を開始するためのメッセージを生成します。
キャラクターのsystem_promptを活用して、キャラクターらしい発言を生成します。
"""

import logging
from typing import Dict, Optional

from .models import ImageAnalysisResult, ImageContext

logger = logging.getLogger(__name__)


class AIInitiativeMessageGenerator:
    """AI主導メッセージ生成システム（キャラクター対応版）"""
    
    def __init__(self, core_app=None):
        self.logger = logger
        self.core_app = core_app
    
    async def generate_ai_initiative_message(
        self,
        analysis_result: ImageAnalysisResult,
        context: ImageContext,
        system_prompt: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        コンテキストに応じたAI主導メッセージ生成（動的プロンプト版）
        
        Args:
            analysis_result: 画像分析結果
            context: コンテキスト情報
            system_prompt: キャラクターのシステムプロンプト
            user_id: ユーザーID
            
        Returns:
            str: 生成されたAI主導メッセージ
        """
        try:
            # MemOSを使ってキャラクターらしいメッセージを生成
            if self.core_app and system_prompt:
                # 状況情報を動的に構築
                context_info = []
                
                if context.source_type == "notification":
                    app_name = context.notification_from or "不明なアプリ"
                    context_info.append(f"状況: {app_name}から画像付きの通知が来ました")
                    context_info.append(f"通知元: {app_name}")
                elif context.source_type == "desktop_monitoring":
                    context_info.append("状況: ユーザーのデスクトップ画面を見ています")
                else:
                    context_info.append("状況: 画像を確認しました")
                
                # 画像分析結果を追加
                context_info.extend([
                    f"画像内容: {analysis_result.description}",
                    f"分類: {analysis_result.category}",
                    f"雰囲気: {analysis_result.mood}",
                    f"時間帯: {analysis_result.time}"
                ])
                
                enhanced_prompt = f"""{system_prompt}

以下の状況について、あなたのキャラクター性を活かして自然に反応してください：

{'\n'.join(context_info)}

1〜2文の短いメッセージで、キャラクターらしく話しかけてください。"""
                
                try:
                    character_message = await self.core_app.memos_chat(
                        query=enhanced_prompt,
                        user_id=user_id or "default",
                        system_prompt=""  # プロンプトは上で組み込み済み
                    )
                    
                    # 生成されたメッセージが適切かチェック
                    if character_message and len(character_message.strip()) > 0:
                        # 長すぎる場合は最初の文だけ使用
                        sentences = character_message.split('。')
                        if len(sentences) > 2:
                            return sentences[0] + '。'
                        return character_message.strip()
                
                except Exception as e:
                    self.logger.warning(f"キャラクターメッセージ生成に失敗: {e}")
            
            # 生成に失敗した場合は例外を発生
            raise Exception("キャラクターメッセージ生成に失敗しました")
        
        except Exception as e:
            self.logger.error(f"AI主導メッセージ生成エラー: {e}")
            return "何かお知らせがありますね。"
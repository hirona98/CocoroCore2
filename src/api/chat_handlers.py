"""
CocoroCore2 チャット処理ハンドラー

画像対応機能を含む、統一チャットの処理ロジックを提供します。
"""

import asyncio
import logging
from typing import Dict, List, Optional

from ..core_app import CocoroCore2App
from ..image import (
    AIInitiativeMessageGenerator,
    ChatHandlerErrorManager,
    ContextDetector,
    ImageAnalysisResult,
    ImageContext,
    ImageProcessor,
    RobustImageAnalyzer,
)

from .models import UnifiedChatRequest, UnifiedChatResponse

logger = logging.getLogger(__name__)


class ChatHandlers:
    """統一チャット処理ハンドラー"""
    
    def __init__(self, core_app: CocoroCore2App):
        self.core_app = core_app
        self.config = core_app.config
        self.logger = logger
        
        # 画像処理関連のコンポーネント初期化
        self.image_processor = ImageProcessor(self.config.model_dump())
        self.robust_analyzer = RobustImageAnalyzer(self.config.model_dump())
        self.context_detector = ContextDetector()
        self.ai_message_generator = AIInitiativeMessageGenerator(core_app)  # キャラクター対応版
        self.error_manager = ChatHandlerErrorManager()


    async def handle_unified_chat(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """
        統一チャットリクエストの処理（画像対応拡張版）
        
        Args:
            request: 統一チャットリクエスト
            
        Returns:
            UnifiedChatResponse: 処理結果
        """
        request_info = f"user_id={request.user_id}, session_id={request.session_id}, has_files={bool(request.files)}"
        
        try:
            self.logger.debug(f"Unified chat request: {request_info}")
            
            # ユーザーの存在を確保
            self.core_app.ensure_user(request.user_id)
            
            # 画像処理フロー
            if request.files and len(request.files) > 0:
                return await self._handle_image_chat(request)
            else:
                return await self._handle_text_only_chat(request)
        
        except Exception as e:
            # 統一エラーハンドリング
            error_response = self.error_manager.handle_chat_error(e, request_info)
            return UnifiedChatResponse(
                status=error_response["status"],
                message=error_response["message"],
                session_id=request.session_id,
                metadata=error_response.get("error_details")
            )
    
    async def _handle_image_chat(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """
        画像付きチャットの処理
        
        Args:
            request: リクエスト
            
        Returns:
            UnifiedChatResponse: 処理結果
        """
        # 1. コンテキスト判定
        context = self.context_detector.determine_image_context(request)
        self.logger.info(f"画像コンテキスト: {context.source_type}")
        
        # 2. 堅牢な画像分析
        image_urls = [file["url"] for file in request.files]
        analysis_result = await self.robust_analyzer.robust_image_analysis(image_urls)
        self.logger.info(
            f"画像分析完了: カテゴリ={analysis_result.category}, 枚数={len(request.files)}, "

        )
        
        # 3. コンテキスト別処理
        if context.source_type in ["notification", "desktop_monitoring"]:
            return await self._handle_ai_initiative_conversation(request, analysis_result, context)
        else:
            return await self._handle_normal_image_chat(request, analysis_result)
    
    async def _handle_ai_initiative_conversation(
        self,
        request: UnifiedChatRequest,
        analysis_result: ImageAnalysisResult,
        context: ImageContext
    ) -> UnifiedChatResponse:
        """
        AI主導会話の処理
        
        Args:
            request: リクエスト
            analysis_result: 画像分析結果
            context: コンテキスト
            
        Returns:
            UnifiedChatResponse: 処理結果
        """
        # 1. キャラクター対応AI主導メッセージ生成
        ai_message = await self.ai_message_generator.generate_ai_initiative_message(
            analysis_result, context, request.system_prompt, request.user_id
        )
        
        # 2. ユーザーメッセージがある場合は会話として処理
        cleaned_user_message = self.context_detector.clean_message_tags(request.message or "")
        
        if cleaned_user_message and cleaned_user_message.strip():
            # 会話として処理
            conversation = [
                {"role": "assistant", "content": ai_message},
                {"role": "user", "content": cleaned_user_message},
            ]
            
            # MemOSで応答生成（AI主導メッセージを文脈として追加）
            enhanced_system_prompt = self._create_enhanced_system_prompt(
                request.system_prompt, ai_message, analysis_result, context
            )
            
            ai_response = await self.core_app.memos_chat(
                query=cleaned_user_message,
                user_id=request.user_id,
                system_prompt=enhanced_system_prompt
            )
            
            # 完全な会話として記憶保存
            full_conversation = conversation + [{"role": "assistant", "content": ai_response}]
            asyncio.create_task(self._save_conversation_async(full_conversation, request.user_id))
            
            return UnifiedChatResponse(
                status="success",
                message="AI主導会話が完了しました",
                response=ai_response,
                context_id=request.context_id,
                session_id=request.session_id,
                response_length=len(ai_response),
                metadata={"ai_initiative": ai_message, "image_analysis": analysis_result.__dict__}
            )
        else:
            # AI主導メッセージのみ
            asyncio.create_task(self._save_conversation_async(
                [{"role": "assistant", "content": ai_message}], request.user_id
            ))
            
            return UnifiedChatResponse(
                status="success",
                message="AI主導メッセージを生成しました",
                response=ai_message,
                context_id=request.context_id,
                session_id=request.session_id,
                response_length=len(ai_message),
                metadata={"waiting_for_user_response": True, "image_analysis": analysis_result.__dict__}
            )
    
    async def _handle_normal_image_chat(
        self,
        request: UnifiedChatRequest,
        analysis_result: ImageAnalysisResult
    ) -> UnifiedChatResponse:
        """
        通常の画像付きチャット処理
        
        Args:
            request: リクエスト
            analysis_result: 画像分析結果
            
        Returns:
            UnifiedChatResponse: 処理結果
        """
        # 画像説明をシステムメッセージとして構築
        image_description = f"[画像が共有されました: {analysis_result.description}]"
        image_description += f" (分類: {analysis_result.category}/{analysis_result.mood}/{analysis_result.time})"
        
        # 画像情報を含むメッセージでMemOSチャット
        enhanced_query = f"{image_description}\\n\\nユーザー: {request.message or ''}"
        
        response = await self.core_app.memos_chat(
            query=enhanced_query,
            user_id=request.user_id,
            system_prompt=request.system_prompt
        )
        
        # 会話として記憶保存（既にmemos_chatで保存済みなので追加処理不要）
        
        return UnifiedChatResponse(
            status="success",
            message="画像付きチャットが完了しました",
            response=response,
            context_id=request.context_id,
            session_id=request.session_id,
            response_length=len(response),
            metadata={"image_analysis": analysis_result.__dict__}
        )
    
    async def _handle_text_only_chat(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """
        テキストのみのチャット処理（既存ロジック）
        
        Args:
            request: リクエスト
            
        Returns:
            UnifiedChatResponse: 処理結果
        """
        import uuid
        
        # コンテキストID生成（必要に応じて）
        context_id = request.context_id or str(uuid.uuid4())
        
        # MemOSに直接アクセス（非同期）
        response = await self.core_app.memos_chat(
            query=request.message,
            user_id=request.user_id,
            system_prompt=request.system_prompt
        )
        
        self.logger.debug(f"MemOS response received: {len(response)} characters")
        
        return UnifiedChatResponse(
            status="success",
            message="チャット処理が完了しました",
            response=response,
            context_id=context_id,
            session_id=request.session_id,
            response_length=len(response)
        )
    
    def _create_enhanced_system_prompt(
        self,
        original_prompt: Optional[str],
        ai_message: str,
        analysis_result: ImageAnalysisResult,
        context: ImageContext
    ) -> str:
        """
        拡張システムプロンプトの作成
        
        Args:
            original_prompt: 元のシステムプロンプト
            ai_message: AI主導メッセージ
            analysis_result: 画像分析結果
            context: コンテキスト
            
        Returns:
            str: 拡張されたシステムプロンプト
        """
        enhanced_parts = []
        
        if original_prompt:
            enhanced_parts.append(original_prompt)
        
        # コンテキスト情報を追加
        if context.source_type == "notification":
            enhanced_parts.append(f"前の文脈: {ai_message}")
            enhanced_parts.append("あなたは通知に関する画像を受け取り、それについてコメントしました。")
        elif context.source_type == "desktop_monitoring":
            enhanced_parts.append(f"前の文脈: {ai_message}")
            enhanced_parts.append("あなたはデスクトップの状況を見て独り言を言いました。")
        
        # 画像情報を追加
        enhanced_parts.append(f"画像情報: {analysis_result.description}")
        
        return "\\n\\n".join(enhanced_parts)
    
    async def _save_conversation_async(self, messages: List[Dict[str, str]], user_id: str) -> None:
        """
        会話の非同期記憶保存
        
        Args:
            messages: 保存するメッセージリスト
            user_id: ユーザーID
        """
        try:
            await asyncio.to_thread(self.core_app.mos.add, messages=messages, user_id=user_id)
            self.logger.info(f"会話を記憶保存: {len(messages)}メッセージ, user_id={user_id}")
        except Exception as e:
            self.logger.error(f"記憶保存に失敗: {e}")
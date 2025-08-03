"""
CocoroCore2 画像処理エラーハンドリング

堅牢な画像分析とフォールバック機能を提供します。
実装計画書のPhase 4に対応する実装です。
"""

import asyncio
import logging
from typing import List, Optional

from .image_processor import ImageProcessor
from .models import ImageAnalysisResult

logger = logging.getLogger(__name__)


class VisionAPIError(Exception):
    """Vision API関連のエラー"""
    pass


class ImageSizeError(Exception):
    """画像サイズ関連のエラー"""
    pass


class RobustImageAnalyzer:
    """画像分析システム（フォールバック処理削除版）"""
    
    def __init__(self, config: dict):
        self.config = config
        self.logger = logger
        self.primary_processor = ImageProcessor(config)
        
        # 設定値
        self.max_retries = config.get("image_analysis_max_retries", 2)
        self.retry_delay_seconds = config.get("image_analysis_retry_delay", 1.0)
        self.max_image_size = config.get("max_image_size", 5242880)  # 5MB
    
    async def robust_image_analysis(self, image_urls: List[str]) -> ImageAnalysisResult:
        """
        画像分析（エラー時は例外を発生）
        
        Args:
            image_urls: 画像URLのリスト
            
        Returns:
            ImageAnalysisResult: 分析結果
            
        Raises:
            VisionAPIError: 画像分析失敗時
            ImageSizeError: 画像サイズエラー時
        """
        if not image_urls:
            raise VisionAPIError("画像URLが提供されていません")
        
        # 画像サイズ検証
        await self._validate_image_sizes(image_urls)
        
        # メイン分析の試行
        return await self._analyze_with_retries(image_urls)
    
    async def _analyze_with_retries(self, image_urls: List[str]) -> ImageAnalysisResult:
        """
        リトライ付きの画像分析
        
        Args:
            image_urls: 画像URLのリスト
            
        Returns:
            ImageAnalysisResult: 分析結果
            
        Raises:
            VisionAPIError: Vision API関連のエラー
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # リトライの場合は少し待機
                    await asyncio.sleep(self.retry_delay_seconds * attempt)
                    self.logger.info(f"画像分析リトライ {attempt}/{self.max_retries}")
                
                result = await self.primary_processor.analyze_image(image_urls)
                return result
            
            except Exception as e:
                last_error = e
                self.logger.warning(f"分析試行 {attempt + 1} 失敗: {e}")
                
                # 最後の試行でない場合は続行
                if attempt < self.max_retries:
                    continue
                else:
                    break
        
        # すべての試行が失敗した場合
        raise VisionAPIError(f"画像分析が{self.max_retries + 1}回の試行で失敗: {last_error}")
    
    async def _validate_image_sizes(self, image_urls: List[str]):
        """
        画像サイズの検証
        
        Args:
            image_urls: 画像URLのリスト
            
        Raises:
            ImageSizeError: 画像サイズが制限を超えている場合
        """
        # data:スキームの簡易サイズチェック
        for i, url in enumerate(image_urls):
            if url.startswith("data:"):
                # Base64エンコードされたデータのサイズを推定
                # "data:image/jpeg;base64," の部分を除いてBase64データ部分のサイズを計算
                if ";base64," in url:
                    base64_data = url.split(";base64,", 1)[1]
                    # Base64は元データの約4/3倍のサイズになる
                    estimated_size = len(base64_data) * 3 // 4
                    
                    if estimated_size > self.max_image_size:
                        raise ImageSizeError(
                            f"画像{i+1}のサイズ({estimated_size}bytes)が制限({self.max_image_size}bytes)を超えています"
                        )


class ChatHandlerErrorManager:
    """チャットハンドラー用エラー管理"""
    
    def __init__(self):
        self.logger = logger
    
    def handle_chat_error(self, error: Exception, request_info: str) -> dict:
        """
        チャットエラーの統一処理
        
        Args:
            error: 発生したエラー
            request_info: リクエスト情報
            
        Returns:
            dict: エラーレスポンス用の辞書
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        self.logger.error(f"チャットエラー [{error_type}] {request_info}: {error_message}")
        
        # エラータイプに応じたユーザーフレンドリーなメッセージ
        if isinstance(error, VisionAPIError):
            user_message = "画像の分析で問題が発生しました。しばらく待ってから再度お試しください。"
        elif isinstance(error, ImageSizeError):
            user_message = "画像のサイズが大きすぎます。もう少し小さい画像でお試しください。"
        elif isinstance(error, asyncio.TimeoutError):
            user_message = "処理に時間がかかりすぎています。もう一度お試しください。"
        elif "connection" in error_message.lower() or "network" in error_message.lower():
            user_message = "ネットワークの問題が発生しました。接続を確認してお試しください。"
        elif "memory" in error_message.lower() or "mos" in error_message.lower():
            user_message = "記憶システムで問題が発生しました。管理者にお問い合わせください。"
        else:
            user_message = "申し訳ございません。一時的な問題が発生しました。もう一度お試しください。"
        
        return {
            "status": "error",
            "message": user_message,
            "error_details": {
                "type": error_type,
                "message": error_message,
                "request_info": request_info
            }
        }
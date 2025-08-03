"""
CocoroCore2 画像処理エンジン

マルチモーダルLLM（GPT-4o等）による画像分析機能を提供します。
CocoroCore（旧版）の実装をベースに、MemOS統合に最適化しています。
"""

import logging
import os
from typing import Dict, List, Optional

from .models import ImageAnalysisResult
# カスタム例外クラスを削除し、標準例外を使用

logger = logging.getLogger(__name__)


class ImageProcessor:
    """マルチモーダル画像処理エンジン"""
    
    def __init__(self, config: Dict):
        """
        初期化
        
        Args:
            config: CocoroAI設定辞書（characterList等を含む）
        """
        self.config = config
        self.logger = logger
        
        # 設定値の取得
        self.multimodal_enabled = config.get("multimodal_enabled", True)
        self.vision_model = config.get("vision_model", "gpt-4o")
        self.backup_vision_model = config.get("backup_vision_model", "gpt-4o-mini")
        self.max_image_size = config.get("max_image_size", 5242880)  # 5MB
        self.analysis_timeout_seconds = config.get("analysis_timeout_seconds", 30)
    
    async def analyze_image(self, image_urls: List[str]) -> ImageAnalysisResult:
        """
        画像の詳細分析（常に詳細モード）
        
        Args:
            image_urls: 画像URLのリスト
            
        Returns:
            ImageAnalysisResult: 分析結果
        """
        if not self.multimodal_enabled:
            self.logger.warning("マルチモーダル機能が無効になっています")
            raise Exception("画像分析に失敗しました")
        
        if not image_urls:
            self.logger.warning("画像URLが提供されていません")
            raise Exception("画像分析に失敗しました")
        
        try:
            import litellm
            
            # LLMクライアントの設定を取得
            api_key, model = self._get_llm_config()
            
            if not api_key:
                self.logger.warning("APIキーが設定されていないため、画像説明の生成をスキップします")
                raise Exception("画像分析に失敗しました")
            
            # プロンプト生成
            system_prompt, user_text = self._generate_prompts(len(image_urls))
            
            # メッセージコンテンツを構築
            user_content = []
            for image_url in image_urls:
                user_content.append({"type": "image_url", "image_url": {"url": image_url}})
            user_content.append({"type": "text", "text": user_text})
            
            # Vision APIで画像の説明を生成
            response = await litellm.acompletion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                api_key=api_key,
                temperature=0.3,
                timeout=self.analysis_timeout_seconds,
            )
            
            full_response = response.choices[0].message.content
            self.logger.info(f"画像説明を生成しました（{len(image_urls)}枚）: {full_response[:50]}...")
            
            # 応答を解析して構造化
            return self.parse_analysis_response(full_response)
            
        except Exception as e:
            self.logger.error(f"画像分析に失敗しました: {e}")
            # バックアップモデルで再試行
            try:
                raise Exception("プライマリモデルで画像分析に失敗しました")
            except Exception as backup_error:
                self.logger.error(f"バックアップモデルでの分析も失敗: {backup_error}")
                raise Exception("画像分析に失敗しました")
    

    
    def parse_analysis_response(self, response: str) -> ImageAnalysisResult:
        """
        分析結果の構造化解析
        
        Args:
            response: LLMからの応答テキスト
            
        Returns:
            ImageAnalysisResult: 構造化された分析結果
        """
        result = ImageAnalysisResult(
            description="",
            category="",
            mood="",
            time="",

        )
        
        if response is None:
            raise Exception("画像分析に失敗しました")
        
        lines = response.split('\\n')
        for line in lines:
            line = line.strip()
            if line.startswith('説明:'):
                result.description = line[3:].strip()
            elif line.startswith('分類:'):
                # メタデータを解析: [カテゴリ] / [雰囲気] / [時間帯]
                metadata_text = line[3:].strip()
                parts = [p.strip() for p in metadata_text.split('/')]
                if len(parts) >= 1:
                    result.category = parts[0]
                if len(parts) >= 2:
                    result.mood = parts[1]
                if len(parts) >= 3:
                    result.time = parts[2]
        
        # 説明が空の場合はフォールバック
        if not result.description:
            raise Exception("画像分析に失敗しました")
        
        return result
    
    def _get_llm_config(self) -> tuple[Optional[str], str]:
        """LLM設定を取得"""
        character_list = self.config.get("characterList", [])
        current_char_index = self.config.get("currentCharacterIndex", 0)
        
        if character_list and current_char_index < len(character_list):
            current_char = character_list[current_char_index]
            api_key = current_char.get("apiKey")
            model = current_char.get("llmModel", self.vision_model)
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            model = self.vision_model
        
        return api_key, model
    
    def _generate_prompts(self, image_count: int) -> tuple[str, str]:
        """画像数に応じたプロンプトを生成"""
        if image_count == 1:
            system_prompt = (
                "画像を客観的に分析し、以下の形式で応答してください：\\n\\n"
                "説明: [この画像の詳細で客観的な説明]\\n"
                "分類: [カテゴリ] / [雰囲気] / [時間帯]\\n\\n"
                "説明は簡潔かつ的確に、以下を含めてください：\\n"
                "- 画像の種類（写真/イラスト/スクリーンショット/図表など）\\n"
                "- 内容や被写体\\n"
                "- 色彩や特徴\\n"
                "- 文字情報があれば記載\\n"
                "例：\\n"
                "説明: 後楽園遊園地を描いたカラーイラスト。中央に白い観覧車と赤いゴンドラ、右側に青黄ストライプのメリーゴーラウンド。青空の下、来園者が散歩している平和な風景。\\n"
                "分類: 風景 / 楽しい / 昼\\n\\n"
                "分類の選択肢：\\n"
                "- カテゴリ: 風景/人物/食事/建物/画面（プログラム）/画面（SNS）/画面（ゲーム）/画面（買い物）/画面（鑑賞）/[その他任意の分類]\\n"
                "- 雰囲気: 明るい/楽しい/悲しい/静か/賑やか/[その他任意の分類]\\n"
                "- 時間帯: 朝/昼/夕方/夜/不明"
            )
            user_text = "この画像を客観的に説明してください。"
        else:
            system_prompt = (
                f"複数の画像（{image_count}枚）を客観的に分析し、以下の形式で応答してください：\\n\\n"
                "説明: [すべての画像の詳細で客観的な説明]\\n"
                "分類: [主要カテゴリ] / [全体的な雰囲気] / [時間帯]\\n\\n"
                "説明は簡潔かつ的確に、以下を含めてください：\\n"
                "- 各画像の種類（写真/イラスト/スクリーンショット/図表など）\\n"
                "- 内容や被写体\\n"
                "- 色彩や特徴\\n"
                "- 文字情報があれば記載\\n"
                "- 画像間の関連性があれば記載\\n"
                "例：\\n"
                "説明: 1枚目：後楽園遊園地を描いたカラーイラスト。中央に白い観覧車と赤いゴンドラ。2枚目：同じ遊園地の夜景写真。ライトアップされた観覧車が美しい。関連性：同じ遊園地の昼と夜の風景。\\n"
                "分類: 風景 / 楽しい / 昼夜\\n\\n"
                "分類の選択肢：\\n"
                "- カテゴリ: 風景/人物/食事/建物/画面（プログラム）/画面（SNS）/画面（ゲーム）/画面（買い物）/画面（鑑賞）/[その他任意の分類]\\n"
                "- 雰囲気: 明るい/楽しい/悲しい/静か/賑やか/[その他任意の分類]\\n"
                "- 時間帯: 朝/昼/夕方/夜/不明"
            )
            user_text = f"これら{image_count}枚の画像を客観的に説明してください。"
        
        return system_prompt, user_text
    

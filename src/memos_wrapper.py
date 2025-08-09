"""
MemOS OpenAI LLM ラッパー

新しいOpenAIモデル（gpt-4o, gpt-5, o1など）用に最適化。
サポートされないパラメータを除去し、最小限のパラメータセットでAPI呼び出しを行う。
"""

from collections.abc import Generator
import openai
import logging
from memos.llms.openai import OpenAILLM
from memos.types import MessageList

# CocoroCore2のログ設定を使用
logger = logging.getLogger(__name__)


class CocoroOpenAILLM(OpenAILLM):
    """CocoroCore2用のOpenAILLMラッパー
    
    新しいOpenAIモデル用に最適化されたシンプルなラッパー。
    サポートされないパラメータを除去し、model+messagesのみでAPI呼び出しを行う。
    """
    
    def __init__(self, config):
        """ラッパー初期化"""
        logger.info(f"[CocoroWrapper] Initializing wrapper for model: {config.model_name_or_path}")
        super().__init__(config)
    
    def generate(self, messages: MessageList) -> str:
        """generate()をオーバーライドし、新しいOpenAIモデル用に最適化"""
        logger.info(f"[CocoroWrapper] generate() called for model: {self.config.model_name_or_path}")
        
        # 新しいモデル用の最小限パラメータセット（APIのデフォルト値に依存）
        params = {
            "model": self.config.model_name_or_path,
            "messages": messages,
        }
        
        logger.info("[CocoroWrapper] Using minimal parameters (model + messages only)")
        
        # extra_bodyがある場合のみ追加
        if hasattr(self.config, 'extra_body') and self.config.extra_body:
            params["extra_body"] = self.config.extra_body
        
        # APIを呼び出し
        response = self.client.chat.completions.create(**params)
        logger.info(f"Response from OpenAI (via CocoroWrapper): {response.model_dump_json()}")
        
        response_content = response.choices[0].message.content
        
        if self.config.remove_think_prefix:
            from memos.llms.utils import remove_thinking_tags
            return remove_thinking_tags(response_content)
        else:
            return response_content
    
    def generate_stream(self, messages: MessageList, **kwargs) -> Generator[str, None, None]:
        """generate_stream()をオーバーライドし、新しいOpenAIモデル用に最適化"""
        logger.info(f"[CocoroWrapper] generate_stream() called for model: {self.config.model_name_or_path}")
        
        # 新しいモデル用の最小限パラメータセット（APIのデフォルト値に依存）
        params = {
            "model": self.config.model_name_or_path,
            "messages": messages,
            "stream": True,
        }
        
        logger.info("[CocoroWrapper] Using minimal stream parameters (model + messages + stream only)")
        
        # extra_bodyがある場合のみ追加
        if hasattr(self.config, 'extra_body') and self.config.extra_body:
            params["extra_body"] = self.config.extra_body
        
        # ストリーミングレスポンスを処理
        response = self.client.chat.completions.create(**params)
        
        reasoning_started = False
        
        for chunk in response:
            delta = chunk.choices[0].delta
            
            # reasoning_contentのサポート（Qwenなど）
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                if not reasoning_started and not self.config.remove_think_prefix:
                    yield "<think>"
                    reasoning_started = True
                yield delta.reasoning_content
            elif hasattr(delta, "content") and delta.content:
                if reasoning_started and not self.config.remove_think_prefix:
                    yield "</think>"
                    reasoning_started = False
                yield delta.content
        
        # <think>タグを閉じる
        if reasoning_started and not self.config.remove_think_prefix:
            yield "</think>"
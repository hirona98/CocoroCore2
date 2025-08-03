"""
CocoroCore2 API Models

FastAPI用のリクエスト・レスポンスモデル定義
CocoroDock互換性を保つためのデータ構造
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ========================================
# 基本モデル
# ========================================

class StandardResponse(BaseModel):
    """標準レスポンスモデル"""
    status: str = Field(description="処理状態（success/error）")
    message: str = Field(description="処理結果メッセージ")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")


class ErrorResponse(BaseModel):
    """エラーレスポンスモデル"""
    status: str = "error"
    message: str = Field(description="エラーメッセージ")
    error_code: Optional[str] = Field(None, description="エラーコード")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")


# ========================================
# チャット関連モデル（CocoroDock互換）
# ========================================

# CoreChatRequest は廃止されました - 統一API（UnifiedChatRequest）を使用してください


class SseData(BaseModel):
    """SSEデータモデル（CocoroDock SseData互換）"""
    type: Optional[str] = Field(None, description="データタイプ（content/memory/error）")
    content: Optional[str] = Field(None, description="コンテンツ")
    role: Optional[str] = Field(None, description="ロール（assistant/system）")
    session_id: Optional[str] = Field(None, description="セッションID")
    context_id: Optional[str] = Field(None, description="コンテキストID")
    action: Optional[str] = Field(None, description="アクション（saved/searched）")
    details: Optional[str] = Field(None, description="詳細情報")
    finished: Optional[bool] = Field(None, description="完了フラグ")


class ChatResponse(StandardResponse):
    """チャットレスポンスモデル"""
    context_id: Optional[str] = Field(None, description="コンテキストID")
    response_length: Optional[int] = Field(None, description="レスポンス文字数")


# ========================================
# MemOS純正API モデル
# ========================================

class MemOSChatRequest(BaseModel):
    """MemOS純正チャットリクエスト"""
    query: str = Field(description="質問・メッセージ")
    user_id: str = Field(description="ユーザーID")
    context: Optional[Dict[str, Any]] = Field(None, description="追加コンテキスト")


class MemOSChatResponse(BaseModel):
    """MemOS純正チャットレスポンス"""
    code: int = Field(200, description="ステータスコード")
    message: str = Field("Operation successful", description="処理メッセージ")
    data: str = Field(description="AIの応答")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")


class MemorySearchRequest(BaseModel):
    """記憶検索リクエスト"""
    user_id: str = Field(description="ユーザーID")
    query: str = Field(description="検索クエリ")
    limit: Optional[int] = Field(10, description="検索結果数上限")


class MemoryAddRequest(BaseModel):
    """記憶追加リクエスト"""
    user_id: str = Field(description="ユーザーID")
    content: str = Field(description="記憶内容")
    category: Optional[str] = Field(None, description="カテゴリ")
    context: Optional[Dict[str, Any]] = Field(None, description="コンテキスト情報")


class MemorySearchResponse(BaseModel):
    """記憶検索レスポンス"""
    code: int = Field(200, description="ステータスコード")
    message: str = Field("Search completed", description="処理メッセージ")
    data: Dict[str, Any] = Field(description="検索結果")
    total_results: int = Field(description="総結果数")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")


# ========================================
# システム制御モデル
# ========================================

class CoreControlRequest(BaseModel):
    """システム制御リクエスト（既存CocoroCore互換）"""
    command: str = Field(description="制御コマンド")
    params: Optional[Dict[str, Any]] = Field(None, description="コマンドパラメータ")
    reason: Optional[str] = Field(None, description="実行理由")


class HealthCheckResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(description="システム状態")
    startup_time: str = Field(description="起動時刻")
    active_sessions: int = Field(description="アクティブセッション数")


# ========================================
# 通知モデル
# ========================================

class CoreNotificationRequest(BaseModel):
    """通知リクエスト（既存CocoroCore互換）"""
    type: str = Field(description="通知タイプ")
    session_id: str = Field(description="セッションID")
    user_id: str = Field(description="ユーザーID")
    context_id: Optional[str] = Field(None, description="コンテキストID")
    text: str = Field(description="通知テキスト")
    metadata: Optional[Dict[str, Any]] = Field(None, description="メタデータ")


# ========================================
# MCP関連モデル
# ========================================

class McpToolRegistrationResponse(BaseModel):
    """MCPツール登録ログレスポンス"""
    status: str = Field(description="処理状態")
    message: str = Field(description="処理結果メッセージ")
    logs: List[str] = Field(description="登録ログ")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")


# ========================================
# セッション管理モデル
# ========================================

class SessionInfo(BaseModel):
    """セッション情報"""
    session_id: str = Field(description="セッションID")
    user_id: str = Field(description="ユーザーID")
    created_at: str = Field(description="作成日時")
    last_activity: str = Field(description="最終アクティビティ")
    request_count: int = Field(description="リクエスト数")
    is_active: bool = Field(description="アクティブ状態")


class SessionStatistics(BaseModel):
    """セッション統計情報"""
    active_sessions: int = Field(description="アクティブセッション数")
    total_users: int = Field(description="総ユーザー数")
    total_requests: int = Field(description="総リクエスト数")
    expired_sessions: int = Field(description="期限切れセッション数")
    max_sessions: int = Field(description="最大セッション数")
    timeout_seconds: int = Field(description="タイムアウト秒数")


# ========================================
# ユーザー管理モデル
# ========================================

class UserInfo(BaseModel):
    """ユーザー情報"""
    user_id: str = Field(description="ユーザーID")
    user_name: str = Field(description="ユーザー名")
    role: str = Field(description="ユーザーロール")
    created: bool = Field(description="作成済みフラグ")


class UserStatistics(BaseModel):
    """ユーザー統計情報"""
    user_id: str = Field(description="ユーザーID")
    total_memories: int = Field(description="総記憶数")
    textual_memories: int = Field(description="テキスト記憶数")
    activation_memories: int = Field(description="アクティベーション記憶数")
    parametric_memories: int = Field(description="パラメトリック記憶数")


# ========================================
# 統一API モデル（新設計）
# ========================================

class UnifiedChatRequest(BaseModel):
    """統一チャットリクエスト（CocoroDock→CocoroCore2）"""
    user_id: str = Field(description="ユーザーID（固定値）")
    session_id: str = Field(description="セッションID（セッション管理用）")
    message: str = Field(description="メッセージテキスト")
    character_name: Optional[str] = Field(None, description="キャラクター名")
    system_prompt: Optional[str] = Field(None, description="システムプロンプト")
    context_id: Optional[str] = Field(None, description="コンテキストID")
    files: Optional[List[Dict[str, Any]]] = Field(None, description="添付ファイル")
    metadata: Optional[Dict[str, Any]] = Field(None, description="メタデータ")


class UnifiedChatResponse(BaseModel):
    """統一チャットレスポンス"""
    status: str = Field(description="処理状態（success/error）")
    message: str = Field(description="処理結果メッセージ")
    response: Optional[str] = Field(None, description="AIの応答")
    context_id: Optional[str] = Field(None, description="新しいコンテキストID")
    session_id: Optional[str] = Field(None, description="セッションID")
    response_length: Optional[int] = Field(None, description="レスポンス文字数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加メタデータ（画像分析結果等）")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")

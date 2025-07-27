"""
CocoroCore2 API Endpoints

FastAPIルーター定義とエンドポイント実装
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..app import get_app_instance, get_session_manager
from ..core_app import CocoroCore2App
from ..core.session_manager import SessionManager
from .legacy_adapter import LegacyAPIAdapter
from .models import (
    CoreChatRequest, CoreControlRequest, CoreNotificationRequest,
    HealthCheckResponse, McpToolRegistrationResponse,
    MemOSChatRequest, MemOSChatResponse,
    MemoryAddRequest, MemorySearchRequest, MemorySearchResponse,
    SessionStatistics, UserStatistics, StandardResponse
)


# ルーター作成
router = APIRouter()

# ロガー
logger = logging.getLogger(__name__)


def get_legacy_adapter(
    core_app: CocoroCore2App = Depends(get_app_instance),
    session_manager: SessionManager = Depends(get_session_manager)
) -> LegacyAPIAdapter:
    """互換性アダプターを取得"""
    return LegacyAPIAdapter(core_app, session_manager)


# ========================================
# 互換性エンドポイント（CocoroDock向け）
# ========================================

@router.post("/chat")
async def legacy_chat(
    request: CoreChatRequest,
    adapter: LegacyAPIAdapter = Depends(get_legacy_adapter)
):
    """既存/chatエンドポイント - 通常のRESTレスポンス"""
    try:
        logger.debug(f"Received chat request: {request}")
        return await adapter.handle_legacy_chat_rest(request)
    except Exception as e:
        logger.error(f"Legacy chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"チャット処理エラー: {str(e)}")


# SSEテストエンドポイントは削除（RESTに移行のため）


@router.get("/health", response_model=HealthCheckResponse)
async def legacy_health(
    adapter: LegacyAPIAdapter = Depends(get_legacy_adapter)
):
    """既存/healthエンドポイント - ヘルスチェック"""
    try:
        return await adapter.handle_legacy_health()
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=f"ヘルスチェックエラー: {str(e)}")


@router.post("/api/control")
async def legacy_control(
    request: CoreControlRequest,
    adapter: LegacyAPIAdapter = Depends(get_legacy_adapter)
):
    """既存/api/controlエンドポイント - システム制御"""
    try:
        result = await adapter.handle_legacy_control(request)
        return result
    except Exception as e:
        logger.error(f"Control command error: {e}")
        raise HTTPException(status_code=500, detail=f"制御コマンドエラー: {str(e)}")


@router.get("/api/mcp/tool-registration-log", response_model=McpToolRegistrationResponse)
async def get_mcp_tool_registration_log():
    """MCPツール登録ログ取得"""
    try:
        # 現在はMCP実装されていないため、空のログを返す
        return McpToolRegistrationResponse(
            status="success",
            message="MCPは現在実装されていません",
            logs=[]
        )
    except Exception as e:
        logger.error(f"MCP tool registration log error: {e}")
        raise HTTPException(status_code=500, detail=f"MCPログ取得エラー: {str(e)}")


# ========================================
# MemOS純正エンドポイント
# ========================================

@router.post("/api/memos/chat", response_model=MemOSChatResponse)
async def memos_chat(
    request: MemOSChatRequest,
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """MemOS純正チャットエンドポイント - 非ストリーミング"""
    try:
        # システムプロンプトを設定（contextに含まれていれば使用）
        system_prompt = None
        if request.context and "system_prompt" in request.context:
            system_prompt = request.context["system_prompt"]
        
        # MemOSから直接レスポンス取得
        response = core_app.memos_chat(
            query=request.query,
            user_id=request.user_id,
            context=request.context,
            system_prompt=system_prompt
        )
        
        return MemOSChatResponse(
            code=200,
            message="Operation successful",
            data=response
        )
    except Exception as e:
        logger.error(f"MemOS chat error: {e}")
        raise HTTPException(status_code=500, detail=f"MemOSチャットエラー: {str(e)}")


@router.post("/api/memory/search", response_model=MemorySearchResponse)
async def search_memory(
    request: MemorySearchRequest,
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """記憶検索エンドポイント"""
    try:
        # MemOSから記憶検索
        search_result = core_app.search_memory(
            query=request.query,
            user_id=request.user_id
        )
        
        # 結果数を計算
        total_results = 0
        if "text_mem" in search_result:
            for cube in search_result["text_mem"]:
                if "memories" in cube:
                    total_results += len(cube["memories"])
        
        return MemorySearchResponse(
            code=200,
            message="Search completed",
            data=search_result,
            total_results=total_results
        )
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        raise HTTPException(status_code=500, detail=f"記憶検索エラー: {str(e)}")


@router.post("/api/memory/add", response_model=StandardResponse)
async def add_memory(
    request: MemoryAddRequest,
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """記憶追加エンドポイント"""
    try:
        # MemOSに記憶追加
        context = request.context or {}
        if request.category:
            context["category"] = request.category
        
        core_app.add_memory(
            content=request.content,
            user_id=request.user_id,
            **context
        )
        
        return StandardResponse(
            status="success",
            message="記憶を追加しました"
        )
    except Exception as e:
        logger.error(f"Memory add error: {e}")
        raise HTTPException(status_code=500, detail=f"記憶追加エラー: {str(e)}")


@router.delete("/api/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    user_id: str,
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """記憶削除エンドポイント"""
    try:
        # MemOSには直接的な記憶削除APIがないため、現在は未実装
        logger.warning(f"Memory deletion requested but not implemented: {memory_id}")
        
        return StandardResponse(
            status="error",
            message="記憶削除機能は現在実装されていません"
        )
    except Exception as e:
        logger.error(f"Memory delete error: {e}")
        raise HTTPException(status_code=500, detail=f"記憶削除エラー: {str(e)}")


# ========================================
# 管理エンドポイント
# ========================================

@router.get("/api/sessions/statistics", response_model=SessionStatistics)
async def get_session_statistics(
    session_manager: SessionManager = Depends(get_session_manager)
):
    """セッション統計取得"""
    try:
        stats = session_manager.get_session_statistics()
        return SessionStatistics(**stats)
    except Exception as e:
        logger.error(f"Session statistics error: {e}")
        raise HTTPException(status_code=500, detail=f"セッション統計取得エラー: {str(e)}")


@router.get("/api/users/{user_id}/statistics", response_model=UserStatistics)
async def get_user_statistics(
    user_id: str,
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """ユーザー統計取得"""
    try:
        # MemOSからユーザーの記憶情報を取得
        memories = core_app.get_user_memories(user_id)
        
        # 統計情報を計算
        textual_memories = 0
        if "text_mem" in memories:
            for cube in memories["text_mem"]:
                if "memories" in cube:
                    textual_memories += len(cube["memories"])
        
        activation_memories = len(memories.get("act_mem", []))
        parametric_memories = len(memories.get("para_mem", []))
        total_memories = textual_memories + activation_memories + parametric_memories
        
        return UserStatistics(
            user_id=user_id,
            total_memories=total_memories,
            textual_memories=textual_memories,
            activation_memories=activation_memories,
            parametric_memories=parametric_memories
        )
    except Exception as e:
        logger.error(f"User statistics error: {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー統計取得エラー: {str(e)}")


@router.get("/api/users")
async def list_users(
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """ユーザーリスト取得"""
    try:
        users = core_app.mos.list_users()
        return {
            "status": "success",
            "message": f"{len(users)}名のユーザーを取得しました",
            "data": users
        }
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(status_code=500, detail=f"ユーザーリスト取得エラー: {str(e)}")


@router.post("/api/users/{user_id}")
async def create_user(
    user_id: str,
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """ユーザー作成"""
    try:
        # ユーザーの存在を確保（存在しない場合は作成）
        core_app.ensure_user(user_id)
        
        return StandardResponse(
            status="success",
            message=f"ユーザー {user_id} を作成しました"
        )
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(status_code=500, detail=f"ユーザー作成エラー: {str(e)}")


# ========================================
# 通知エンドポイント（互換性）
# ========================================

@router.post("/api/notification")
async def send_notification(
    request: CoreNotificationRequest,
    adapter: LegacyAPIAdapter = Depends(get_legacy_adapter)
):
    """通知送信エンドポイント"""
    try:
        result = await adapter.handle_legacy_notification(request)
        return result
    except Exception as e:
        logger.error(f"Notification error: {e}")
        raise HTTPException(status_code=500, detail=f"通知送信エラー: {str(e)}")


# ========================================
# 開発・デバッグ用エンドポイント
# ========================================

@router.get("/api/debug/app-status")
async def get_app_status(
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """アプリケーション状態取得（デバッグ用）"""
    try:
        status = core_app.get_app_status()
        return status
    except Exception as e:
        logger.error(f"App status error: {e}")
        raise HTTPException(status_code=500, detail=f"アプリケーション状態取得エラー: {str(e)}")


@router.get("/api/debug/config")
async def get_config(
    core_app: CocoroCore2App = Depends(get_app_instance)
):
    """設定情報取得（デバッグ用）"""
    try:
        # 機密情報を除外した設定情報を返す
        config_dict = core_app.config.dict()
        
        # API キー等の機密情報をマスク
        if "mos_config" in config_dict:
            if "chat_model" in config_dict["mos_config"]:
                if "config" in config_dict["mos_config"]["chat_model"]:
                    if "api_key" in config_dict["mos_config"]["chat_model"]["config"]:
                        config_dict["mos_config"]["chat_model"]["config"]["api_key"] = "***MASKED***"
        
        return {
            "status": "success",
            "message": "設定情報を取得しました",
            "data": config_dict
        }
    except Exception as e:
        logger.error(f"Config get error: {e}")
        raise HTTPException(status_code=500, detail=f"設定取得エラー: {str(e)}")
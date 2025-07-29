"""
CocoroCore2 FastAPI Application

MemOS統合による統一WebAPIサーバー
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import CocoroCore2Config
from .core_app import CocoroCore2App
from .core.session_manager import SessionManager


# アプリケーションインスタンス（グローバル）
app_instance: CocoroCore2App = None
session_manager: SessionManager = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """アプリケーションライフサイクル管理"""
    global app_instance, session_manager
    
    logger = logging.getLogger(__name__)
    logger.info("Starting CocoroCore2 FastAPI application...")
    
    try:
        # 設定読み込み
        config = CocoroCore2Config.load()
        
        # コアアプリケーション初期化
        app_instance = CocoroCore2App(config)
        await app_instance.startup()
        
        # セッション管理初期化
        session_manager = SessionManager()
        await session_manager.start()
        
        logger.info("CocoroCore2 startup completed")
        
        yield
        
    finally:
        logger.info("Shutting down CocoroCore2...")
        
        # クリーンアップ
        if session_manager:
            await session_manager.stop()
        
        if app_instance:
            await app_instance.shutdown()
        
        logger.info("CocoroCore2 shutdown completed")


def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成"""
    
    # FastAPIアプリケーション作成
    app = FastAPI(
        title="CocoroCore2",
        description="CocoroAI Unified Backend with MemOS Integration",
        version="2.0.0",
        lifespan=lifespan,
    )
    
    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # エンドポイント登録
    from .api.endpoints import router
    app.include_router(router)
    
    # ルートエンドポイント
    @app.get("/")
    async def root():
        """ルートエンドポイント"""
        if app_instance:
            status = app_instance.get_app_status()
            return {
                "message": "CocoroCore2 - MemOS Unified Backend",
                "version": "2.0.0",
                "status": status
            }
        return {
            "message": "CocoroCore2 - MemOS Unified Backend", 
            "version": "2.0.0",
            "status": "initializing"
        }
    
    return app


def get_app_instance() -> CocoroCore2App:
    """アプリケーションインスタンスを取得
    
    Returns:
        CocoroCore2App: アプリケーションインスタンス
        
    Raises:
        HTTPException: アプリケーションが初期化されていない場合
    """
    if app_instance is None:
        raise HTTPException(status_code=503, detail="アプリケーションが初期化されていません")
    return app_instance


def get_session_manager() -> SessionManager:
    """セッション管理インスタンスを取得
    
    Returns:
        SessionManager: セッション管理インスタンス
        
    Raises:
        HTTPException: セッション管理が初期化されていない場合
    """
    if session_manager is None:
        raise HTTPException(status_code=503, detail="セッション管理が初期化されていません")
    return session_manager


# FastAPIアプリケーション作成
app = create_app()
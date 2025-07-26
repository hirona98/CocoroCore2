"""
CocoroCore2 Main Entry Point

MemOS統合 CocoroAI バックエンドサーバー
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

import uvicorn

from .app import app
from .config import CocoroCore2Config, parse_args, ConfigurationError


# ログ設定
def setup_logging(config: CocoroCore2Config):
    """ログ設定を初期化"""
    
    # ログディレクトリ作成
    log_path = Path(config.logging.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ログレベル設定
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    
    # ログフォーマット
    formatter = logging.Formatter(config.logging.format)
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラー
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            config.logging.file,
            maxBytes=config.logging.max_size_mb * 1024 * 1024,
            backupCount=config.logging.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"ファイルロガーの設定に失敗しました: {e}")
    
    # uvicornロガーレベル調整
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# グローバル終了フラグ
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """シグナルハンドラー"""
    logger = logging.getLogger(__name__)
    logger.info(f"Signal {signum} received. Shutting down gracefully...")
    shutdown_event.set()


def setup_signal_handlers():
    """シグナルハンドラーを設定"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windowsの場合はSIGBREAKも処理
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)


async def run_server(config: CocoroCore2Config):
    """FastAPIサーバーを起動"""
    logger = logging.getLogger(__name__)
    
    # uvicorn設定
    uvicorn_config = uvicorn.Config(
        app=app,
        host=config.server.host,
        port=config.server.port,
        log_level=config.logging.level.lower(),
        access_log=False,  # 独自のログ設定を使用
        reload=config.server.reload,
        workers=1,  # lifespanとの互換性のため常に1
    )
    
    # uvicornサーバー作成
    server = uvicorn.Server(uvicorn_config)
    
    # サーバータスク作成
    server_task = asyncio.create_task(server.serve())
    
    # 終了待機タスク作成
    shutdown_task = asyncio.create_task(shutdown_event.wait())
    
    try:
        logger.info(f"CocoroCore2 starting on {config.server.host}:{config.server.port}")
        
        # サーバー開始または終了シグナル待機
        done, pending = await asyncio.wait(
            [server_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        if shutdown_task in done:
            logger.info("Shutdown signal received. Stopping server...")
            
            # サーバーを優雅に停止
            server.should_exit = True
            await server.shutdown()
            
        # 残りのタスクをキャンセル
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("CocoroCore2 server stopped")


def check_environment():
    """実行環境をチェック"""
    logger = logging.getLogger(__name__)
    
    # Python バージョンチェック
    if sys.version_info < (3, 10):
        logger.error("Python 3.10以上が必要です")
        sys.exit(1)
    
    # 必要な環境変数チェック
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"以下の環境変数が設定されていません: {', '.join(missing_vars)}")
        logger.warning("MemOSの機能が制限される可能性があります")
    
    logger.info(f"Python {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")


def print_banner(config: CocoroCore2Config):
    """起動バナーを表示"""
    banner = f"""
┌─────────────────────────────────────────────────┐
│                CocoroCore2                      │
│         MemOS Unified Backend v{config.version:<8}      │
│                                                 │
│  Character: {config.character.name:<30}    │
│  Server:    {config.server.host}:{config.server.port:<25}     │
│  Memory:    MemOS Integration Enabled          │
│                                                 │
│  Ready for CocoroDock & CocoroShell            │
└─────────────────────────────────────────────────┘
"""
    print(banner)


async def main():
    """メイン実行関数"""
    try:
        # コマンドライン引数解析
        args = parse_args()
        
        # 設定読み込み
        try:
            if args.config_file:
                config = CocoroCore2Config.load(args.config_file, args.environment)
            else:
                config = CocoroCore2Config.load(environment=args.environment)
        except ConfigurationError as e:
            print(f"設定エラー: {e}")
            sys.exit(1)
        
        # ログ設定
        setup_logging(config)
        logger = logging.getLogger(__name__)
        
        # 環境チェック
        check_environment()
        
        # 起動バナー表示
        print_banner(config)
        
        # シグナルハンドラー設定
        setup_signal_handlers()
        
        # サーバー実行
        await run_server(config)
        
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


def sync_main():
    """同期メイン関数（Windows対応）"""
    if sys.platform == "win32":
        # Windowsでのイベントループポリシー設定
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # asyncio.run()を使用してメイン実行
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()
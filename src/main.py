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

# モジュールパスを追加（直接実行対応）
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

from src.app import app
from src.config import CocoroAIConfig, parse_args, ConfigurationError


# ログ設定
def setup_logging(config: CocoroAIConfig):
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
    
    # ログレベル設定
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logging.getLogger("neo4j").setLevel(logging.INFO)
    logging.getLogger("neo4j.io").setLevel(logging.INFO)
    logging.getLogger("neo4j.pool").setLevel(logging.INFO)
    logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

    logging.getLogger("httpcore.http11").setLevel(logging.INFO)
    logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("memos.llms.openai").setLevel(logging.WARNING)

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


def setup_api_keys_from_config(config: CocoroAIConfig):
    """設定ファイルからAPIキーを環境変数に設定"""
    try:
        # MemOS設定から OpenAI APIキーを取得
        from config import load_memos_config
        memos_config = load_memos_config()
        
        # chat_model の APIキー
        chat_model_config = memos_config.get("chat_model", {}).get("config", {})
        chat_api_key = chat_model_config.get("api_key", "")
        
        if chat_api_key and chat_api_key.startswith("sk-"):
            os.environ["OPENAI_API_KEY"] = chat_api_key
            return True
        
        # mem_reader の LLM APIキー
        mem_reader_llm_config = memos_config.get("mem_reader", {}).get("config", {}).get("llm", {}).get("config", {})
        mem_llm_api_key = mem_reader_llm_config.get("api_key", "")
        
        if mem_llm_api_key and mem_llm_api_key.startswith("sk-"):
            os.environ["OPENAI_API_KEY"] = mem_llm_api_key
            return True
        
        
    except Exception as e:
        pass
    
    return False


async def run_server(config: CocoroAIConfig):
    """FastAPIサーバーを起動"""
    logger = logging.getLogger(__name__)
    
    # uvicorn設定
    uvicorn_config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=config.cocoroCorePort,
        log_level=config.logging.level.lower(),
        access_log=False,  # 独自のログ設定を使用
        reload=False,
        workers=1,  # lifespanとの互換性のため常に1
    )
    
    # uvicornサーバー作成
    server = uvicorn.Server(uvicorn_config)
    
    # サーバータスク作成
    server_task = asyncio.create_task(server.serve())
    
    # 終了待機タスク作成
    shutdown_task = asyncio.create_task(shutdown_event.wait())
    
    try:
        logger.info(f"CocoroCore2 starting on 127.0.0.1:{config.cocoroCorePort}")
        
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


def check_environment(config: CocoroAIConfig):
    """実行環境をチェック"""
    logger = logging.getLogger(__name__)
    
    # Python バージョンチェック
    if sys.version_info < (3, 10):
        logger.error("Python 3.10以上が必要です")
        sys.exit(1)
    
    # 設定ファイルからAPIキーを設定
    if setup_api_keys_from_config(config):
        logger.info("設定ファイルからAPIキーを設定しました")
    else:
        logger.warning("設定ファイルにOpenAI APIキーが見つかりませんでした")
    
    logger.info(f"Python {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")


def print_banner(config: CocoroAIConfig):
    """起動バナーを表示"""
    banner = f"""
//////////////////////////////////////////////////////////

                     CocoroCore2
       CocoroAI Backend Version 2 MemOS Unified

    Ready for CocoroDock & CocoroShell 127.0.0.1:{config.cocoroCorePort:<25}
  ** ログ出力文字化け防止の為 -X utf8 オプション必須 **
       
//////////////////////////////////////////////////////////
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
                config = CocoroAIConfig.load(args.config_file, args.environment)
                print(f"設定ファイル読み込み: {args.config_file}")
            else:
                config = CocoroAIConfig.load(environment=args.environment)
                from src.config import find_config_file
                config_path = find_config_file(args.environment)
                print(f"設定ファイル読み込み: {config_path}")
        except ConfigurationError as e:
            print(f"設定エラー: {e}")
            sys.exit(1)
        
        # ログ設定
        setup_logging(config)
        logger = logging.getLogger(__name__)
        
        # 環境チェック
        check_environment(config)
        
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
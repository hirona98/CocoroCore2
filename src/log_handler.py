"""
CocoroDock用カスタムログハンドラー
"""

import logging
import json
import threading
import queue
from typing import Optional
import requests
from datetime import datetime


# グローバルログハンドラーインスタンス
_dock_log_handler_instance: Optional['CocoroDockLogHandler'] = None


def get_dock_log_handler() -> Optional['CocoroDockLogHandler']:
    """グローバルログハンドラーインスタンスを取得"""
    return _dock_log_handler_instance


def set_dock_log_handler(handler: Optional['CocoroDockLogHandler']):
    """グローバルログハンドラーインスタンスを設定"""
    global _dock_log_handler_instance
    _dock_log_handler_instance = handler


class CocoroDockLogHandler(logging.Handler):
    """
    CocoroDockにログメッセージを送信するカスタムハンドラー
    """

    def __init__(self, dock_url: str = "http://127.0.0.1:55600", component_name: str = "CocoroCore2"):
        super().__init__()
        self.dock_url = dock_url.rstrip("/")
        self.component_name = component_name
        self._enabled = False
        self._startup_buffer = []  # 起動時ログ用バッファ（最大500件）
        self._buffer_sent = False  # バッファ送信済みフラグ
        
        # スレッドセーフなキューと転送スレッド
        self._log_queue = queue.Queue()
        self._sender_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._session: Optional[requests.Session] = None
        
    def set_enabled(self, enabled: bool):
        """ログ送信の有効/無効を設定"""
        was_enabled = self._enabled
        self._enabled = enabled
        
        if enabled and self._sender_thread is None:
            # HTTPセッション初期化
            self._session = requests.Session()
            self._session.timeout = 2.0
            
            # 転送スレッド開始
            self._stop_event.clear()
            self._sender_thread = threading.Thread(target=self._sender_worker, daemon=True)
            self._sender_thread.start()
            
        elif not enabled and self._sender_thread is not None:
            # 転送スレッド停止
            self._stop_event.set()
            if self._sender_thread.is_alive():
                self._sender_thread.join(timeout=1.0)
            self._sender_thread = None
            
            # HTTPセッション閉じる
            if self._session is not None:
                try:
                    self._session.close()
                except Exception:
                    pass
                self._session = None
        
        # 新たに有効化された時、バッファ送信をキューに追加
        if enabled and not was_enabled and not self._buffer_sent:
            self._queue_buffered_logs()
            self._buffer_sent = True

    def emit(self, record: logging.LogRecord):
        """ログレコードを処理してCocoroDockに送信"""
        try:
            # HTTPライブラリのapi/logsリクエストログを除外（無限ループ防止）
            if ((record.name == "httpx" or record.name.startswith("urllib3")) and 
                "/api/logs" in record.getMessage()):
                return

            # ログメッセージを作成（400文字制限）
            formatted_message = self.format(record)
            if len(formatted_message) > 400:
                formatted_message = formatted_message[:397] + "..."
            
            log_message = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "component": self.component_name,
                "message": formatted_message
            }

            if not self._enabled or self._session is None:
                # ログ送信が無効の場合はバッファに保存（最大500件まで）
                if len(self._startup_buffer) < 500:
                    self._startup_buffer.append(log_message)
                return

            # 初回有効化時にバッファ内容をキューに追加
            if not self._buffer_sent:
                self._queue_buffered_logs()
                self._buffer_sent = True

            # 通常のリアルタイム送信（キューに追加）
            try:
                self._log_queue.put_nowait(log_message)
            except queue.Full:
                # キューが満杯の場合は古いメッセージを破棄
                pass

        except Exception:
            # ログハンドラー内でエラーが発生してもメイン処理をブロックしない
            # エラーログは出力しない（無限ループを防ぐため）
            pass

    def _sender_worker(self):
        """専用スレッドでログ送信を処理"""
        while not self._stop_event.is_set():
            try:
                # キューからログメッセージを取得（タイムアウト付き）
                log_message = self._log_queue.get(timeout=0.5)
                self._send_log_sync(log_message)
                self._log_queue.task_done()
            except queue.Empty:
                # タイムアウト時は継続
                continue
            except Exception:
                # エラーは無視（無限ループを防ぐため）
                continue
    
    def _send_log_sync(self, log_message: dict):
        """ログメッセージを同期的にCocoroDockに送信"""
        if self._session is None:
            return
        
        try:
            response = self._session.post(
                f"{self.dock_url}/api/logs",
                json=log_message
            )
            response.raise_for_status()
        except requests.exceptions.ConnectException:
            # CocoroDockが起動していない場合はサイレントに無視
            pass
        except requests.exceptions.Timeout:
            # タイムアウトの場合もサイレントに無視
            pass
        except Exception:
            # その他のエラーもサイレントに処理
            pass

    def _queue_buffered_logs(self):
        """バッファ内のログをキューに追加"""
        try:
            buffer_count = len(self._startup_buffer)
            
            # バッファ内のログを順次キューに追加
            for log_message in self._startup_buffer:
                try:
                    self._log_queue.put_nowait(log_message)
                except queue.Full:
                    break
            
            # セパレーターメッセージをキューに追加
            if buffer_count > 0:
                separator_message = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": "INFO",
                    "component": "SEPARATOR", 
                    "message": f"─── CocoroCore2 起動時ログ（{buffer_count}件）ここまで ───"
                }
                try:
                    self._log_queue.put_nowait(separator_message)
                except queue.Full:
                    pass
            
            # バッファをクリア
            self._startup_buffer.clear()
        except Exception:
            # エラーログは出力しない（無限ループを防ぐため）
            pass

    def close(self):
        """ハンドラーを閉じる"""
        self.set_enabled(False)
        super().close()
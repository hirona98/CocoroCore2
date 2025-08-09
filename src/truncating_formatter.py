"""
長いログメッセージを切り詰めるカスタムフォーマッター
"""

import logging
import copy


class TruncatingFormatter(logging.Formatter):
    """200文字を超えるメッセージを切り詰めるフォーマッター"""
    
    def __init__(self, *args, max_length=200, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_length = max_length
    
    def format(self, record):
        # レコードをコピーして元のレコードを変更しない
        record_copy = copy.copy(record)
        
        try:
            # httpxなどのログで引数フォーマットの問題を回避
            # メッセージを事前にフォーマット
            if record_copy.args:
                try:
                    formatted_msg = record_copy.msg % record_copy.args
                    record_copy.msg = formatted_msg
                    record_copy.args = ()
                except (TypeError, ValueError):
                    # フォーマットに失敗した場合は元のメッセージを使用
                    pass
            
            # メッセージを取得
            message = record_copy.getMessage()
            
            # メッセージが長すぎる場合は切り詰め
            if len(message) > self.max_length:
                record_copy.msg = message[:self.max_length] + "... (切り詰め)"
                record_copy.args = ()
            
            # 通常のフォーマット処理
            return super().format(record_copy)
            
        except Exception as e:
            # エラーが発生した場合は元のレコードをそのままフォーマット
            return super().format(record)
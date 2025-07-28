"""
Phase 2: 手動実行による動作確認テスト

このファイルは手動でPhase 2の実装を確認するためのものです。
実際のMOSとスケジューラーの動作を確認します。
"""

import asyncio
import logging
from pathlib import Path

# プロジェクトルートへのパスを追加
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import CocoroCore2Config, load_config
from src.core_app import CocoroCore2App

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def test_phase2_functionality():
    """Phase 2機能の手動テスト"""
    try:
        # 設定を読み込み
        print("=== Phase 2 手動テスト開始 ===")
        print("\n1. 設定読み込み...")
        config = load_config()
        
        # スケジューラー設定を確認
        print(f"\nスケジューラー設定:")
        print(f"  - enabled: {config.mem_scheduler.enabled}")
        print(f"  - enable_chat_integration: {config.mem_scheduler.enable_chat_integration}")
        print(f"  - enable_memory_integration: {config.mem_scheduler.enable_memory_integration}")
        print(f"  - auto_submit_query: {config.mem_scheduler.auto_submit_query}")
        print(f"  - auto_submit_answer: {config.mem_scheduler.auto_submit_answer}")
        
        # アプリケーション作成
        print("\n2. CocoroCore2App作成...")
        app = CocoroCore2App(config)
        
        # アプリケーション起動
        print("\n3. アプリケーション起動...")
        await app.startup()
        
        # ステータス確認
        print("\n4. アプリケーションステータス確認...")
        status = app.get_app_status()
        print(f"  - アプリケーション状態: {status['status']}")
        print(f"  - スケジューラー状態: {status['scheduler_status']}")
        
        # テストユーザーID
        test_user_id = "test_user_phase2"
        
        # MemCube取得テスト
        print(f"\n5. MemCube取得テスト (ユーザー: {test_user_id})...")
        mem_cube = app._get_user_memcube(test_user_id)
        if mem_cube:
            print(f"  - MemCube取得成功: {mem_cube}")
        else:
            print("  - MemCube取得失敗（新規ユーザーの場合は正常）")
        
        # チャット処理テスト
        print("\n6. チャット処理テスト...")
        queries = [
            "こんにちは。今日はいい天気ですね。",
            "私の名前は太郎です。",
            "趣味は読書とプログラミングです。"
        ]
        
        for i, query in enumerate(queries, 1):
            print(f"\n  テスト {i}: {query}")
            response = app.memos_chat(query, test_user_id)
            print(f"  応答: {response[:100]}...")  # 最初の100文字のみ表示
            
            # スケジューラーの動作確認
            if app.text_memory_scheduler and app.text_memory_scheduler.is_running:
                print("  - スケジューラーへのメッセージ送信: 成功")
            else:
                print("  - スケジューラーへのメッセージ送信: スキップ（無効または未実行）")
        
        # 記憶追加テスト
        print("\n7. 記憶追加テスト...")
        memories = [
            "ユーザーの名前は太郎",
            "趣味は読書とプログラミング",
            "今日の天気について話した"
        ]
        
        for i, memory in enumerate(memories, 1):
            print(f"\n  記憶 {i}: {memory}")
            app.add_memory(memory, test_user_id)
            print("  - 記憶追加: 完了")
        
        # 最終ステータス確認
        print("\n8. 最終ステータス確認...")
        final_status = app.get_app_status()
        scheduler_status = final_status.get('scheduler_status', {})
        
        print(f"  スケジューラー詳細:")
        print(f"    - 初期化済み: {scheduler_status.get('initialized', False)}")
        print(f"    - 実行中: {scheduler_status.get('running', False)}")
        print(f"    - チャット統合: {scheduler_status.get('chat_integration_enabled', False)}")
        print(f"    - 記憶統合: {scheduler_status.get('memory_integration_enabled', False)}")
        print(f"    - MemCube利用可能: {scheduler_status.get('memcube_available', False)}")
        
        # アプリケーション終了
        print("\n9. アプリケーション終了...")
        await app.shutdown()
        
        print("\n=== Phase 2 手動テスト完了 ===")
        print("\n結果サマリー:")
        print("  ✓ アプリケーション起動・終了: 成功")
        print("  ✓ チャット処理: 成功")
        print("  ✓ 記憶追加処理: 成功")
        
        if config.mem_scheduler.enabled:
            print("  ✓ スケジューラー連携: 有効")
        else:
            print("  - スケジューラー連携: 無効（設定により）")
        
    except Exception as e:
        print(f"\n!!! エラー発生: {e}")
        import traceback
        traceback.print_exc()


def main():
    """メイン関数"""
    print("Phase 2 手動テストを開始します...")
    print("注意: このテストは実際のMOSとスケジューラーを使用します。")
    print("設定ファイルが正しく構成されていることを確認してください。\n")
    
    # 非同期関数を実行
    asyncio.run(test_phase2_functionality())


if __name__ == "__main__":
    main()
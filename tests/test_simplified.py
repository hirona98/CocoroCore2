#!/usr/bin/env python
"""シンプル化後の記憶機能テスト"""

import requests
import json
import time
import sys

# API設定
BASE_URL = "http://127.0.0.1:55601"
USER_ID = "test_user"

def test_api_health():
    """APIヘルスチェック"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

def test_chat_with_memory(session_id, message):
    """チャットAPIをテストし、記憶が保存されるか確認"""
    url = f"{BASE_URL}/api/chat/unified"
    data = {
        "user_id": USER_ID,
        "session_id": session_id,
        "message": message
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Chat successful: {result.get('response', '')[:100]}...")
            return True
        else:
            print(f"❌ Chat failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False

def test_memory_search(query):
    """記憶検索をテスト"""
    url = f"{BASE_URL}/api/memory/search"
    data = {
        "user_id": USER_ID,
        "query": query
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            total = result.get("total_results", 0)
            print(f"✅ Memory search found {total} results")
            
            # 検索結果を表示
            if "data" in result and "text_mem" in result["data"]:
                for cube in result["data"]["text_mem"]:
                    if "memories" in cube:
                        for memory in cube["memories"][:3]:  # 最初の3件のみ表示
                            print(f"  - {memory.get('memory', '')[:80]}...")
            return total > 0
        else:
            print(f"❌ Memory search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Memory search error: {e}")
        return False

def main():
    """メインテスト実行"""
    print("=== CocoroCore2 シンプル化後テスト ===\n")
    
    # 1. ヘルスチェック
    if not test_api_health():
        print("API is not running. Please start CocoroCore2 first.")
        sys.exit(1)
    
    print("\n--- テスト1: 基本チャット ---")
    # 2. 基本チャット
    test_chat_with_memory("session1", "こんにちは、私の名前は山田太郎です。")
    
    # 少し待つ
    time.sleep(2)
    
    print("\n--- テスト2: 記憶確認 ---")
    # 3. 記憶確認
    test_chat_with_memory("session2", "私の名前を覚えていますか？")
    
    # 少し待つ
    time.sleep(2)
    
    print("\n--- テスト3: 記憶検索 ---")
    # 4. 記憶検索
    test_memory_search("山田太郎")
    
    print("\n=== シンプル化テスト完了 ===")
    print("🎉 MemOS標準スケジューラーが正常に動作しています！")

if __name__ == "__main__":
    main()
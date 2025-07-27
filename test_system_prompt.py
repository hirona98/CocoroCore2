"""
システムプロンプト機能のテストスクリプト
"""

import requests
import json

# テスト用のベースURL
BASE_URL = "http://localhost:55601"

def test_legacy_chat_with_system_prompt():
    """既存のCocoroDock互換APIでシステムプロンプトをテスト"""
    print("=== Legacy Chat API with System Prompt Test ===")
    
    # カスタムシステムプロンプトを含むリクエスト
    request_data = {
        "session_id": "test-session-001",
        "user_id": "test_user",
        "text": "こんにちは！自己紹介をお願いします。",
        "system_prompt_params": {
            "prompt": "あなたは「テスト太郎」という名前のロボットです。とても礼儀正しく、全ての返答に「でござる」を付けて話します。"
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=request_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_memos_chat_with_system_prompt():
    """MemOS純正APIでシステムプロンプトをテスト"""
    print("\n=== MemOS Chat API with System Prompt Test ===")
    
    # カスタムシステムプロンプトを含むリクエスト
    request_data = {
        "query": "こんにちは！自己紹介をお願いします。",
        "user_id": "test_user",
        "context": {
            "system_prompt": "あなたは「AIねこ」という名前の猫型ロボットです。語尾に「にゃん」を付けて話し、とてもフレンドリーです。"
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/memos/chat", json=request_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_default_character_prompt():
    """デフォルトキャラクターのプロンプトをテスト"""
    print("\n=== Default Character Prompt Test ===")
    
    # システムプロンプトを指定しないリクエスト（デフォルトが使われる）
    request_data = {
        "session_id": "test-session-002",
        "user_id": "test_user",
        "text": "こんにちは！自己紹介をお願いします。"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=request_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def check_health():
    """ヘルスチェック"""
    print("\n=== Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # ヘルスチェック
    check_health()
    
    # 各テストを実行
    test_legacy_chat_with_system_prompt()
    test_memos_chat_with_system_prompt()
    test_default_character_prompt()
    
    print("\n=== Test Complete ===")
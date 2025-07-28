"""
統一API専用テストスクリプト
"""

import requests
import json

# テスト用のベースURL
BASE_URL = "http://localhost:55601"

def check_health():
    """ヘルスチェック"""
    print("=== Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Character: {data.get('character', 'Unknown')}")
            print(f"Memory Enabled: {data.get('memory_enabled', False)}")
            print("Health check passed!")
        else:
            print("Health check failed!")
    except Exception as e:
        print(f"Health check error: {e}")

def test_unified_api_basic():
    """統一API基本テスト"""
    print("\n=== Unified API Basic Test ===")
    
    request_data = {
        "user_id": "test_user",
        "session_id": "test_session_001",
        "message": "統一APIのテストです。あなたの名前を教えてください。",
        "character_name": "ココロ"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/chat/unified", json=request_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Response: {data.get('response', 'No response')}")
            print(f"Context ID: {data.get('context_id')}")
            print(f"Response Length: {data.get('response_length')}")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_unified_api_with_system_prompt():
    """統一API（システムプロンプト指定）テスト"""
    print("\n=== Unified API with System Prompt Test ===")
    
    request_data = {
        "user_id": "test_user",
        "session_id": "test_session_002", 
        "message": "こんにちは！自己紹介をお願いします。",
        "character_name": "テスト太郎",
        "system_prompt": "あなたは「テスト太郎」という名前の関西弁で話すAIです。語尾に「やで」「やねん」を付けて、親しみやすく話してください。",
        "metadata": {
            "source": "test_script",
            "test_type": "system_prompt"
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/chat/unified", json=request_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status')}")
            print(f"Response: {data.get('response', 'No response')}")
            print(f"Context ID: {data.get('context_id')}")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_unified_api_session_continuity():
    """統一API（セッション継続）テスト"""
    print("\n=== Unified API Session Continuity Test ===")
    
    session_id = "test_session_continuity"
    
    # 最初のメッセージ
    print("--- First Message ---")
    request1 = {
        "user_id": "test_user",
        "session_id": session_id,
        "message": "私の名前は田中です。覚えておいてください。",
        "character_name": "ココロ"
    }
    
    try:
        response1 = requests.post(f"{BASE_URL}/api/chat/unified", json=request1)
        print(f"Status Code: {response1.status_code}")
        
        if response1.status_code == 200:
            data1 = response1.json()
            print(f"Response: {data1.get('response', 'No response')}")
            context_id = data1.get('context_id')
            
            # 2番目のメッセージ（記憶テスト）
            print("\n--- Second Message (Memory Test) ---")
            request2 = {
                "user_id": "test_user",
                "session_id": session_id,
                "message": "私の名前を覚えていますか？",
                "character_name": "ココロ",
                "context_id": context_id
            }
            
            response2 = requests.post(f"{BASE_URL}/api/chat/unified", json=request2)
            print(f"Status Code: {response2.status_code}")
            
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"Response: {data2.get('response', 'No response')}")
            else:
                print(f"Error Response: {response2.text}")
        else:
            print(f"Error Response: {response1.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("統一API専用テスト開始")
    
    # ヘルスチェック
    check_health()
    
    # 各テスト実行
    test_unified_api_basic()
    test_unified_api_with_system_prompt()
    test_unified_api_session_continuity()
    
    print("\n=== Test Complete ===")
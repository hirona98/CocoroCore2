# CocoroCore2 統一API仕様

CocoroCore2の新しい統一APIは、CocoroDockとCocoroCore2間の通信を最適化し、MemOSの機能を直接活用できるよう設計されています。

## 概要

### 従来の問題点
- レガシーAPIでは`session_id`が`user_id`として誤用されていた
- セッション管理が正しく機能していなかった
- MemOSの高度な機能にアクセスできなかった

### 新しい統一APIの利点
- `user_id`を固定値として使用（デスクトップマスコット前提）
- `session_id`を正しくセッション管理に使用
- システムプロンプトの直接指定が可能
- MemOSの機能を直接活用

## API エンドポイント

### `/api/chat/unified` (POST)

新しい統一チャットエンドポイント

#### リクエスト

```json
{
  "user_id": "user",                    // ユーザーID（固定値）
  "session_id": "dock_20241127_abc123", // セッションID（セッション管理用）
  "message": "こんにちは！",             // メッセージテキスト
  "character_name": "ココロ",            // キャラクター名（オプション）
  "system_prompt": "あなたは...",        // システムプロンプト（オプション）
  "context_id": "context_123",          // コンテキストID（オプション）
  "files": [                            // 添付ファイル（オプション）
    {
      "type": "image",
      "url": "data:image/png;base64,..."
    }
  ],
  "metadata": {                         // メタデータ（オプション）
    "source": "CocoroDock",
    "timestamp": "2024-11-27T12:00:00Z"
  }
}
```

#### レスポンス

```json
{
  "status": "success",                  // 処理状態（success/error）
  "message": "チャット処理が完了しました", // 処理結果メッセージ
  "response": "こんにちは！...",         // AIの応答
  "context_id": "context_124",          // 新しいコンテキストID
  "session_id": "dock_20241127_abc123", // セッションID
  "response_length": 45,                // レスポンス文字数
  "timestamp": "2024-11-27T12:00:01Z"   // タイムスタンプ
}
```

## CocoroDock側の実装

### 新しいモデル

```csharp
public class UnifiedChatRequest
{
    public string user_id { get; set; } = string.Empty;
    public string session_id { get; set; } = string.Empty;
    public string message { get; set; } = string.Empty;
    public string? character_name { get; set; }
    public string? system_prompt { get; set; }
    public string? context_id { get; set; }
    public List<Dictionary<string, object>>? files { get; set; }
    public Dictionary<string, object>? metadata { get; set; }
}

public class UnifiedChatResponse
{
    public string status { get; set; } = string.Empty;
    public string message { get; set; } = string.Empty;
    public string? response { get; set; }
    public string? context_id { get; set; }
    public string? session_id { get; set; }
    public int? response_length { get; set; }
    public DateTime timestamp { get; set; }
}
```

### 使用例

```csharp
// 統一APIを使用したチャット送信
public async Task SendChatToCoreUnifiedAsync(string message, string? characterName = null)
{
    var currentCharacter = GetCurrentCharacterSettings();
    
    var request = new UnifiedChatRequest
    {
        user_id = "user",                 // 固定値
        session_id = _currentSessionId,   // セッション管理用
        message = message,
        character_name = characterName ?? currentCharacter?.modelName,
        system_prompt = currentCharacter?.systemPrompt,  // 直接指定
        context_id = _currentContextId,
        metadata = new Dictionary<string, object>
        {
            { "source", "CocoroDock" }
        }
    };
    
    var response = await _coreClient.SendUnifiedChatMessageAsync(request);
    
    // コンテキストIDを更新
    _currentContextId = response.context_id;
    
    // AI応答を処理
    if (!string.IsNullOrEmpty(response.response))
    {
        // UIに表示
        DisplayAIResponse(response.response);
    }
}
```

## 設計原則

### ユーザーID管理
- **固定値**: デスクトップマスコットは1ユーザー前提
- **永続性**: PCを再起動しても同じユーザーとして認識
- **記憶継続**: 過去の会話や学習内容を維持

### セッション管理
- **一時的**: 起動毎または会話毎に生成
- **識別用**: 同じユーザーの異なるセッションを区別
- **タイムアウト**: 非アクティブ時間に応じて自動削除

### システムプロンプト
- **直接指定**: レガシーAPIの複雑な変換を廃止
- **キャラクター連動**: 設定ファイルから自動取得
- **デフォルト対応**: 未指定時はキャラクター別デフォルトを使用

## 移行ガイド

### 段階的移行
1. 新統一APIを並行実装
2. CocoroDockで新APIをテスト
3. 安定確認後、新API優先に切り替え
4. レガシーAPIの段階的廃止

### 互換性
- 既存のレガシーAPIは当面維持
- 新APIと並行して動作
- 設定で切り替え可能（将来実装）

## テスト方法

```bash
# テストスクリプト実行
cd CocoroCore2
python test_system_prompt.py
```

テストでは以下が確認されます：
- 統一APIの基本動作
- システムプロンプト指定
- デフォルトプロンプト動作
- エラーハンドリング

## 今後の拡張

### 予定している機能
- ファイル添付の完全対応
- マルチユーザー対応（設定ベース）
- 音声データの統合処理
- リアルタイムストリーミング

### 設定の統合
```json
{
  "api_settings": {
    "use_unified_api": true,
    "fallback_to_legacy": false,
    "session_timeout": 300
  }
}
```
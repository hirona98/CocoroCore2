# Phase 2: チャット処理スケジューラー連携実装計画

## 📅 作成日: 2025-01-28
## 🎯 目的: CocoroCore2のチャット処理でMemOSスケジューラーを活用し、テキストメモリの自動最適化を実現

---

## 🔍 調査結果概要

### MemOSスケジューラーの使用パターン
1. **クエリ前**: `QUERY_LABEL`でスケジューラーにクエリメッセージを送信
2. **チャット実行**: `mos.chat()`でLLM応答を取得
3. **応答後**: `ANSWER_LABEL`でスケジューラーに応答メッセージを送信

### 現在のCocoroCore2チャットフロー
```
ユーザー → memos_chat() → システムプロンプト追加 → MOS.chat() → 応答返却
```

### Phase 2で実現するフロー
```
ユーザー → memos_chat() → スケジューラーにクエリ送信 → MOS.chat() → スケジューラーに応答送信 → 応答返却
                ↓                                                    ↓
        テキストメモリ検索・取得                           記憶の自動整理・最適化
```

---

## 🏗️ 実装ステップ詳細

### Step 1: MemCube取得ヘルパーメソッド実装 (1日)

#### 目的
ユーザーのMemCubeを安全に取得し、スケジューラーに渡すためのヘルパーメソッドを実装

#### 実装内容

**新規メソッド**: `_get_user_memcube(user_id: str) -> Optional[GeneralMemCube]`

```python
def _get_user_memcube(self, user_id: str) -> Optional[GeneralMemCube]:
    """ユーザーのデフォルトMemCubeを取得
    
    Args:
        user_id: ユーザーID
        
    Returns:
        Optional[GeneralMemCube]: MemCubeインスタンス（見つからない場合はNone）
    """
    try:
        # ユーザーの存在確認
        self.ensure_user(user_id)
        
        # ユーザーのMemCubeを取得
        user_cubes = self.mos.user_manager.get_user_cubes(user_id=user_id)
        
        if not user_cubes:
            self.logger.warning(f"No MemCubes found for user {user_id}")
            return None
        
        # 最初のMemCubeを使用（デフォルト）
        default_cube = user_cubes[0]
        cube_id = default_cube.cube_id
        
        # MOSに登録されているかチェック
        if cube_id in self.mos.mem_cubes:
            return self.mos.mem_cubes[cube_id]
        else:
            self.logger.warning(f"MemCube {cube_id} not registered in MOS")
            return None
            
    except Exception as e:
        self.logger.error(f"Failed to get MemCube for user {user_id}: {e}")
        return None
```

#### 実装場所
- ファイル: `src/core_app.py`
- 既存の`_get_chat_llm_from_mos()`メソッドの後に追加

### Step 2: チャット処理のスケジューラー連携拡張 (2日)

#### 目的
既存の`memos_chat()`メソッドにスケジューラー連携機能を追加

#### 実装内容

**memos_chat()メソッドの拡張**:

```python
def memos_chat(self, query: str, user_id: Optional[str] = None, context: Optional[Dict] = None, system_prompt: Optional[str] = None) -> str:
    """MemOS純正チャット処理（スケジューラー連携付き）"""
    try:
        # 既存の処理: ユーザーID決定、システムプロンプト決定
        effective_user_id = user_id or self.default_user_id
        # ... システムプロンプト処理 ...
        
        # スケジューラー連携: クエリメッセージ送信
        if self.text_memory_scheduler and self.text_memory_scheduler.is_running:
            mem_cube = self._get_user_memcube(effective_user_id)
            if mem_cube:
                self.text_memory_scheduler.submit_query_message(
                    user_id=effective_user_id,
                    content=query,  # 元のクエリ（システムプロンプト含まない）
                    mem_cube=mem_cube
                )
        
        # 既存の処理: MOS.chat()実行
        response = self.mos.chat(query=full_query, user_id=effective_user_id)
        
        # スケジューラー連携: 応答メッセージ送信
        if self.text_memory_scheduler and self.text_memory_scheduler.is_running:
            mem_cube = self._get_user_memcube(effective_user_id)
            if mem_cube:
                self.text_memory_scheduler.submit_answer_message(
                    user_id=effective_user_id,
                    content=response,
                    mem_cube=mem_cube
                )
        
        self.logger.debug(f"Chat response: {len(response)} characters")
        return response
        
    except Exception as e:
        self.logger.error(f"Chat failed: {e}")
        raise
```

#### 設定オプション追加

**config.py に追加**:
```python
class MemSchedulerConfig(BaseModel):
    # 既存フィールド...
    
    # チャット連携設定
    enable_chat_integration: bool = True
    enable_memory_integration: bool = True
    auto_submit_query: bool = True
    auto_submit_answer: bool = True
```

### Step 3: 記憶追加処理のスケジューラー連携 (1日)

#### 目的
`add_memory()`メソッドにスケジューラー連携を追加

#### 実装内容

**add_memory()メソッドの拡張**:

```python
def add_memory(self, content: str, user_id: Optional[str] = None, **context) -> None:
    """記憶追加（スケジューラー連携付き）"""
    try:
        effective_user_id = user_id or self.default_user_id
        
        # 既存の処理: コンテキスト情報追加、MOS.add()実行
        # ... 既存処理 ...
        
        # スケジューラー連携: 記憶追加メッセージ送信
        if (self.text_memory_scheduler and 
            self.text_memory_scheduler.is_running and
            self.config.mem_scheduler.enable_memory_integration):
            
            mem_cube = self._get_user_memcube(effective_user_id)
            if mem_cube:
                self.text_memory_scheduler.submit_add_message(
                    user_id=effective_user_id,
                    content=content,  # 元のコンテンツ
                    mem_cube=mem_cube
                )
        
    except Exception as e:
        self.logger.error(f"Failed to add memory: {e}")
        self.logger.warning("Memory features may be temporarily disabled")
```

### Step 4: エラーハンドリングと設定オプション (1日)

#### 設定の詳細化

**default_memos_config.json に追加**:
```json
{
  "mem_scheduler": {
    "enabled": true,
    "enable_chat_integration": true,
    "enable_memory_integration": true,
    "auto_submit_query": true,
    "auto_submit_answer": true,
    "graceful_degradation": true,
    // 既存設定...
  }
}
```

#### エラーハンドリング強化

**新規メソッド**: `_safely_submit_to_scheduler()`

```python
def _safely_submit_to_scheduler(self, submit_func, *args, **kwargs) -> bool:
    """スケジューラーへの安全なメッセージ送信
    
    Returns:
        bool: 送信成功フラグ
    """
    try:
        if not (self.text_memory_scheduler and self.text_memory_scheduler.is_running):
            return False
        
        submit_func(*args, **kwargs)
        return True
        
    except Exception as e:
        self.logger.warning(f"Scheduler message submission failed: {e}")
        
        # グレースフルデグラデーション設定がある場合
        if self.config.mem_scheduler.graceful_degradation:
            return False
        else:
            raise
```

### Step 5: テスト・検証 (1日)

#### 単体テスト作成

**ファイル**: `tests/test_phase2_chat_integration.py`

テスト項目:
- MemCube取得機能のテスト
- チャット処理でのスケジューラー連携テスト
- 記憶追加でのスケジューラー連携テスト
- エラーハンドリングテスト
- 設定オプションテスト

#### 統合テスト作成

**ファイル**: `tests/test_phase2_integration.py`

テスト項目:
- 実際のチャットフローでのスケジューラー動作
- スケジューラー無効時の動作確認
- エラー時のフォールバック動作確認

---

## 📁 変更ファイル一覧

### 修正ファイル
- `src/core_app.py`: メインのチャット・記憶処理拡張
- `src/config.py`: 設定クラス拡張
- `config/default_memos_config.json`: デフォルト設定追加

### 新規ファイル
- `tests/test_phase2_chat_integration.py`: 単体テスト
- `tests/test_phase2_integration.py`: 統合テスト

---

## 🎯 Phase 2 完了基準

### 必須機能
- [ ] ユーザーMemCube取得機能
- [ ] チャット処理でのクエリ・応答メッセージ自動送信
- [ ] 記憶追加でのADDメッセージ自動送信
- [ ] 設定による機能のオン/オフ切り替え
- [ ] エラー時のグレースフルデグラデーション

### 確認項目
- [ ] 既存のチャット機能に影響を与えない
- [ ] スケジューラー無効時も正常動作
- [ ] エラー時にアプリケーション全体が停止しない
- [ ] 適切なログ出力
- [ ] テスト全体の90%以上成功

---

## 📊 実装スケジュール

**総実装期間**: 6日

- **Day 1**: Step 1 - MemCube取得ヘルパーメソッド
- **Day 2-3**: Step 2 - チャット処理スケジューラー連携
- **Day 4**: Step 3 - 記憶追加スケジューラー連携
- **Day 5**: Step 4 - エラーハンドリング・設定
- **Day 6**: Step 5 - テスト・検証

---

## 🚨 リスク・注意事項

### 技術的リスク
1. **MemCube取得の失敗**: ユーザーのMemCubeが存在しない・登録されていない場合
2. **スケジューラー応答性**: メッセージ送信の遅延がチャット応答に影響する可能性
3. **メモリ使用量**: スケジューラーの並列処理による負荷増加

### 実装時の注意点
1. **既存機能の保護**: チャット機能の基本動作を絶対に破綻させない
2. **非同期処理**: スケジューラーメッセージ送信は非ブロッキングに
3. **ログ重視**: デバッグのための詳細なログ出力
4. **段階的テスト**: 各ステップで動作確認を実施

---

*このPhase 2実装計画により、CocoroCore2でのテキストメモリスケジューラー活用が実現され、自動的な記憶最適化が動作します。*
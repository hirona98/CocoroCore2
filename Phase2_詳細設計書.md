# Phase 2: チャット処理スケジューラー連携 - 詳細設計書

## 📅 作成日: 2025-01-28
## 🎯 目的: Phase 2実装の詳細設計とコード例

---

## 🔧 実装詳細

### Step 1: MemCube取得ヘルパーメソッド

#### 1.1 `_get_user_memcube()`メソッド実装

**ファイル**: `src/core_app.py`  
**追加位置**: `_get_chat_llm_from_mos()`メソッドの後

```python
def _get_user_memcube(self, user_id: str) -> Optional["GeneralMemCube"]:
    """ユーザーのデフォルトMemCubeを取得
    
    Args:
        user_id: ユーザーID
        
    Returns:
        Optional[GeneralMemCube]: MemCubeインスタンス（見つからない場合はNone）
    """
    try:
        # ユーザーの存在を確認・作成
        self.ensure_user(user_id)
        
        # ユーザーのMemCubeリストを取得
        user_cubes = self.mos.user_manager.get_user_cubes(user_id=user_id)
        
        if not user_cubes or len(user_cubes) == 0:
            self.logger.warning(f"No MemCubes found for user {user_id}")
            return None
        
        # 最初のMemCubeをデフォルトとして使用
        default_cube = user_cubes[0]
        cube_id = default_cube.cube_id
        
        # MOSのmem_cubesに登録されているかチェック
        if cube_id in self.mos.mem_cubes:
            self.logger.debug(f"Retrieved MemCube {cube_id} for user {user_id}")
            return self.mos.mem_cubes[cube_id]
        else:
            # 登録されていない場合は警告ログ
            self.logger.warning(f"MemCube {cube_id} found but not registered in MOS for user {user_id}")
            return None
            
    except Exception as e:
        self.logger.error(f"Failed to get MemCube for user {user_id}: {e}")
        return None

def _get_user_memcube_id(self, user_id: str) -> Optional[str]:
    """ユーザーのデフォルトMemCube IDを取得
    
    Args:
        user_id: ユーザーID
        
    Returns:
        Optional[str]: MemCube ID（見つからない場合はNone）
    """
    try:
        user_cubes = self.mos.user_manager.get_user_cubes(user_id=user_id)
        
        if not user_cubes or len(user_cubes) == 0:
            return None
        
        return user_cubes[0].cube_id
        
    except Exception as e:
        self.logger.error(f"Failed to get MemCube ID for user {user_id}: {e}")
        return None
```

#### 1.2 スケジューラー連携安全実行メソッド

```python
def _safely_submit_to_scheduler(self, action_name: str, submit_func, *args, **kwargs) -> bool:
    """スケジューラーへの安全なメッセージ送信
    
    Args:
        action_name: アクション名（ログ用）
        submit_func: 送信関数
        *args, **kwargs: 送信関数への引数
        
    Returns:
        bool: 送信成功フラグ
    """
    try:
        # スケジューラーが利用可能かチェック
        if not (self.text_memory_scheduler and 
                self.text_memory_scheduler.is_running and
                self.config.mem_scheduler.enabled):
            self.logger.debug(f"Scheduler not available for {action_name}")
            return False
        
        # メッセージ送信実行
        submit_func(*args, **kwargs)
        self.logger.debug(f"Successfully submitted {action_name} to scheduler")
        return True
        
    except Exception as e:
        self.logger.warning(f"Failed to submit {action_name} to scheduler: {e}")
        
        # グレースフルデグラデーション設定がある場合はエラーを隠す
        if self.config.mem_scheduler.text_memory_optimization.get("graceful_degradation", True):
            return False
        else:
            # 設定で例外の再発生が指定されている場合
            raise
```

### Step 2: チャット処理のスケジューラー連携拡張

#### 2.1 `memos_chat()`メソッドの拡張

```python
def memos_chat(self, query: str, user_id: Optional[str] = None, context: Optional[Dict] = None, system_prompt: Optional[str] = None) -> str:
    """MemOS純正チャット処理（スケジューラー連携付き）
    
    Args:
        query: ユーザーの質問
        user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
        context: 追加コンテキスト情報
        system_prompt: システムプロンプト（キャラクター設定）
        
    Returns:
        str: AIの応答
    """
    try:
        # 既存の処理: 有効なユーザーIDを決定
        effective_user_id = user_id or self.default_user_id
        
        # 既存の処理: システムプロンプトを決定
        if system_prompt:
            effective_system_prompt = system_prompt
        else:
            character_name = self.config.character.name
            effective_system_prompt = self.default_system_prompts.get(
                character_name,
                f"あなたは「{character_name}」という名前のバーチャルアシスタントです。"
            )
        
        # システムプロンプトをqueryに追加
        full_query = f"{effective_system_prompt}\n\n{query}"
        
        # **新規追加**: スケジューラーにクエリメッセージを送信
        if self.config.mem_scheduler.auto_submit_query:
            mem_cube = self._get_user_memcube(effective_user_id)
            if mem_cube:
                self._safely_submit_to_scheduler(
                    "query_message",
                    self.text_memory_scheduler.submit_query_message,
                    user_id=effective_user_id,
                    content=query,  # 元のクエリ（システムプロンプトは含まない）
                    mem_cube=mem_cube
                )
        
        # 既存の処理: 正規版MOSでのチャット処理
        response = self.mos.chat(query=full_query, user_id=effective_user_id)
        
        # **新規追加**: スケジューラーに応答メッセージを送信
        if self.config.mem_scheduler.auto_submit_answer:
            mem_cube = self._get_user_memcube(effective_user_id)
            if mem_cube:
                self._safely_submit_to_scheduler(
                    "answer_message",
                    self.text_memory_scheduler.submit_answer_message,
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

### Step 3: 記憶追加処理のスケジューラー連携

#### 3.1 `add_memory()`メソッドの拡張

```python
def add_memory(self, content: str, user_id: Optional[str] = None, **context) -> None:
    """記憶追加（スケジューラー連携付き）
    
    Args:
        content: 記憶内容
        user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
        **context: 追加コンテキスト情報
    """
    try:
        # 既存の処理: 有効なユーザーIDを決定
        effective_user_id = user_id or self.default_user_id
        
        # 既存の処理: コンテキスト情報を本文に含める
        memory_content = content
        if context:
            import json
            context_info = {
                "character": self.config.character.name,
                "timestamp": datetime.now().isoformat(),
                **context
            }
            memory_content += f" | Context: {json.dumps(context_info)}"
        
        # 既存の処理: 正規版MOSAPIで記憶追加
        self.mos.add(memory_content=memory_content, user_id=effective_user_id)
        
        # **新規追加**: スケジューラーに記憶追加メッセージを送信
        if self.config.mem_scheduler.enable_memory_integration:
            mem_cube = self._get_user_memcube(effective_user_id)
            if mem_cube:
                self._safely_submit_to_scheduler(
                    "add_message",
                    self.text_memory_scheduler.submit_add_message,
                    user_id=effective_user_id,
                    content=content,  # 元のコンテンツ（コンテキスト情報は含まない）
                    mem_cube=mem_cube
                )
        
        self.logger.debug(f"Memory added: {len(content)} characters")
        
    except Exception as e:
        self.logger.error(f"Failed to add memory: {e}")
        # メモリ保存の失敗はチャット機能全体を停止させない
        self.logger.warning("Memory features may be temporarily disabled")
```

### Step 4: 設定拡張

#### 4.1 `config.py`の拡張

```python
class MemSchedulerConfig(BaseModel):
    """メモリスケジューラー設定"""
    enabled: bool = False
    top_k: int = 5
    context_window_size: int = 5
    enable_act_memory_update: bool = False
    enable_parallel_dispatch: bool = False
    thread_pool_max_workers: int = 3
    consume_interval_seconds: int = 2
    act_mem_update_interval: int = 300
    
    # **新規追加**: チャット連携設定
    enable_chat_integration: bool = True
    enable_memory_integration: bool = True
    auto_submit_query: bool = True
    auto_submit_answer: bool = True
    
    # テキストメモリ特化設定
    text_memory_optimization: Dict[str, Any] = Field(default_factory=lambda: {
        "enable_deduplication": True,
        "similarity_threshold": 0.95,
        "working_memory_size": 20,
        "long_term_memory_capacity": 10000,
        "user_memory_capacity": 10000,
        # **新規追加**: エラーハンドリング設定
        "graceful_degradation": True,
        "log_scheduler_errors": True
    })
```

#### 4.2 `default_memos_config.json`の拡張

```json
{
  "mem_scheduler": {
    "enabled": true,
    "top_k": 5,
    "context_window_size": 5,
    "enable_act_memory_update": false,
    "enable_parallel_dispatch": false,
    "thread_pool_max_workers": 3,
    "consume_interval_seconds": 2,
    "act_mem_update_interval": 300,
    "enable_chat_integration": true,
    "enable_memory_integration": true,
    "auto_submit_query": true,
    "auto_submit_answer": true,
    "text_memory_optimization": {
      "enable_deduplication": true,
      "similarity_threshold": 0.95,
      "working_memory_size": 20,
      "long_term_memory_capacity": 10000,
      "user_memory_capacity": 10000,
      "graceful_degradation": true,
      "log_scheduler_errors": true
    }
  }
}
```

### Step 5: ステータス取得機能の拡張

#### 5.1 `get_app_status()`メソッドの拡張

```python
def get_app_status(self) -> Dict[str, Any]:
    """アプリケーション状態を取得"""
    try:
        # 既存のステータス情報取得
        status = {
            # ... 既存のステータス情報 ...
        }
        
        # **拡張**: スケジューラー詳細情報を追加
        if self.text_memory_scheduler:
            scheduler_status = self.text_memory_scheduler.get_scheduler_status()
            
            # Phase 2固有のステータス情報を追加
            scheduler_status.update({
                "chat_integration_enabled": self.config.mem_scheduler.enable_chat_integration,
                "memory_integration_enabled": self.config.mem_scheduler.enable_memory_integration,
                "auto_submit_query": self.config.mem_scheduler.auto_submit_query,
                "auto_submit_answer": self.config.mem_scheduler.auto_submit_answer,
                "memcube_available": self._get_user_memcube(self.default_user_id) is not None
            })
            
            status["scheduler_status"] = scheduler_status
        
        return status
        
    except Exception as e:
        self.logger.error(f"Failed to get app status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "version": self.config.version,
        }
```

---

## 🧪 テスト設計

### Unit Test: `test_phase2_chat_integration.py`

```python
"""
Phase 2チャット統合機能のテスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.config import CocoroCore2Config
from src.core_app import CocoroCore2App


class TestPhase2ChatIntegration:
    """Phase 2チャット統合テストクラス"""
    
    @pytest.fixture
    def sample_config_phase2(self):
        """Phase 2設定を作成"""
        config_data = {
            # ... 基本設定 ...
            "mem_scheduler": {
                "enabled": True,
                "enable_chat_integration": True,
                "enable_memory_integration": True,
                "auto_submit_query": True,
                "auto_submit_answer": True,
                # ... その他設定 ...
            }
        }
        return CocoroCore2Config(**config_data)
    
    @patch('src.core_app.MOS')
    def test_get_user_memcube_success(self, mock_mos_class, sample_config_phase2):
        """MemCube取得成功テスト"""
        # MOSとMemCubeをモック
        mock_mos = Mock()
        mock_user_manager = Mock()
        mock_cube = Mock()
        mock_cube.cube_id = "test_cube_id"
        
        mock_user_manager.get_user_cubes.return_value = [mock_cube]
        mock_mos.user_manager = mock_user_manager
        mock_mos.mem_cubes = {"test_cube_id": mock_cube}
        mock_mos_class.return_value = mock_mos
        
        app = CocoroCore2App(sample_config_phase2)
        
        # MemCube取得テスト
        result = app._get_user_memcube("test_user")
        assert result == mock_cube
    
    @patch('src.core_app.MOS')
    def test_memos_chat_with_scheduler_integration(self, mock_mos_class, sample_config_phase2):
        """スケジューラー連携付きチャットテスト"""
        # MOSとスケジューラーをモック
        mock_mos = Mock()
        mock_mos.chat.return_value = "Test response"
        mock_mos_class.return_value = mock_mos
        
        with patch('src.core.text_memory_scheduler._memos_import_error', None):
            app = CocoroCore2App(sample_config_phase2)
            
            # スケジューラーをモック
            mock_scheduler = Mock()
            mock_scheduler.is_running = True
            mock_scheduler.submit_query_message = Mock()
            mock_scheduler.submit_answer_message = Mock()
            app.text_memory_scheduler = mock_scheduler
            
            # MemCubeをモック
            mock_cube = Mock()
            app._get_user_memcube = Mock(return_value=mock_cube)
            
            # チャット実行
            response = app.memos_chat("Test query", "test_user")
            
            # 結果確認
            assert response == "Test response"
            mock_scheduler.submit_query_message.assert_called_once()
            mock_scheduler.submit_answer_message.assert_called_once()
```

---

## 📊 実装スケジュール詳細

### Day 1: MemCube取得ヘルパーメソッド
- `_get_user_memcube()`実装
- `_get_user_memcube_id()`実装
- `_safely_submit_to_scheduler()`実装
- 基本的な単体テスト作成

### Day 2: チャット処理拡張 (Part 1)
- `memos_chat()`メソッドの分析・設計
- クエリメッセージ送信機能の実装
- 基本動作テスト

### Day 3: チャット処理拡張 (Part 2)
- 応答メッセージ送信機能の実装
- エラーハンドリングの実装
- チャット統合テストの作成

### Day 4: 記憶追加連携
- `add_memory()`メソッドの拡張
- ADD_LABELメッセージ送信の実装
- 記憶統合テストの作成

### Day 5: 設定・ステータス拡張
- 設定クラスの拡張
- ステータス取得機能の拡張
- 設定テストの更新

### Day 6: 総合テスト・検証
- 統合テストの作成・実行
- 実動作確認
- ドキュメント更新

---

*この詳細設計書に従って実装することで、CocoroCore2のチャット処理でMemOSスケジューラーが自動的に活用され、テキストメモリの最適化が行われます。*
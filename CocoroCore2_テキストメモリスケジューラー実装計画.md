# CocoroCore2 テキストメモリスケジューラー実装計画

## 📅 作成日: 2025-01-28
## 🎯 目的: CocoroCore2にMemOSのテキストメモリスケジューラーを統合し、効率的なテキストメモリ管理を実現

---

## 🔍 調査結果サマリー（テキストメモリ特化）

### MemOSメモリスケジューラーの活用機能
- **メッセージキューイング**: `ScheduleMessageItem`を使った非同期メッセージ処理
- **ディスパッチャー**: `SchedulerDispatcher`によるラベル別ハンドラー振り分け
- **モニタリング**: `SchedulerMonitor`による意図検出・検索トリガー判定
- **検索・取得**: `SchedulerRetriever`による関連テキストメモリ検索
- **ワーキングメモリ管理**: 関連性の高いメモリをワーキングメモリに配置

### CocoroCore2の現状
- MemOSが既に統合済み（同期チャット処理）
- テキストメモリ（TreeTextMemory/GeneralTextMemory）使用
- ユーザー・セッション管理機能あり
- FastAPI基盤のRESTサーバー

---

## 📋 実装計画（テキストメモリ特化）

### Phase 1: テキストメモリスケジューラー統合基盤
1. **MemOSスケジューラー設定追加**
   - `config.py`にスケジューラー関連設定を追加
   - テキストメモリのみの設定に特化
   - アクティベーションメモリ機能を無効化

2. **CocoroCore2Appへのスケジューラー統合**
   - `GeneralScheduler`インスタンスの初期化
   - テキストメモリのみを対象とした設定
   - 起動・終了処理にスケジューラーライフサイクル管理を追加

### Phase 2: テキストメモリの効率的管理
1. **チャット処理での非同期メモリ管理**
   - クエリ時に`QUERY_LABEL`メッセージをスケジューラーに送信
   - 関連テキストメモリの自動検索・ワーキングメモリ更新
   - 応答時に`ANSWER_LABEL`メッセージをスケジューラーに送信

2. **テキストメモリ操作の最適化**
   - 記憶追加時に`ADD_LABEL`メッセージを送信
   - バックグラウンドでのテキストメモリ整理・分類
   - 重複メモリの検出・統合

### Phase 3: 高度なテキストメモリ機能
1. **意図的なメモリ検索**
   - `SchedulerMonitor`による検索トリガー判定
   - 欠落証拠の特定・補完
   - ワーキングメモリの動的更新

2. **モニタリング・分析機能**
   - テキストメモリ使用状況の追跡
   - メモリアクセス頻度の分析
   - メモリ効率性の可視化

---

## 🏗️ 詳細設計（テキストメモリ特化）

### 1. 設定拡張

**config/default_memos_config.json** への追加:
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
    "text_memory_optimization": {
      "enable_deduplication": true,
      "similarity_threshold": 0.95,
      "working_memory_size": 20,
      "long_term_memory_capacity": 10000,
      "user_memory_capacity": 10000
    }
  }
}
```

### 2. CocoroCore2App拡張

**新しいメソッド**:
- `_initialize_text_memory_scheduler()`: テキストメモリスケジューラー初期化
- `_submit_scheduler_message()`: スケジューラーメッセージ送信
- `get_text_memory_stats()`: テキストメモリ統計取得
- `optimize_text_memory()`: テキストメモリ最適化

**修正メソッド**:
- `memos_chat()`: チャット処理にテキストメモリスケジューラー統合
- `add_memory()`: 記憶追加でスケジューラー活用
- `startup()`/`shutdown()`: スケジューラーライフサイクル管理

### 3. API拡張

**新しいエンドポイント**:
- `GET /scheduler/status`: テキストメモリスケジューラー状態取得
- `GET /scheduler/logs`: スケジューラーログ取得
- `GET /memory/text/stats`: テキストメモリ統計情報取得
- `POST /memory/text/optimize`: テキストメモリ最適化実行

### 4. ディレクトリ構成

```
CocoroCore2/
├── src/
│   ├── core/
│   │   ├── text_memory_scheduler.py    # NEW: テキストメモリスケジューラー統合
│   │   └── scheduler_config.py         # NEW: スケジューラー設定管理
│   ├── api/
│   │   └── text_memory_endpoints.py    # NEW: テキストメモリスケジューラーAPI
│   └── services/
│       └── text_memory_service.py      # NEW: テキストメモリ操作サービス
└── config/
    └── text_memory_scheduler.json      # NEW: テキストメモリスケジューラー設定
```

### 5. 技術的な統合ポイント（テキストメモリ特化）

#### テキストメモリスケジューラーメッセージフロー:
1. ユーザーチャット → `QUERY_LABEL`メッセージ → スケジューラー
2. 意図検出・関連テキストメモリ検索・ワーキングメモリ更新
3. LLM応答生成 → `ANSWER_LABEL`メッセージ → スケジューラー
4. テキストメモリ使用頻度更新・重要度調整

#### 並行処理設計:
- メインチャット処理は同期的に実行（レスポンス性確保）
- テキストメモリスケジューラー処理は非同期バックグラウンドで実行
- スレッドセーフなメッセージキュー使用

#### メモリ階層管理:
- **LongTermMemory**: 永続的な知識・学習内容
- **UserMemory**: ユーザー固有の記憶・設定
- **WorkingMemory**: 現在の会話で使用する関連メモリ

### 6. 段階的実装アプローチ

**Step 1**: 基本統合（設定・初期化・基本メッセージ送信）
**Step 2**: チャット統合（QUERY/ANSWERラベル処理）
**Step 3**: テキストメモリ最適化（重複検出・分類・整理）
**Step 4**: 分析・モニタリング機能（使用状況・効率性）

---

## 🎯 期待される効果（テキストメモリ特化）

1. **メモリ効率向上**: 関連性の高いテキストメモリの自動選択
2. **検索精度向上**: 意図検出による適切なメモリ検索
3. **重複削減**: 類似テキストメモリの自動統合
4. **ユーザー体験**: より文脈に適した応答生成
5. **保守性**: MemOSの標準テキストメモリ機能活用

---

## 📝 実装時の注意点

1. **アクティベーションメモリ無効化**: `enable_act_memory_update: false`
2. **KVキャッシュ機能除外**: テキストメモリのみに集中
3. **ワーキングメモリサイズ調整**: 適切なサイズでパフォーマンス最適化
4. **検索閾値調整**: テキストメモリ検索の精度とパフォーマンスのバランス

---

## 🚀 実装優先順位

### 高優先度
- [ ] Phase 1: 基本統合とスケジューラー設定
- [ ] コア機能（QUERY/ANSWER/ADDメッセージ処理）

### 中優先度
- [ ] Phase 2: テキストメモリ最適化機能
- [ ] API拡張（ステータス・ログ取得）

### 低優先度
- [ ] Phase 3: 高度な分析・モニタリング機能
- [ ] パフォーマンス最適化・チューニング

---

## 📚 参考資料

- **MemOS公式ドキュメント**: `Reference/MemOS-Docs/`
- **MemOSソースコード**: `Reference/MemOS/src/memos/mem_scheduler/`
- **GitHubリポジトリ**: https://github.com/MemTensor/MemOS
- **CocoroCore2既存実装**: `src/core_app.py`, `src/config.py`

---

*このドキュメントは実装の進行に合わせて更新されます。*
# CocoroCore2 概要
## MemOSベース記憶統合システム

---

## 1. プロジェクト概要

### 1.1 目的と背景

CocoroCore2は、現在のCocoroCore（AIAvatarKit使用）とCocoroMemory（ChatMemory使用）の機能を、**MemOS**を基盤として統合・再構成する新システムです。

**移行の目的:**
- **記憶システムの高度化**: MemOSの先進的な記憶管理機能を活用
- **アーキテクチャの単純化**: 2つのコンポーネントを1つに統合し保守性向上
- **性能の向上**: MemOSの高性能な記憶検索・管理機能を利用
- **将来拡張性**: モジュラー設計による機能拡張の容易さ

### 1.2 現行システム分析

#### 現行CocoroCore（AIAvatarKit）
```
機能:
- FastAPI HTTP サーバー（ポート: 55601）
- LLM対話エンジン（多プロバイダー対応）
- Speech-To-Speech パイプライン
- ChatMemory との非同期通信
- MCP（Model Context Protocol）ツール統合
- セッション管理（5分タイムアウト）

技術スタック:
- Python 3.10
- aiavatar（AIAvatarKit）フレームワーク
- FastAPI + uvicorn
- httpx（非同期HTTP通信）
- litellm（マルチLLMプロバイダー）
```

#### 現行CocoroMemory（ChatMemory）
```
機能:
- PostgreSQL ベース長期記憶
- 埋め込みベクトルによる類似検索
- 会話履歴の要約・分類・検索
- chatmemory ライブラリベース

技術スタック:
- Python 3.10
- PostgreSQL + pgvector
- chatmemory ライブラリ
- FastAPI（独立サーバー）
```

#### 現行システムの課題
1. **2つのプロセス管理の複雑さ**: CocoroCore と CocoroMemory の分離
2. **通信オーバーヘッド**: HTTP通信による記憶操作の遅延
3. **依存関係管理**: 異なるライブラリ（aiavatar vs chatmemory）の並行管理
4. **記憶機能の制限**: chatmemorycに比べMemOSのより高度な記憶管理機能

### 1.3 MemOSの特徴と利点

MemOS（Memory Operating System for LLMs）は大規模言語モデル向けの記憶管理システムです。

#### 主要機能
```
記憶タイプ:
- Textual Memory: 構造化・非構造化テキスト知識
- Activation Memory: KVキャッシュによる推論高速化
- Parametric Memory: LoRA重みなどモデル適応パラメータ

アーキテクチャ:
- MemCube: モジュラー記憶アーキテクチャ
- Memory-Augmented Generation (MAG): 統一API
- 拡張可能設計: カスタムメモリモジュール対応
```

#### MemOS資料
- ドキュメント: ../Reference/MemOS-Docs
- ソースコード: ../Reference/MemOS
- GitHubリポジトリ（deepwikiで利用可能）: https://github.com/MemTensor/MemOS

---

## 2. CocoroCore2 設計方針

### 2.1 設計原則

1. **統合性**: 記憶機能を内包した単一プロセス設計
2. **互換性**: 既存のCocoroDock・CocoroShellとの連携維持
3. **シンプル性**: 複雑な通信を廃止し、直接的な記憶アクセス
4. **拡張性**: MemOSのモジュラー設計を活用した機能拡張
5. **性能**: MemOSの高性能記憶検索による応答速度向上

---

## 3. システムアーキテクチャ

### 3.1 全体構成

```
 ┌────────────────┐    ┌─────────────────────────────────┐    ┌─────────────────┐
 │   CocoroDock   │◄──►│        CocoroCore2              │◄──►│  CocoroShell    │
 │  (WPF UI)      │    │    (FastAPI + MemOS)            │    │ (Unity/VRM)     │
 │  Port: 55600   │    │      Port: 55601                │    │  Port: 55605    │
 │                │    │                                 │    └─────────────────┘
 │                │    │ ┌─────────────────────────────┐ │
 │  Notification  │    │ │     MemOS Core              │ │
 │    Server      │    │ │  - Memory Management        │ │
 │  Port: 55604   │    │ │  - Chat Integration         │ │
 │                │    │ │  - Multi-User Support       │ │
 │                │    │ │  - MemCube Management       │ │
 └────────────────┘    │ └─────────────────────────────┘ │
                       │                                 │
                       │ ┌─────────────────────────────┐ │             
                       │ │    Additional Features      │ │             
                       │ │  - STT/VAD Pipeline         │ │             
                       │ │  - MCP Tool Integration     │ │             
                       │ │  - Session Management       │ │             
                       │ └─────────────────────────────┘ │             
                       └─────────────────────────────────┘             
```

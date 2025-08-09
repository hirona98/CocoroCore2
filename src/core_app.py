"""
CocoroCore2 Core Application

"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from memos.mem_os.main import MOS

try:
    from config import CocoroAIConfig, get_mos_config, generate_memos_config_from_setting, load_neo4j_config
except ImportError:
    from src.config import CocoroAIConfig, get_mos_config, generate_memos_config_from_setting, load_neo4j_config

try:
    from .core.neo4j_manager import Neo4jManager
except ImportError:
    from core.neo4j_manager import Neo4jManager


class CocoroCore2App:
    """MOSを使用したCocoroCore2メインアプリケーション"""

    def __init__(self, config: CocoroAIConfig):
        """初期化

        Args:
            config: CocoroAI設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # MOS用の環境変数設定
        self._setup_memos_environment()

        # MOS初期化
        try:
            # MOSConfig作成
            mos_config = get_mos_config(config)
            self.mos = MOS(mos_config)
            
            # カスタムOpenAILLMラッパーを適用（新しいモデル対応）
            self.logger.info("[MOS_INIT] Checking if custom wrapper should be applied...")
            if self._should_use_custom_openai_wrapper():
                self.logger.info("[MOS_INIT] Will apply custom wrapper")
                self._apply_custom_openai_wrapper()
            else:
                self.logger.info("[MOS_INIT] Custom wrapper not needed")

            # デフォルトユーザーID設定
            memos_config_data = generate_memos_config_from_setting(config)
            self.default_user_id = memos_config_data.get("user_id", "default")
            self.logger.info(f"MOS initialized successfully with user_id: {self.default_user_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize MOS: {e}")
            raise

        # セッション管理（session_id -> user_id マッピング）
        self.session_mapping: Dict[str, str] = {}

        # アプリケーション状態
        self.is_running = False
        self.startup_time = datetime.now()

        # Neo4j組み込みサービス管理
        self.neo4j_manager: Optional[Neo4jManager] = None
        self.neo4j_settings = load_neo4j_config()
        if self.neo4j_settings.get("embedded_enabled", False):
            try:
                self.neo4j_manager = Neo4jManager(self.neo4j_settings)
                self.logger.info("Neo4j manager created for embedded mode")

            except Exception as e:
                self.logger.error(f"Failed to create Neo4j manager: {e}")
                self.neo4j_manager = None
        else:
            self.logger.info("Embedded Neo4j is disabled, expecting external Neo4j instance")

        self.logger.info("CocoroCore2App initialized with full MOS integration")

    def _log_advanced_features_status(self):
        """CocoroCore2で有効化されたMemOS機能の状態をログ出力"""
        self.logger.info("============================================================")
        self.logger.info("[INFO] CocoroCore2 MemOS Integration Status")
        self.logger.info("============================================================")

        # Phase 1: 文脈依存クエリ対応
        query_status = "[OK] ENABLED" if self.config.enable_query_rewriting else "[OFF] DISABLED"
        self.logger.info(f"[QR] Query Rewriting: {query_status}")

        # Phase 2: Internet Retrieval
        if self.config.enable_internet_retrieval:
            if self.config.googleApiKey and self.config.googleSearchEngineId:
                self.logger.info(f"[NET] Internet Retrieval: [OK] ENABLED ({self.config.internetMaxResults}件)")
            else:
                self.logger.info("[NET] Internet Retrieval: [WARN] 設定不完全")
        else:
            self.logger.info("[NET] Internet Retrieval: [OFF] DISABLED")

        # Memory Scheduler（常に有効）
        try:
            scheduler = getattr(self.mos, 'mem_scheduler', None)
            if scheduler:
                self.logger.info(f"[SYS] Memory Scheduler: [OK] ENABLED (Active)")
                self.logger.info(f"[SYS]   |- Top-K: {self.config.scheduler_top_k}")
                self.logger.info(f"[SYS]   |- Top-N: {self.config.scheduler_top_n}")
                self.logger.info(f"[SYS]   |- Context Window: {self.config.scheduler_context_window_size}")
                self.logger.info(f"[SYS]   |- Workers: {self.config.scheduler_thread_pool_max_workers}")
                self.logger.info(f"[SYS]   |- Consume Interval: {self.config.scheduler_consume_interval_seconds}s")
                self.logger.info(f"[SYS]   |- Parallel Dispatch: {'[OK]' if self.config.scheduler_enable_parallel_dispatch else '[OFF]'}")
                self.logger.info(f"[SYS]   +- Activation Memory Update: {'[OK]' if self.config.scheduler_enable_act_memory_update else '[OFF]'}")
            else:
                self.logger.info("[SYS] Memory Scheduler: [WARN] Not initialized")
        except Exception as e:
            self.logger.warning(f"[SYS] Memory Scheduler: [WARN] Status check failed: {e}")

        self.logger.info(f"[CHAT] 会話履歴保持: {self.config.max_turns_window}ターン")
        self.logger.info("============================================================")

    def _setup_memos_environment(self):
        """MOS用の環境変数を設定する"""
        try:
            # 設定ファイルからAPIキーを取得
            memos_config_data = generate_memos_config_from_setting(self.config)
            api_key = memos_config_data["chat_model"]["config"]["api_key"]

            # 環境変数設定
            if api_key:  # APIキーが設定されている場合のみ
                os.environ["OPENAI_API_KEY"] = api_key
            os.environ["MOS_TEXT_MEM_TYPE"] = "tree_text"

            # 必要に応じて他の環境変数も設定
            if "OPENAI_API_BASE" not in os.environ:
                # デフォルトのOpenAI API base URLを使用
                pass

            self.logger.info("MemOS environment variables configured")

        except Exception as e:
            self.logger.error(f"Failed to setup MemOS environment: {e}")
            raise

    def _find_character_by_user_id(self, user_id: str) -> Optional[object]:
        """user_idに対応するキャラクター設定を検索
        
        Args:
            user_id: 検索対象のユーザーID
            
        Returns:
            Optional[object]: 対応するキャラクター設定、見つからない場合はNone
        """
        try:
            for character in self.config.characterList:
                if character.userId == user_id:
                    return character
            return None
        except Exception as e:
            self.logger.error(f"Failed to find character for user_id {user_id}: {e}")
            return None

    def _sync_memcube_api_keys(self) -> None:
        """既存MemCubeのAPIキーを各キャラクター設定から個別同期"""
        import os
        import json
        from pathlib import Path
        
        try:
            # .memos/user_cubesディレクトリ内の全てのMemCubeをチェック
            user_cubes_dir = Path(".memos/user_cubes")
            if not user_cubes_dir.exists():
                self.logger.debug("No existing MemCubes found for API key sync")
                return
            
            self.logger.info("Syncing existing MemCube API keys with character-specific settings...")
            synced_count = 0
            skipped_count = 0
            
            # 各MemCubeディレクトリを処理
            for cube_dir in user_cubes_dir.iterdir():
                if not cube_dir.is_dir():
                    continue
                
                config_file = cube_dir / "config.json"
                if not config_file.exists():
                    self.logger.warning(f"No config.json found in MemCube: {cube_dir.name}")
                    continue
                
                try:
                    # config.jsonを読み込み
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # MemCubeのuser_idを取得
                    cube_user_id = config_data.get("user_id")
                    if not cube_user_id:
                        self.logger.warning(f"No user_id found in MemCube: {cube_dir.name}")
                        continue
                    
                    # 対応するキャラクター設定を検索
                    character = self._find_character_by_user_id(cube_user_id)
                    if not character:
                        self.logger.warning(f"No character found for user_id '{cube_user_id}' in MemCube: {cube_dir.name}")
                        skipped_count += 1
                        continue
                    
                    # キャラクターのMemory機能が無効な場合はスキップ
                    if not getattr(character, 'isEnableMemory', False):
                        self.logger.debug(f"Memory disabled for character '{character.modelName}' (user_id: {cube_user_id}), skipping API key sync")
                        skipped_count += 1
                        continue
                    
                    # キャラクター固有のAPIキーを取得
                    api_key = getattr(character, 'apiKey', '') or ""
                    embedded_api_key = getattr(character, 'embeddedApiKey', '') or api_key
                    
                    # APIキーの有効性チェック
                    if not api_key.startswith("sk-"):
                        self.logger.debug(f"No valid API key for character '{character.modelName}' (user_id: {cube_user_id}), skipping sync")
                        skipped_count += 1
                        continue
                    
                    # APIキーを更新する必要があるかチェック
                    needs_update = False
                    
                    # extractor_llm のAPIキー更新
                    current_extractor_key = (config_data.get("text_mem", {}).get("config", {})
                                           .get("extractor_llm", {}).get("config", {}).get("api_key"))
                    if current_extractor_key != api_key:
                        if "text_mem" not in config_data:
                            config_data["text_mem"] = {}
                        if "config" not in config_data["text_mem"]:
                            config_data["text_mem"]["config"] = {}
                        if "extractor_llm" not in config_data["text_mem"]["config"]:
                            config_data["text_mem"]["config"]["extractor_llm"] = {}
                        if "config" not in config_data["text_mem"]["config"]["extractor_llm"]:
                            config_data["text_mem"]["config"]["extractor_llm"]["config"] = {}
                        
                        config_data["text_mem"]["config"]["extractor_llm"]["config"]["api_key"] = api_key
                        needs_update = True
                    
                    # dispatcher_llm のAPIキー更新
                    current_dispatcher_key = (config_data.get("text_mem", {}).get("config", {})
                                            .get("dispatcher_llm", {}).get("config", {}).get("api_key"))
                    if current_dispatcher_key != api_key:
                        if "text_mem" not in config_data:
                            config_data["text_mem"] = {}
                        if "config" not in config_data["text_mem"]:
                            config_data["text_mem"]["config"] = {}
                        if "dispatcher_llm" not in config_data["text_mem"]["config"]:
                            config_data["text_mem"]["config"]["dispatcher_llm"] = {}
                        if "config" not in config_data["text_mem"]["config"]["dispatcher_llm"]:
                            config_data["text_mem"]["config"]["dispatcher_llm"]["config"] = {}
                        
                        config_data["text_mem"]["config"]["dispatcher_llm"]["config"]["api_key"] = api_key
                        needs_update = True
                    
                    # embedder のAPIキー更新
                    current_embedder_key = (config_data.get("text_mem", {}).get("config", {})
                                          .get("embedder", {}).get("config", {}).get("api_key"))
                    if current_embedder_key != embedded_api_key:
                        if "text_mem" not in config_data:
                            config_data["text_mem"] = {}
                        if "config" not in config_data["text_mem"]:
                            config_data["text_mem"]["config"] = {}
                        if "embedder" not in config_data["text_mem"]["config"]:
                            config_data["text_mem"]["config"]["embedder"] = {}
                        if "config" not in config_data["text_mem"]["config"]["embedder"]:
                            config_data["text_mem"]["config"]["embedder"]["config"] = {}
                        
                        config_data["text_mem"]["config"]["embedder"]["config"]["api_key"] = embedded_api_key
                        needs_update = True
                    
                    # 更新が必要な場合のみファイルを書き換え
                    if needs_update:
                        with open(config_file, 'w', encoding='utf-8') as f:
                            json.dump(config_data, f, indent=2, ensure_ascii=False)
                        self.logger.info(f"Updated API keys in MemCube '{cube_dir.name}' for character '{character.modelName}' (user_id: {cube_user_id})")
                        synced_count += 1
                    else:
                        self.logger.debug(f"API keys already up-to-date in MemCube '{cube_dir.name}' for character '{character.modelName}' (user_id: {cube_user_id})")
                
                except Exception as e:
                    self.logger.error(f"Failed to sync API keys in MemCube {cube_dir.name}: {e}")
                    skipped_count += 1
            
            self.logger.info(f"MemCube API key sync completed: {synced_count} updated, {skipped_count} skipped")
            
        except Exception as e:
            self.logger.error(f"Failed to sync MemCube API keys: {e}")

    def _should_use_custom_openai_wrapper(self) -> bool:
        """カスタムOpenAIラッパーを使用すべきか判定"""
        # MOSのchat_llmがOpenAILLMかチェック
        from memos.llms.openai import OpenAILLM
        
        self.logger.info(f"[WRAPPER_CHECK] Checking if custom wrapper should be applied...")
        self.logger.info(f"[WRAPPER_CHECK] chat_llm type: {type(self.mos.chat_llm)}")
        
        if not isinstance(self.mos.chat_llm, OpenAILLM):
            self.logger.info("[WRAPPER_CHECK] chat_llm is not OpenAILLM, skipping wrapper")
            return False
        
        # モデル名をチェック（新しいモデルかどうか）
        model_name = self.mos.chat_llm.config.model_name_or_path
        new_models = ["gpt-4o", "o1", "o3", "gpt-5"]  # 新しいモデルのプレフィックス
        
        self.logger.info(f"[WRAPPER_CHECK] Model name: {model_name}")
        self.logger.info(f"[WRAPPER_CHECK] Checking against prefixes: {new_models}")
        
        is_new_model = any(model_name.startswith(prefix) for prefix in new_models)
        
        if is_new_model:
            self.logger.info(f"[WRAPPER_CHECK] ✓ Detected new OpenAI model: {model_name}, will apply custom wrapper")
        else:
            self.logger.info(f"[WRAPPER_CHECK] ✗ Model {model_name} is not a new model, skipping wrapper")
        
        return is_new_model

    def _apply_custom_openai_wrapper(self):
        """カスタムOpenAILLMラッパーを適用"""
        self.logger.info("[WRAPPER_APPLY] Starting to apply custom OpenAI wrapper...")
        
        from .memos_wrapper import CocoroOpenAILLM
        from memos.llms.openai import OpenAILLM
        
        # 包括的にOpenAILLMインスタンスを検索して置き換え
        self._replace_all_openai_llms(self.mos, CocoroOpenAILLM, OpenAILLM)
        
        self.logger.info("[WRAPPER_APPLY] Custom wrapper application completed!")
    
    def _replace_all_openai_llms(self, obj, new_class, target_class, path="mos", visited=None):
        """オブジェクト内のすべてのOpenAILLMインスタンスを再帰的に検索して置き換え"""
        if visited is None:
            visited = set()
        
        # 無限ループ防止
        if id(obj) in visited:
            return
        visited.add(id(obj))
        
        # オブジェクトの属性をチェック
        if hasattr(obj, '__dict__'):
            for attr_name, attr_value in obj.__dict__.items():
                current_path = f"{path}.{attr_name}"
                
                # OpenAILLMインスタンスを発見した場合
                if isinstance(attr_value, target_class):
                    self.logger.info(f"[WRAPPER_REPLACE] Found OpenAILLM at {current_path}")
                    # 新しいインスタンスに置き換え
                    new_instance = new_class(attr_value.config)
                    setattr(obj, attr_name, new_instance)
                    self.logger.info(f"[WRAPPER_REPLACE] ✓ Replaced {current_path} with CocoroOpenAILLM")
                
                # リストやタプルの中もチェック
                elif type(attr_value) in (list, tuple):
                    for i, item in enumerate(attr_value):
                        if isinstance(item, target_class):
                            self.logger.info(f"[WRAPPER_REPLACE] Found OpenAILLM at {current_path}[{i}]")
                            new_instance = new_class(item.config)
                            if type(attr_value) is list:
                                attr_value[i] = new_instance
                            self.logger.info(f"[WRAPPER_REPLACE] ✓ Replaced {current_path}[{i}] with CocoroOpenAILLM")
                        else:
                            # リスト内のオブジェクトも再帰的にチェック
                            self._replace_all_openai_llms(item, new_class, target_class, f"{current_path}[{i}]", visited)
                
                # 辞書の中もチェック
                elif type(attr_value) is dict:
                    for key, value in attr_value.items():
                        if isinstance(value, target_class):
                            self.logger.info(f"[WRAPPER_REPLACE] Found OpenAILLM at {current_path}[{key}]")
                            new_instance = new_class(value.config)
                            attr_value[key] = new_instance
                            self.logger.info(f"[WRAPPER_REPLACE] ✓ Replaced {current_path}[{key}] with CocoroOpenAILLM")
                        else:
                            # 辞書内のオブジェクトも再帰的にチェック
                            self._replace_all_openai_llms(value, new_class, target_class, f"{current_path}[{key}]", visited)
                
                # その他のオブジェクトも再帰的にチェック（基本型は除外）
                elif type(attr_value) not in (str, int, float, bool, type(None)):
                    try:
                        self._replace_all_openai_llms(attr_value, new_class, target_class, current_path, visited)
                    except Exception as e:
                        # 再帰検索中のエラーは無視（循環参照など）
                        pass

    def _apply_wrapper_to_memcube(self, mem_cube):
        """個々のMemCube内のLLMにラッパーを適用"""
        from .memos_wrapper import CocoroOpenAILLM
        from memos.llms.openai import OpenAILLM
        
        if not self._should_use_custom_openai_wrapper():
            return
        
        cube_id = getattr(mem_cube, 'config', {})
        cube_id = getattr(cube_id, 'cube_id', 'unknown') if hasattr(cube_id, 'cube_id') else 'unknown'
        
        self.logger.info(f"[WRAPPER_APPLY] Applying wrapper to MemCube: {cube_id}")
        
        # MemCube全体に対して包括的な置き換えを実行
        self._replace_all_openai_llms(mem_cube, CocoroOpenAILLM, OpenAILLM, f"memcube.{cube_id}")

    async def startup(self):
        """アプリケーション起動処理"""
        try:
            self.logger.info("Starting CocoroCore2App...")

            # 既存MemCubeのAPIキーを設定ファイルから同期（Neo4j起動前に実行）
            self._sync_memcube_api_keys()


            # デフォルトユーザーを作成
            try:
                self.mos.create_user(user_id=self.default_user_id)
                self.logger.info(f"Default user created: {self.default_user_id}")
            except Exception as e:
                # ユーザーが既に存在する場合はエラーを無視
                self.logger.info(f"User {self.default_user_id} may already exist: {e}")

            # MemCube確実に作成
            self._ensure_user_memcube(self.default_user_id)

            self.is_running = True

            # MemOS高度機能の状態表示
            self._log_advanced_features_status()

            self.logger.info("CocoroCore2App startup completed")

        except Exception as e:
            self.logger.error(f"Failed to start CocoroCore2App: {e}")
            raise

    async def shutdown(self):
        """アプリケーション終了処理"""
        try:
            self.logger.info("Shutting down CocoroCore2App...")

            # Memory Scheduler停止処理（MemCube永続化前に実行）
            try:
                self.logger.info("Stopping Memory Scheduler...")
                scheduler = getattr(self.mos, 'mem_scheduler', None)
                if scheduler:
                    # Memory Schedulerを適切に停止
                    if hasattr(scheduler, 'stop'):
                        scheduler.stop()
                        self.logger.info("Memory Scheduler stopped successfully")
                    else:
                        self.logger.warning("Memory Scheduler has no stop method")
                else:
                    self.logger.info("Memory Scheduler was not active")
            except Exception as e:
                self.logger.error(f"Failed to stop Memory Scheduler: {e}")

            # MemCubeの永続化（Neo4j停止前に実行）
            try:
                self.logger.info("Persisting MemCubes...")

                # MOSに登録されている全MemCubeを永続化
                import os
                import shutil

                for mem_cube_id in self.mos.mem_cubes.keys():
                    cube_dir = f".memos/user_cubes/{mem_cube_id}"
                    try:
                        if os.path.exists(cube_dir):
                            shutil.rmtree(cube_dir)
                        self.mos.dump(cube_dir, mem_cube_id=mem_cube_id)

                    except Exception as e:
                        self.logger.error(f"Failed to persist MemCube {mem_cube_id}: {e}")

                self.logger.info("MemCube persistence completed")
            except Exception as e:
                self.logger.error(f"Failed to persist MemCubes: {e}")

            # Neo4j組み込みサービス停止（最後に実行：dump完了後）
            if self.neo4j_manager:
                try:
                    self.logger.info("Stopping embedded Neo4j service...")
                    await self.neo4j_manager.stop()
                    self.logger.info("Embedded Neo4j service stopped")
                except Exception as e:
                    self.logger.error(f"Failed to stop Neo4j service: {e}")

            self.is_running = False
            self.logger.info("CocoroCore2App shutdown completed")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    async def memos_chat(self, query: str, user_id: Optional[str] = None, context: Optional[Dict] = None, system_prompt: Optional[str] = None) -> str:
        """MemOS純正チャット処理（文脈依存クエリ対応・高速応答・非同期記憶保存）

        Args:
            query: ユーザーの質問
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            context: 追加コンテキスト情報
            system_prompt: システムプロンプト（キャラクター設定）

        Returns:
            str: AIの応答（記憶保存はバックグラウンドで実行）
        """
        try:
            # 有効なユーザーIDを決定
            effective_user_id = user_id or self.default_user_id

            # システムプロンプトを追加
            full_query = f"{system_prompt}\n\n{query}" if system_prompt else query

            # MOSでのチャット処理（応答生成）
            response = self.mos.chat(query=full_query, user_id=effective_user_id)

            # 応答ログ記録（デバッグ用）
            self.logger.info(f"Chat response: {len(response)} characters")

            # 記憶保存を非同期で実行（応答返却をブロックしない）
            messages = [{"role": "user", "content": query}, {"role": "assistant", "content": response}]
            asyncio.create_task(self._save_conversation_memory_async(messages, effective_user_id))

            self.logger.info(f"Completed chat processing for user {effective_user_id} (memory saving in background)")
            return response

        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            raise

    async def _save_conversation_memory_async(self, messages, user_id: str):
        """会話記憶の非同期保存処理（バックグラウンドタスク）"""
        try:
            self.logger.info(f"Starting memory save for user {user_id}")
            # asyncio.to_thread() を使用してブロッキング処理を別スレッドで実行
            await asyncio.to_thread(self.mos.add, messages=messages, user_id=user_id)
            self.logger.info(f"Memory saved successfully for user {user_id}")
        except Exception as e:
            self.logger.error(f"Failed to save memory for user {user_id}: {e}")
            # メモリ保存失敗は致命的ではないので例外は再発生させない

    def add_memory(self, content: str, user_id: Optional[str] = None, session_id: Optional[str] = None, **context) -> None:
        """記憶追加（スケジューラー連携付き）

        Args:
            content: 記憶内容
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            session_id: セッションID（オプション）
            **context: 追加コンテキスト情報
        """
        try:
            # 有効なユーザーIDを決定
            effective_user_id = user_id or self.default_user_id

            # messagesフォーマットで記憶を追加（memory_typeをより適切に制御するため）
            messages = [{"role": "user", "content": content}, {"role": "assistant", "content": "了解しました。この情報を記憶します。"}]

            # MOSAPIで記憶追加（messagesフォーマットを使用）
            self.mos.add(messages=messages, user_id=effective_user_id)

            self.logger.debug(f"Memory added: {len(content)} characters")

        except Exception as e:
            self.logger.error(f"Failed to add memory: {e}")
            # メモリ保存の失敗はチャット機能全体を停止させない

    def search_memory(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """記憶検索（同期）

        Args:
            query: 検索クエリ
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）

        Returns:
            Dict[str, Any]: 検索結果
        """
        try:
            # 有効なユーザーIDを決定
            effective_user_id = user_id or self.default_user_id

            # MOSAPIで検索
            result = self.mos.search(query=query, user_id=effective_user_id)

            self.logger.debug(f"Memory search completed: {len(str(result))} characters")
            return result

        except Exception as e:
            self.logger.error(f"Memory search failed: {e}")
            raise

    def get_user_memories(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """ユーザーの全記憶を取得

        Args:
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）

        Returns:
            Dict[str, Any]: 全記憶データ
        """
        try:
            # 有効なユーザーIDを決定
            effective_user_id = user_id or self.default_user_id

            # MOSAPIで全記憶取得
            result = self.mos.get_all(user_id=effective_user_id)

            self.logger.debug("Retrieved all memories")
            return result

        except Exception as e:
            self.logger.error(f"Failed to get memories: {e}")
            raise

    def ensure_user(self, user_id: str) -> None:
        """ユーザーの存在を確保（存在しない場合は作成）

        Args:
            user_id: ユーザーID
        """
        try:
            # ユーザーが既に存在するかチェック
            users = self.mos.list_users()
            user_exists = False
            for user in users:
                if user.get("user_id") == user_id:
                    user_exists = True
                    self.logger.debug(f"User {user_id} already exists")
                    break

            # ユーザーが存在しない場合は作成
            if not user_exists:
                self.mos.create_user(user_id=user_id)
                self.logger.info(f"Created new user: {user_id}")

            # MemCubeの確認と作成
            self._ensure_user_memcube(user_id)

        except Exception as e:
            self.logger.error(f"Failed to ensure user {user_id}: {e}")
            # ユーザー作成の失敗は致命的ではないので、警告ログのみ

    def _get_memcube_config_from_settings(self, user_id: str) -> dict:
        """設定ファイルからMemCube設定を動的に構築

        Args:
            user_id: ユーザーID

        Returns:
            dict: MemCube設定辞書
        """
        # 設定ファイルから必要な値を取得
        memos_config_data = generate_memos_config_from_setting(self.config)
        chat_model_config = memos_config_data["chat_model"]["config"]
        mem_reader_config = memos_config_data["mem_reader"]["config"]
        embedder_config = mem_reader_config["embedder"]["config"]
        # 保存されたNeo4j設定を再利用
        neo4j_settings = self.neo4j_settings
        self.logger.info(f"Using Neo4j URI for MemCube: {neo4j_settings.get('uri', 'NOT_SET')}")

        # ベクトル次元数を設定ファイルから取得、フォールバック付き
        embedder_model = embedder_config["model_name_or_path"]

        # モデルから次元数を推定
        if "text-embedding-3-large" in embedder_model:
            vector_dimension = 3072
        elif "text-embedding-3-small" in embedder_model:
            vector_dimension = 1536
        elif "text-embedding-ada-002" in embedder_model:
            vector_dimension = 1536
        else:
            # デフォルト値
            vector_dimension = 1536
            self.logger.warning(f"Unknown embedder model {embedder_model}, using default dimension {vector_dimension}")

        self.logger.debug(f"Generated MemCube config for user {user_id}")
        self.logger.debug(f"  - Embedder model: {embedder_model}")
        self.logger.debug(f"  - Vector dimension: {vector_dimension} (from {'config' if getattr(self.config, 'embedder_config', {}).get('vector_dimension') else 'model-based fallback'})")
        self.logger.debug(f"  - Chat model: {chat_model_config['model_name_or_path']}")

        # TreeTextMemory用のMemCube設定を構築
        cube_config = {
            "user_id": user_id,
            "cube_id": f"{user_id}_default_cube",
            "text_mem": {
                "backend": "tree_text",
                "config": {
                    "cube_id": f"{user_id}_default_cube",
                    "memory_filename": "tree_textual_memory.json",
                    "extractor_llm": {
                        "backend": memos_config_data["chat_model"]["backend"],
                        "config": {
                            "model_name_or_path": chat_model_config["model_name_or_path"],
                            "temperature": 0.0,  # Memory用は固定値
                            "api_key": chat_model_config["api_key"],
                            "api_base": chat_model_config.get("api_base", "https://api.openai.com/v1"),
                        },
                    },
                    "dispatcher_llm": {
                        "backend": memos_config_data["chat_model"]["backend"],
                        "config": {
                            "model_name_or_path": chat_model_config["model_name_or_path"],
                            "temperature": 0.0,  # Memory用は固定値
                            "api_key": chat_model_config["api_key"],
                            "api_base": chat_model_config.get("api_base", "https://api.openai.com/v1"),
                        },
                    },
                    "embedder": {
                        "backend": mem_reader_config["embedder"]["backend"],
                        "config": {"model_name_or_path": embedder_config["model_name_or_path"], "provider": embedder_config.get("provider", "openai"), "api_key": embedder_config["api_key"], "base_url": embedder_config.get("base_url", "https://api.openai.com/v1")},
                    },
                    "graph_db": {
                        "backend": "neo4j",
                        "config": {
                            "uri": neo4j_settings["uri"],  # Setting.jsonから動的生成された値
                            "user": "neo4j",  # 固定値（認証無効なので実際は使用されない）
                            "password": "password",  # 固定値（認証無効なので実際は使用されない）
                            "db_name": "neo4j",  # 固定値
                            "auto_create": False,  # Community Editionでは強制的に無効
                            "embedding_dimension": vector_dimension,  # モデルから動的算出
                        },
                    },
                    "reorganize": False,  # 初期は無効
                    # Internet Retrieval設定
                    "internet_retriever": self._get_internet_retriever_config(user_id) if self.config.enable_internet_retrieval else None,
                },
            },
            "act_mem": {},
            "para_mem": {},
        }

        self.logger.debug(f"Generated MemCube config for user {user_id}")
        self.logger.debug(f"  - Embedder model: {embedder_config['model_name_or_path']}")
        self.logger.debug(f"  - Vector dimension: {vector_dimension}")
        self.logger.debug(f"  - Chat model: {chat_model_config['model_name_or_path']}")
        
        # Internet Retrieval設定詳細ログ
        internet_config = cube_config["text_mem"]["config"].get("internet_retriever")
        self.logger.info(f"[NET] [MemCube] Internet Retrieval configured: {internet_config is not None}")
        if internet_config:
            self.logger.info(f"[NET] [MemCube] Internet backend: {internet_config.get('backend')}")
            self.logger.info(f"[NET] [MemCube] API key present: {bool(internet_config.get('config', {}).get('api_key'))}")
        else:
            self.logger.warning(f"[NET] [MemCube] Internet Retrieval disabled - enable setting: {self.config.enable_internet_retrieval}")

        return cube_config

    def _get_internet_retriever_config(self, user_id: str) -> dict:
        """Internet Retriever設定を生成

        Args:
            user_id: ユーザーID

        Returns:
            dict: Internet Retriever設定辞書
        """
        # Google API設定をCocoroAIConfigから取得
        google_api_key = self.config.googleApiKey
        google_search_engine_id = self.config.googleSearchEngineId
        max_results = self.config.internetMaxResults

        # 必須項目の確認
        if not google_api_key or not google_search_engine_id:
            self.logger.warning("Internet Retrieval requires Google API key and Search Engine ID")
            self.logger.warning(f"  - Google API Key: {'SET' if google_api_key else 'NOT SET'}")
            self.logger.warning(f"  - Search Engine ID: {'SET' if google_search_engine_id else 'NOT SET'}")
            return None

        # Internet Retriever設定を構築（MemOS GoogleCustomSearchConfig仕様）
        internet_config = {
            "backend": "google",
            "config": {
                "api_key": google_api_key,
                "search_engine_id": google_search_engine_id,  # GoogleCustomSearchConfigの正式パラメータ
                "max_results": max_results,
                "num_per_request": min(10, max_results),  # Google APIの制限（最大10）
            },
        }

        self.logger.debug(f"Generated Internet Retriever config for user {user_id}")
        self.logger.debug("  - Backend: google")
        self.logger.debug(f"  - Max results: {max_results}")

        return internet_config

    def _ensure_user_memcube(self, user_id: str) -> None:
        """ユーザーのMemCubeの存在を確保

        Args:
            user_id: ユーザーID
        """
        # 必要なインポート（再登録処理で使用）
        from memos.configs.mem_cube import GeneralMemCubeConfig
        from memos.mem_cube.general import GeneralMemCube

        try:
            # ユーザーの既存MemCubeをチェック
            user_cubes = self.mos.user_manager.get_user_cubes(user_id=user_id)

            if user_cubes and len(user_cubes) > 0:
                self.logger.debug(f"User {user_id} already has {len(user_cubes)} MemCube(s)")

                # 既存のMemCubeがMOSに登録されているか確認
                all_cubes_registered = True
                import os

                for cube in user_cubes:
                    cube_id = cube.cube_id
                    if cube_id not in self.mos.mem_cubes:
                        self.logger.info(f"Re-registering existing MemCube {cube_id} for user {user_id}")
                        try:
                            # TreeTextMemoryの場合、実際のデータはNeo4jに保存されている
                            # MemCubeディレクトリからのロードを試行
                            cube_path = f".memos/user_cubes/{cube_id}"

                            if os.path.exists(cube_path):
                                # パスから適切なcube_idを抽出してMemCubeをロード
                                mem_cube = GeneralMemCube.init_from_dir(cube_path)
                                # MemCubeオブジェクトを直接登録してIDの重複を回避
                                self.mos.register_mem_cube(mem_cube, user_id=user_id)
                                # 再登録されたMemCube内のLLMにもラッパーを適用
                                self._apply_wrapper_to_memcube(mem_cube)
                                self.logger.info(f"Successfully re-registered MemCube from {cube_path}")
                            else:
                                # MemCubeディレクトリが存在しない場合は新規作成が必要
                                self.logger.warning(f"MemCube directory not found: {cube_path}")
                                all_cubes_registered = False
                                break
                        except Exception as e:
                            self.logger.error(f"Failed to re-register MemCube {cube_id}: {e}")
                            all_cubes_registered = False
                            break
                    else:
                        self.logger.debug(f"MemCube {cube_id} is already registered in MOS")

                # 全てのMemCubeが正しく登録されている場合は終了
                if all_cubes_registered:
                    return

                # 登録に失敗したMemCubeがある場合は新しく作成
                self.logger.info(f"Creating new MemCube for user {user_id} due to registration failures")

            # デフォルトMemCubeを作成
            # 設定ファイルからMemCube設定を動的に構築
            cube_config_dict = self._get_memcube_config_from_settings(user_id)

            # GeneralMemCubeConfigを直接作成
            cube_config = GeneralMemCubeConfig.model_validate(cube_config_dict)

            # MemCubeを作成
            mem_cube = GeneralMemCube(cube_config)
            self.logger.info(f"Created MemCube with config cube_id: {cube_config.cube_id}")
            self.logger.info(f"Created MemCube actual cube_id: {mem_cube.config.cube_id}")

            # MOSにMemCubeを直接登録（メモリ内管理）
            self.mos.register_mem_cube(mem_cube, user_id=user_id)
            
            # 新しく作成されたMemCube内のLLMにもラッパーを適用
            self._apply_wrapper_to_memcube(mem_cube)

            # 登録後のMemCube確認
            registered_cubes = self.mos.user_manager.get_user_cubes(user_id)
            registered_cube_ids = [cube.cube_id for cube in registered_cubes]
            self.logger.info(f"Registered cubes for user {user_id}: {registered_cube_ids}")

            # MemCubeは正常にメモリ内に登録された（永続化はshutdown時に実行）
            self.logger.debug("MemCube registered in memory, persistence will be handled at shutdown")

            self.logger.info(f"Created and registered default MemCube for user: {user_id}")

        except Exception as e:
            import traceback

            self.logger.error(f"Failed to ensure MemCube for user {user_id}: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # MemCube作成の失敗は警告ログのみ

    def get_app_status(self) -> Dict[str, Any]:
        """アプリケーション状態を取得

        Returns:
            Dict[str, Any]: 状態情報
        """
        try:
            # セッション情報
            active_sessions = len(self.session_mapping)

            status = {
                "status": "healthy" if self.is_running else "stopped",
                "memory_type": "MemOS Full",
                "startup_time": self.startup_time.isoformat(),
                "active_sessions": active_sessions,
                "memos_status": {
                    "type": "full",
                    "backend": "configurable",
                    "default_user_id": self.default_user_id,
                    "sessions": active_sessions,
                },
            }

            return status

        except Exception as e:
            self.logger.error(f"Failed to get app status: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

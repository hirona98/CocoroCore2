"""
CocoroCore2 Core Application

"""

import os
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from memos.mem_os.main import MOS

from config import CocoroCore2Config, get_mos_config
from .core.text_memory_scheduler import TextMemorySchedulerManager


class CocoroCore2App:
    """正規版MOSを使用したCocoroCore2メインアプリケーション"""
    
    def __init__(self, config: CocoroCore2Config):
        """初期化
        
        Args:
            config: CocoroCore2設定
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 正規版MOS用の環境変数設定
        self._setup_memos_environment()
        
        # 正規版MOS初期化
        try:
            # MOSConfig作成
            mos_config = get_mos_config(config)
            self.mos = MOS(mos_config)
            
            # デフォルトユーザーID設定
            self.default_user_id = config.mos_config.get("user_id", "default")
            
            # デフォルトシステムプロンプト設定（キャラクター別）
            self.default_system_prompts = {
                "ココロ": "あなたは「ココロ」という名前のバーチャルアシスタントです。明るく元気で、ユーザーを励まし、サポートすることが大好きです。敬語を使いながらも親しみやすい話し方をします。",
                "さくら": "あなたは「さくら」という名前のバーチャルアシスタントです。落ち着いていて優しく、ユーザーの気持ちに寄り添うような話し方をします。丁寧で上品な言葉遣いを心がけています。",
                "みらい": "あなたは「みらい」という名前のバーチャルアシスタントです。好奇心旺盛で前向き、新しいことにチャレンジするのが好きです。フレンドリーでカジュアルな話し方をします。"
            }
            
            self.logger.info(f"正規版MOS initialized successfully with user_id: {self.default_user_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize MOS: {e}")
            raise
        
        # セッション管理（session_id -> user_id マッピング）
        self.session_mapping: Dict[str, str] = {}
        
        # アプリケーション状態
        self.is_running = False
        self.startup_time = datetime.now()
        
        # テキストメモリスケジューラー初期化
        self.text_memory_scheduler: Optional[TextMemorySchedulerManager] = None
        if config.mem_scheduler.enabled:
            try:
                self.text_memory_scheduler = TextMemorySchedulerManager(config)
                self.logger.info("Text memory scheduler manager created")
            except Exception as e:
                self.logger.error(f"Failed to create text memory scheduler manager: {e}")
                # スケジューラーエラーはアプリケーション全体を停止させない
                self.text_memory_scheduler = None
        else:
            self.logger.info("Text memory scheduler is disabled in configuration")
        
        self.logger.info("CocoroCore2App initialized with full MOS integration")
    
    def _setup_memos_environment(self):
        """正規版MOS用の環境変数を設定する"""
        try:
            # 設定ファイルからAPIキーを取得
            api_key = self.config.mos_config["chat_model"]["config"]["api_key"]
            
            # 環境変数設定
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["MOS_TEXT_MEM_TYPE"] = "general_text"
            
            # 必要に応じて他の環境変数も設定
            if "OPENAI_API_BASE" not in os.environ:
                # デフォルトのOpenAI API base URLを使用
                pass
            
            self.logger.info("MemOS environment variables configured")
            
        except Exception as e:
            self.logger.error(f"Failed to setup MemOS environment: {e}")
            raise
    
    def _get_chat_llm_from_mos(self):
        """MOSからchat_llmインスタンスを取得
        
        Returns:
            BaseLLM: チャット用LLMインスタンス
            
        Raises:
            RuntimeError: LLMインスタンスの取得に失敗した場合
        """
        try:
            # MOSのchat_llmを直接取得
            if hasattr(self.mos, 'chat_llm') and self.mos.chat_llm is not None:
                self.logger.debug("Retrieved chat_llm from MOS instance")
                return self.mos.chat_llm
            else:
                # フォールバック: MOSConfigから新しいLLMインスタンスを作成
                self.logger.warning("chat_llm not found in MOS, creating from config")
                from memos.llms.factory import LLMFactory
                from memos.configs.llm import LLMConfigFactory
                
                chat_model_config = self.config.mos_config["chat_model"]
                llm_config_factory = LLMConfigFactory(**chat_model_config)
                return LLMFactory.from_config(llm_config_factory)
                
        except Exception as e:
            self.logger.error(f"Failed to get chat LLM from MOS: {e}")
            raise RuntimeError(f"MOSからLLMインスタンスの取得に失敗しました: {e}")
    
    async def startup(self):
        """アプリケーション起動処理"""
        try:
            self.logger.info("Starting CocoroCore2App...")
            
            # デフォルトユーザーを作成
            try:
                self.mos.create_user(user_id=self.default_user_id)
                self.logger.info(f"Default user created: {self.default_user_id}")
            except Exception as e:
                # ユーザーが既に存在する場合はエラーを無視
                self.logger.info(f"User {self.default_user_id} may already exist: {e}")
            
            # テスト用のメモリ追加で動作確認
            try:
                test_content = f"System startup at {datetime.now().isoformat()}"
                self.mos.add(memory_content=test_content, user_id=self.default_user_id)
                self.logger.info("MemOS functionality verified")
            except Exception as e:
                self.logger.warning(f"MemOS test failed: {e}")
            
            # 音声処理パイプラインの初期化（将来実装）
            if self.config.speech.enabled:
                self.logger.info("Speech processing is enabled")
                # await self.voice_pipeline.initialize()
            
            # MCP統合の初期化（将来実装）
            if self.config.mcp.enabled:
                self.logger.info("MCP integration is enabled")
                # await self.mcp_tools.initialize()
            
            # テキストメモリスケジューラー初期化・開始
            if self.text_memory_scheduler:
                try:
                    self.logger.info("Initializing text memory scheduler...")
                    
                    # chat_llmを取得（MOSから）
                    chat_llm = self._get_chat_llm_from_mos()
                    self.text_memory_scheduler.initialize(chat_llm)
                    await self.text_memory_scheduler.start()
                    
                    self.logger.info("Text memory scheduler started successfully")
                except Exception as e:
                    self.logger.error(f"Failed to start text memory scheduler: {e}")
                    # スケジューラーエラーはアプリケーション全体を停止させない
                    self.text_memory_scheduler = None
            
            self.is_running = True
            self.logger.info("CocoroCore2App startup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to start CocoroCore2App: {e}")
            raise
    
    async def shutdown(self):
        """アプリケーション終了処理"""
        try:
            self.logger.info("Shutting down CocoroCore2App...")
            
            # テキストメモリスケジューラー停止
            if self.text_memory_scheduler and self.text_memory_scheduler.is_running:
                try:
                    self.logger.info("Stopping text memory scheduler...")
                    await self.text_memory_scheduler.stop()
                    self.logger.info("Text memory scheduler stopped")
                except Exception as e:
                    self.logger.error(f"Failed to stop text memory scheduler: {e}")
            
            # 各コンポーネントのクリーンアップ
            # 正規版MOSは特別なクリーンアップ不要
            
            # 音声処理パイプラインのクリーンアップ（将来実装）
            # await self.voice_pipeline.cleanup()
            
            # MCP統合のクリーンアップ（将来実装）
            # await self.mcp_tools.cleanup()
            
            self.is_running = False
            self.logger.info("CocoroCore2App shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def get_user_from_session(self, session_id: str, default_user_id: Optional[str] = None) -> str:
        """セッションIDからユーザーIDを取得する
        
        Args:
            session_id: セッションID
            default_user_id: デフォルトユーザーID
            
        Returns:
            str: ユーザーID
        """
        if session_id in self.session_mapping:
            return self.session_mapping[session_id]
        
        # セッションIDが未登録の場合、デフォルトユーザーIDを使用
        if default_user_id is None:
            default_user_id = self.default_user_id
        
        user_id = default_user_id
        self.session_mapping[session_id] = user_id
        
        self.logger.info(f"Mapped session {session_id} to user {user_id}")
        return user_id
    
    def memos_chat(self, query: str, user_id: Optional[str] = None, context: Optional[Dict] = None, system_prompt: Optional[str] = None) -> str:
        """MemOS純正チャット処理（同期）
        
        Args:
            query: ユーザーの質問
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            context: 追加コンテキスト情報
            system_prompt: システムプロンプト（キャラクター設定）
            
        Returns:
            str: AIの応答
        """
        try:
            # 有効なユーザーIDを決定
            effective_user_id = user_id or self.default_user_id
            
            # システムプロンプトを決定（指定されていない場合はキャラクター別のデフォルトを使用）
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
            
            # 正規版MOSでのチャット処理
            response = self.mos.chat(query=full_query, user_id=effective_user_id)
            
            self.logger.debug(f"Chat response: {len(response)} characters")
            return response
            
        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            raise
    
    def add_memory(self, content: str, user_id: Optional[str] = None, **context) -> None:
        """記憶追加（同期）
        
        Args:
            content: 記憶内容
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            **context: 追加コンテキスト情報
        """
        try:
            # 有効なユーザーIDを決定
            effective_user_id = user_id or self.default_user_id
            
            # コンテキスト情報を本文に含める
            memory_content = content
            if context:
                import json
                context_info = {
                    "character": self.config.character.name,
                    "timestamp": datetime.now().isoformat(),
                    **context
                }
                memory_content += f" | Context: {json.dumps(context_info)}"
            
            # 正規版MOSAPIで記憶追加
            self.mos.add(memory_content=memory_content, user_id=effective_user_id)
            self.logger.debug(f"Memory added: {len(content)} characters")
            
        except Exception as e:
            self.logger.error(f"Failed to add memory: {e}")
            # メモリ保存の失敗はチャット機能全体を停止させない
            self.logger.warning("Memory features may be temporarily disabled")
    
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
            
            # 正規版MOSAPIで検索
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
            
            # 正規版MOSAPIで全記憶取得
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
        mos_config = self.config.mos_config
        chat_model_config = mos_config["chat_model"]["config"]
        mem_reader_config = mos_config["mem_reader"]["config"]
        embedder_config = mem_reader_config["embedder"]["config"]
        
        # ベクトル次元数をembedderモデルから推定
        embedder_model = embedder_config["model_name_or_path"]
        if "text-embedding-3-large" in embedder_model:
            vector_dimension = 1536  # text-embedding-3-largeでも1536次元を使用
        elif "text-embedding-3-small" in embedder_model:
            vector_dimension = 1536
        elif "text-embedding-ada-002" in embedder_model:
            vector_dimension = 1536
        else:
            # デフォルト値
            vector_dimension = 1536
            self.logger.warning(f"Unknown embedder model {embedder_model}, using default dimension {vector_dimension}")
        
        # MemCube設定を構築
        cube_config = {
            "user_id": user_id,
            "cube_id": f"{user_id}_default_cube",
            "text_mem": {
                "backend": "general_text",
                "config": {
                    "cube_id": f"{user_id}_default_cube",
                    "memory_filename": "textual_memory.json",
                    "extractor_llm": {
                        "backend": mos_config["chat_model"]["backend"],
                        "config": {
                            "model_name_or_path": chat_model_config["model_name_or_path"],
                            "temperature": 0.0,  # Memory用は固定値
                            "api_key": chat_model_config["api_key"],
                            "api_base": chat_model_config.get("api_base", "https://api.openai.com/v1")
                        }
                    },
                    "embedder": {
                        "backend": mem_reader_config["embedder"]["backend"],
                        "config": {
                            "model_name_or_path": embedder_config["model_name_or_path"],
                            "provider": embedder_config.get("provider", "openai"),
                            "api_key": embedder_config["api_key"],
                            "base_url": embedder_config.get("base_url", "https://api.openai.com/v1")
                        }
                    },
                    "vector_db": {
                        "backend": "qdrant",
                        "config": {
                            "collection_name": f"{user_id}_collection",
                            "path": ".memos/qdrant",
                            "distance_metric": "cosine",
                            "vector_dimension": vector_dimension
                        }
                    }
                }
            },
            "act_mem": {},
            "para_mem": {}
        }
        
        self.logger.debug(f"Generated MemCube config for user {user_id}")
        self.logger.debug(f"  - Embedder model: {embedder_config['model_name_or_path']}")
        self.logger.debug(f"  - Vector dimension: {vector_dimension}")
        self.logger.debug(f"  - Chat model: {chat_model_config['model_name_or_path']}")
        
        return cube_config

    def _ensure_user_memcube(self, user_id: str) -> None:
        """ユーザーのMemCubeの存在を確保
        
        Args:
            user_id: ユーザーID
        """
        try:
            # ユーザーの既存MemCubeをチェック
            user_cubes = self.mos.user_manager.get_user_cubes(user_id=user_id)
            
            if user_cubes and len(user_cubes) > 0:
                self.logger.debug(f"User {user_id} already has {len(user_cubes)} MemCube(s)")
                
                # 既存のMemCubeがMOSに登録されているか確認
                all_cubes_registered = True
                for cube in user_cubes:
                    cube_id = cube.cube_id
                    if cube_id not in self.mos.mem_cubes:
                        self.logger.info(f"Re-registering existing MemCube {cube_id} for user {user_id}")
                        try:
                            # MemCubeをファイルから読み込んで再登録
                            from memos.mem_cube.general import GeneralMemCube
                            import os
                            cube_path = f".memos/user_cubes/{cube_id}"
                            if os.path.exists(cube_path):
                                self.mos.register_mem_cube(cube_path, user_id=user_id)
                                self.logger.info(f"Successfully re-registered MemCube {cube_id}")
                            else:
                                self.logger.warning(f"MemCube path not found: {cube_path}, will create new MemCube")
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
            from memos.configs.mem_cube import GeneralMemCubeConfig
            from memos.mem_cube.general import GeneralMemCube
            
            # 設定ファイルからMemCube設定を動的に構築
            cube_config_dict = self._get_memcube_config_from_settings(user_id)
            
            # GeneralMemCubeConfigを直接作成
            cube_config = GeneralMemCubeConfig.model_validate(cube_config_dict)
            
            # MemCubeを作成
            mem_cube = GeneralMemCube(cube_config)
            self.logger.info(f"Created MemCube with config cube_id: {cube_config.cube_id}")
            self.logger.info(f"Created MemCube actual cube_id: {mem_cube.config.cube_id}")
            
            # MOSにMemCubeを直接登録
            self.mos.register_mem_cube(mem_cube, user_id=user_id)
            
            # 登録後のMemCube確認
            registered_cubes = self.mos.user_manager.get_user_cubes(user_id)
            self.logger.info(f"Registered cubes for user {user_id}: {[cube.cube_id for cube in registered_cubes]}")
            
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
                "version": self.config.version,
                "character": self.config.character.name,
                "memory_enabled": True,
                "memory_type": "MemOS Full",
                "startup_time": self.startup_time.isoformat(),
                "active_sessions": active_sessions,
                "memos_status": {
                    "type": "full",
                    "backend": "configurable",
                    "default_user_id": self.default_user_id,
                    "sessions": active_sessions,
                },
                "features": {
                    "speech_enabled": self.config.speech.enabled,
                    "mcp_enabled": self.config.mcp.enabled,
                    "shell_integration": self.config.shell_integration.enabled,
                    "text_memory_scheduler_enabled": self.config.mem_scheduler.enabled,
                }
            }
            
            # スケジューラー情報を追加
            if self.text_memory_scheduler:
                status["scheduler_status"] = self.text_memory_scheduler.get_scheduler_status()
            else:
                status["scheduler_status"] = {
                    "initialized": False,
                    "running": False,
                    "enabled": self.config.mem_scheduler.enabled,
                    "available": False,
                    "reason": "scheduler not created"
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get app status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "version": self.config.version,
            }
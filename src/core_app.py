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
from .core.optimization_scheduler import OptimizationScheduler
from .core.neo4j_manager import Neo4jManager


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
        self.optimization_scheduler: Optional[OptimizationScheduler] = None
        
        # Neo4j組み込みサービス管理
        self.neo4j_manager: Optional[Neo4jManager] = None
        if config.neo4j.embedded_enabled:
            try:
                neo4j_config = {
                    "uri": config.neo4j.uri,
                    "user": config.neo4j.user,
                    "password": config.neo4j.password,
                    "db_name": config.neo4j.db_name,
                    "embedded_enabled": config.neo4j.embedded_enabled,
                    "java_home": config.neo4j.java_home,
                    "neo4j_home": config.neo4j.neo4j_home,
                    "startup_timeout": config.neo4j.startup_timeout
                }
                self.neo4j_manager = Neo4jManager(neo4j_config)
                self.logger.info("Neo4j manager created for embedded mode")
                
            except Exception as e:
                self.logger.error(f"Failed to create Neo4j manager: {e}")
                self.neo4j_manager = None
        else:
            self.logger.info("Embedded Neo4j is disabled, expecting external Neo4j instance")
        
        if config.mem_scheduler.enabled:
            try:
                self.text_memory_scheduler = TextMemorySchedulerManager(config)
                self.logger.info("Text memory scheduler manager created")
                
                # Phase 3: 自動最適化スケジューラー初期化
                if config.mem_scheduler.enable_auto_optimization:
                    self.optimization_scheduler = OptimizationScheduler(config, self.text_memory_scheduler)
                    self.logger.info("Optimization scheduler created")
                else:
                    self.logger.info("Auto optimization is disabled in configuration")
                    
            except Exception as e:
                self.logger.error(f"Failed to create text memory scheduler manager: {e}")
                # スケジューラーエラーはアプリケーション全体を停止させない
                self.text_memory_scheduler = None
                self.optimization_scheduler = None
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
            os.environ["MOS_TEXT_MEM_TYPE"] = "tree_text"
            
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
    
    async def startup(self):
        """アプリケーション起動処理"""
        try:
            self.logger.info("Starting CocoroCore2App...")
            
            # Neo4j組み込みサービス起動（MOSより前に起動）
            if self.neo4j_manager:
                self.logger.info("Starting embedded Neo4j service...")
                try:
                    neo4j_started = await self.neo4j_manager.start()
                    if neo4j_started:
                        self.logger.info("Embedded Neo4j service started successfully")
                    else:
                        self.logger.error("Failed to start embedded Neo4j service")
                        # Neo4j起動失敗は致命的エラーとして扱う（TreeTextMemoryに必要）
                        raise RuntimeError("Neo4j startup failed - required for TreeTextMemory")
                except Exception as e:
                    self.logger.error(f"Neo4j startup error: {e}")
                    raise
            else:
                self.logger.info("Embedded Neo4j is disabled - expecting external Neo4j")
            
            # デフォルトユーザーを作成
            try:
                self.mos.create_user(user_id=self.default_user_id)
                self.logger.info(f"Default user created: {self.default_user_id}")
            except Exception as e:
                # ユーザーが既に存在する場合はエラーを無視
                self.logger.info(f"User {self.default_user_id} may already exist: {e}")
            
            # MemCube確実に作成
            self._ensure_user_memcube(self.default_user_id)
            
            # テスト用のメモリ追加で動作確認
            try:
                test_content = f"System startup at {datetime.now().isoformat()}"
                self.mos.add(memory_content=test_content, user_id=self.default_user_id)
                self.logger.info("MemOS functionality verified")
            except Exception as e:
                self.logger.warning(f"MemOS test failed: {e}")
                # MemCube作成を再試行
                self.logger.info("Retrying MemCube creation...")
                self._ensure_user_memcube(self.default_user_id)
            
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
                    
                    # Phase 3: 自動最適化スケジューラー開始
                    if self.optimization_scheduler:
                        try:
                            self.logger.info("Starting optimization scheduler...")
                            
                            # 双方向連携を設定
                            self.text_memory_scheduler.set_optimization_scheduler(self.optimization_scheduler)
                            
                            await self.optimization_scheduler.start()
                            self.logger.info("Optimization scheduler started successfully")
                        except Exception as e:
                            self.logger.error(f"Failed to start optimization scheduler: {e}")
                            self.optimization_scheduler = None
                    
                except Exception as e:
                    self.logger.error(f"Failed to start text memory scheduler: {e}")
                    # スケジューラーエラーはアプリケーション全体を停止させない
                    self.text_memory_scheduler = None
                    self.optimization_scheduler = None
            
            self.is_running = True
            self.logger.info("CocoroCore2App startup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to start CocoroCore2App: {e}")
            raise
    
    async def shutdown(self):
        """アプリケーション終了処理"""
        try:
            self.logger.info("Shutting down CocoroCore2App...")
            
            # Phase 3: 自動最適化スケジューラー停止
            if self.optimization_scheduler and self.optimization_scheduler.is_running:
                try:
                    self.logger.info("Stopping optimization scheduler...")
                    await self.optimization_scheduler.stop()
                    self.logger.info("Optimization scheduler stopped")
                except Exception as e:
                    self.logger.error(f"Failed to stop optimization scheduler: {e}")
            
            # テキストメモリスケジューラー停止
            if self.text_memory_scheduler and self.text_memory_scheduler.is_running:
                try:
                    self.logger.info("Stopping text memory scheduler...")
                    await self.text_memory_scheduler.stop()
                    self.logger.info("Text memory scheduler stopped")
                except Exception as e:
                    self.logger.error(f"Failed to stop text memory scheduler: {e}")
            
            # MemCubeの永続化（Neo4j停止前に実行）
            try:
                self.logger.info("Persisting MemCubes...")
                
                # MOSに登録されている全MemCubeを永続化
                for mem_cube_id, mem_cube in self.mos.mem_cubes.items():
                    cube_dir = f".memos/user_cubes/{mem_cube_id}"
                    try:
                        # ディレクトリ作成とダンプ実行
                        import os
                        os.makedirs(cube_dir, exist_ok=True)
                        mem_cube.dump(cube_dir)
                        self.logger.info(f"MemCube {mem_cube_id} persisted to {cube_dir}")
                    except Exception as e:
                        self.logger.error(f"Failed to persist MemCube {mem_cube_id}: {e}")
                
                self.logger.info("MemCube persistence completed")
            except Exception as e:
                self.logger.error(f"Failed to persist MemCubes: {e}")
            
            # 各コンポーネントのクリーンアップ
            
            # 音声処理パイプラインのクリーンアップ（将来実装）
            # await self.voice_pipeline.cleanup()
            
            # MCP統合のクリーンアップ（将来実装）
            # await self.mcp_tools.cleanup()
            
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
            
            # スケジューラーにクエリメッセージを送信
            if (self.config.mem_scheduler.auto_submit_query and 
                self.text_memory_scheduler and 
                self.text_memory_scheduler.is_running):
                mem_cube = self._get_user_memcube(effective_user_id)
                if mem_cube:
                    self._safely_submit_to_scheduler(
                        "query_message",
                        self.text_memory_scheduler.submit_query_message,
                        user_id=effective_user_id,
                        content=query,  # 元のクエリ（システムプロンプトは含まない）
                        mem_cube=mem_cube
                    )
            
            # 正規版MOSでのチャット処理
            response = self.mos.chat(query=full_query, user_id=effective_user_id)
            
            # スケジューラーに応答メッセージを送信
            if (self.config.mem_scheduler.auto_submit_answer and 
                self.text_memory_scheduler and 
                self.text_memory_scheduler.is_running):
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
    
    def add_memory(self, content: str, user_id: Optional[str] = None, **context) -> None:
        """記憶追加（スケジューラー連携付き）
        
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
            
            # スケジューラーに記憶追加メッセージを送信
            if (self.config.mem_scheduler.enable_memory_integration and 
                self.text_memory_scheduler and 
                self.text_memory_scheduler.is_running):
                mem_cube = self._get_user_memcube(effective_user_id)
                if mem_cube:
                    self._safely_submit_to_scheduler(
                        "add_message",
                        self.text_memory_scheduler.submit_add_message,
                        user_id=effective_user_id,
                        content=content,  # 元のコンテンツ（コンテキスト情報は含まない）
                        mem_cube=mem_cube
                    )
            
            # Phase 3: 自動最適化スケジューラーに記憶追加を通知
            if self.optimization_scheduler and self.config.mem_scheduler.enable_auto_optimization:
                try:
                    self.optimization_scheduler.notify_memory_added(effective_user_id)
                    self.logger.debug(f"Notified optimization scheduler of memory addition for user {effective_user_id}")
                except Exception as e:
                    self.logger.error(f"Failed to notify optimization scheduler: {e}")
            
            self.logger.debug(f"Memory added: {len(content)} characters")
            
        except Exception as e:
            self.logger.error(f"Failed to add memory: {e}")
            # メモリ保存の失敗はチャット機能全体を停止させない

    # ===========================================
    # Phase 3: 最適化API機能
    # ===========================================
    
    async def optimize_memory(
        self, 
        user_id: Optional[str] = None, 
        optimization_type: str = "full",
        force_optimization: bool = False
    ) -> Dict[str, Any]:
        """手動最適化実行API
        
        Args:
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            optimization_type: 最適化タイプ ("full", "dedup", "quality", "rerank")
            force_optimization: 強制最適化フラグ
            
        Returns:
            Dict[str, Any]: 最適化結果
        """
        effective_user_id = user_id or self.default_user_id
        
        if not self.text_memory_scheduler:
            return {"success": False, "error": "Text memory scheduler not available"}
        
        try:
            result = await self.text_memory_scheduler.optimize_text_memory(
                user_id=effective_user_id,
                optimization_type=optimization_type,
                force_optimization=force_optimization
            )
            self.logger.info(f"Manual optimization completed for user {effective_user_id}: {optimization_type}")
            return result
        except Exception as e:
            self.logger.error(f"Manual optimization failed for user {effective_user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_optimization_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """最適化状態取得API
        
        Args:
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            
        Returns:
            Dict[str, Any]: 最適化状態情報
        """
        effective_user_id = user_id or self.default_user_id
        
        try:
            status = {}
            
            # テキストメモリスケジューラーの状態
            if self.text_memory_scheduler:
                scheduler_status = self.text_memory_scheduler.get_scheduler_status()
                status["text_memory_scheduler"] = scheduler_status
            else:
                status["text_memory_scheduler"] = {"available": False}
            
            # 自動最適化スケジューラーの状態
            if self.optimization_scheduler:
                optimization_status = self.optimization_scheduler.get_scheduler_status()
                status["optimization_scheduler"] = optimization_status
            else:
                status["optimization_scheduler"] = {"available": False}
            
            # ワーキングメモリの状態
            if self.text_memory_scheduler:
                try:
                    working_memory_status = self.text_memory_scheduler.get_working_memory_status(effective_user_id)
                    status["working_memory"] = working_memory_status
                except Exception as e:
                    status["working_memory"] = {"error": str(e)}
            else:
                status["working_memory"] = {"available": False}
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get optimization status for user {effective_user_id}: {e}")
            return {"error": str(e)}
    
    def analyze_memory(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """記憶分析API
        
        Args:
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            
        Returns:
            Dict[str, Any]: 記憶分析結果
        """
        effective_user_id = user_id or self.default_user_id
        
        if not self.text_memory_scheduler:
            return {"error": "Text memory scheduler not available"}
        
        try:
            # ワーキングメモリ状態
            working_memory_status = self.text_memory_scheduler.get_working_memory_status(effective_user_id)
            
            # 重複検出
            duplicate_analysis = self.text_memory_scheduler.detect_duplicate_memories(effective_user_id)
            
            # 品質分析
            quality_analysis = self.text_memory_scheduler.analyze_memory_quality(effective_user_id)
            
            return {
                "user_id": effective_user_id,
                "timestamp": datetime.now().isoformat(),
                "working_memory_status": working_memory_status,
                "duplicate_analysis": duplicate_analysis,
                "quality_analysis": quality_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Memory analysis failed for user {effective_user_id}: {e}")
            return {"error": str(e)}
    
    def force_optimization(
        self, 
        user_id: Optional[str] = None, 
        optimization_type: str = "full"
    ) -> Dict[str, Any]:
        """強制最適化トリガーAPI
        
        Args:
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            optimization_type: 最適化タイプ
            
        Returns:
            Dict[str, Any]: 操作結果
        """
        effective_user_id = user_id or self.default_user_id
        
        if not self.optimization_scheduler:
            return {"success": False, "error": "Optimization scheduler not available"}
        
        try:
            self.optimization_scheduler.force_optimization(effective_user_id, optimization_type)
            
            return {
                "success": True,
                "message": f"Forced optimization scheduled for user {effective_user_id}",
                "optimization_type": optimization_type,
                "user_id": effective_user_id
            }
            
        except Exception as e:
            self.logger.error(f"Force optimization failed for user {effective_user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def reset_memory_count(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """記憶カウントリセットAPI
        
        Args:
            user_id: ユーザーID（Noneの場合はデフォルトユーザーを使用）
            
        Returns:
            Dict[str, Any]: 操作結果
        """
        effective_user_id = user_id or self.default_user_id
        
        if not self.optimization_scheduler:
            return {"success": False, "error": "Optimization scheduler not available"}
        
        try:
            self.optimization_scheduler.reset_user_memory_count(effective_user_id)
            
            return {
                "success": True,
                "message": f"Memory count reset for user {effective_user_id}",
                "user_id": effective_user_id
            }
            
        except Exception as e:
            self.logger.error(f"Reset memory count failed for user {effective_user_id}: {e}")
            return {"success": False, "error": str(e)}
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
                        "backend": mos_config["chat_model"]["backend"],
                        "config": {
                            "model_name_or_path": chat_model_config["model_name_or_path"],
                            "temperature": 0.0,  # Memory用は固定値
                            "api_key": chat_model_config["api_key"],
                            "api_base": chat_model_config.get("api_base", "https://api.openai.com/v1")
                        }
                    },
                    "dispatcher_llm": {
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
                    "graph_db": {
                        "backend": "neo4j",
                        "config": {
                            "uri": self.config.neo4j.uri,
                            "user": self.config.neo4j.user,
                            "password": self.config.neo4j.password,
                            "db_name": self.config.neo4j.db_name,
                            "auto_create": False,  # Community Editionでは強制的に無効
                            "embedding_dimension": vector_dimension  # 動的に設定
                        }
                    },
                    "reorganize": False  # 初期は無効
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
            
            # MOSにMemCubeを直接登録（メモリ内管理）
            self.mos.register_mem_cube(mem_cube, user_id=user_id)
            
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
            else:
                status["scheduler_status"] = {
                    "initialized": False,
                    "running": False,
                    "enabled": self.config.mem_scheduler.enabled,
                    "available": False,
                    "reason": "scheduler not created",
                    "chat_integration_enabled": self.config.mem_scheduler.enable_chat_integration,
                    "memory_integration_enabled": self.config.mem_scheduler.enable_memory_integration,
                    "auto_submit_query": self.config.mem_scheduler.auto_submit_query,
                    "auto_submit_answer": self.config.mem_scheduler.auto_submit_answer,
                    "memcube_available": False
                }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get app status: {e}")
            return {
                "status": "error",
                "error": str(e),
                "version": self.config.version,
            }
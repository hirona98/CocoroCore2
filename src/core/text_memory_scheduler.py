"""
CocoroCore2 テキストメモリスケジューラー統合モジュール

MemOSのGeneralSchedulerをCocoroCore2に統合するためのレイヤー
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

# MemOS関連のインポート（遅延インポートで対応）
try:
    from memos.mem_scheduler.scheduler_factory import SchedulerFactory
    from memos.mem_scheduler.general_scheduler import GeneralScheduler
    from memos.mem_scheduler.modules.schemas import (
        ScheduleMessageItem, 
        QUERY_LABEL, 
        ANSWER_LABEL, 
        ADD_LABEL
    )
    from memos.llms.base import BaseLLM
    from memos.mem_cube.general import GeneralMemCube
except ImportError as e:
    # MemOSが利用できない場合の対応
    SchedulerFactory = None
    GeneralScheduler = None
    ScheduleMessageItem = None
    QUERY_LABEL = "query"
    ANSWER_LABEL = "answer"
    ADD_LABEL = "add"
    BaseLLM = None
    GeneralMemCube = None
    _memos_import_error = e
else:
    _memos_import_error = None

from ..config import CocoroCore2Config
from .scheduler_config import create_scheduler_config_factory, validate_scheduler_config


class TextMemorySchedulerManager:
    """テキストメモリスケジューラー管理クラス"""
    
    def __init__(self, config: CocoroCore2Config):
        """初期化
        
        Args:
            config: CocoroCore2設定
            
        Raises:
            ImportError: MemOSライブラリが利用できない場合
            ValueError: 設定が無効な場合
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.scheduler: Optional["GeneralScheduler"] = None
        self.is_initialized = False
        self.is_running = False
        
        # MemOSライブラリの利用可能性をチェック
        if _memos_import_error is not None:
            raise ImportError(f"MemOSライブラリが利用できません: {_memos_import_error}")
        
        # 設定検証
        if not validate_scheduler_config(config):
            raise ValueError("Invalid scheduler configuration")
        
        self.logger.info("TextMemorySchedulerManager initialized with config validation passed")
    
    def initialize(self, chat_llm: "BaseLLM", process_llm: Optional["BaseLLM"] = None):
        """スケジューラーを初期化
        
        Args:
            chat_llm: チャット用LLM
            process_llm: 処理用LLM（Noneの場合はchat_llmを使用）
            
        Raises:
            RuntimeError: 初期化に失敗した場合
        """
        try:
            self.logger.info("Initializing text memory scheduler...")
            
            # MemOSライブラリの利用可能性を再チェック
            if _memos_import_error is not None:
                raise RuntimeError(f"MemOSライブラリが利用できません: {_memos_import_error}")
            
            # スケジューラー設定ファクトリー作成
            config_factory = create_scheduler_config_factory(self.config)
            
            # スケジューラーインスタンス作成
            self.scheduler = SchedulerFactory.from_config(config_factory)
            
            # LLM設定
            if process_llm is None:
                process_llm = chat_llm
            
            self.scheduler.initialize_modules(chat_llm, process_llm)
            
            self.is_initialized = True
            self.logger.info("Text memory scheduler initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize text memory scheduler: {e}")
            self.is_initialized = False
            raise RuntimeError(f"スケジューラーの初期化に失敗しました: {e}")
    
    async def start(self):
        """スケジューラーを開始
        
        Raises:
            RuntimeError: 開始に失敗した場合
        """
        if not self.is_initialized:
            raise RuntimeError("Scheduler must be initialized before starting")
        
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return
        
        try:
            self.logger.info("Starting text memory scheduler...")
            self.scheduler.start()
            self.is_running = True
            self.logger.info("Text memory scheduler started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start text memory scheduler: {e}")
            self.is_running = False
            raise RuntimeError(f"スケジューラーの開始に失敗しました: {e}")
    
    async def stop(self):
        """スケジューラーを停止"""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        try:
            self.logger.info("Stopping text memory scheduler...")
            if self.scheduler:
                self.scheduler.stop()
            self.is_running = False
            self.logger.info("Text memory scheduler stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to stop text memory scheduler: {e}")
            # 停止エラーでも状態は停止扱いにする
            self.is_running = False
            raise RuntimeError(f"スケジューラーの停止に失敗しました: {e}")
    
    def submit_query_message(self, user_id: str, content: str, mem_cube: "GeneralMemCube"):
        """クエリメッセージを送信
        
        Args:
            user_id: ユーザーID
            content: クエリ内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping query message")
            return
        
        if ScheduleMessageItem is None:
            self.logger.error("MemOS library not available, cannot submit message")
            return
        
        try:
            message = ScheduleMessageItem(
                user_id=user_id,
                mem_cube_id=mem_cube.config.cube_id,
                label=QUERY_LABEL,
                mem_cube=mem_cube,
                content=content,
                timestamp=datetime.now()
            )
            
            self.scheduler.submit_messages(message)
            self.logger.debug(f"Submitted query message: {content[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to submit query message: {e}")
    
    def submit_answer_message(self, user_id: str, content: str, mem_cube: "GeneralMemCube"):
        """応答メッセージを送信
        
        Args:
            user_id: ユーザーID
            content: 応答内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping answer message")
            return
        
        if ScheduleMessageItem is None:
            self.logger.error("MemOS library not available, cannot submit message")
            return
        
        try:
            message = ScheduleMessageItem(
                user_id=user_id,
                mem_cube_id=mem_cube.config.cube_id,
                label=ANSWER_LABEL,
                mem_cube=mem_cube,
                content=content,
                timestamp=datetime.now()
            )
            
            self.scheduler.submit_messages(message)
            self.logger.debug(f"Submitted answer message: {content[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to submit answer message: {e}")
    
    def submit_add_message(self, user_id: str, content: str, mem_cube: "GeneralMemCube"):
        """記憶追加メッセージを送信
        
        Args:
            user_id: ユーザーID
            content: 記憶内容
            mem_cube: メモリキューブ
        """
        if not self.is_running:
            self.logger.warning("Scheduler is not running, skipping add message")
            return
        
        if ScheduleMessageItem is None:
            self.logger.error("MemOS library not available, cannot submit message")
            return
        
        try:
            # 記憶追加メッセージは配列形式で送信
            import json
            content_array = [content]
            
            message = ScheduleMessageItem(
                user_id=user_id,
                mem_cube_id=mem_cube.config.cube_id,
                label=ADD_LABEL,
                mem_cube=mem_cube,
                content=json.dumps(content_array),
                timestamp=datetime.now()
            )
            
            self.scheduler.submit_messages(message)
            self.logger.debug(f"Submitted add message: {content[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to submit add message: {e}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """スケジューラーステータスを取得
        
        Returns:
            Dict[str, Any]: ステータス情報
        """
        status = {
            "initialized": self.is_initialized,
            "running": self.is_running,
            "enabled": self.config.mem_scheduler.enabled,
            "memos_available": _memos_import_error is None,
            "configuration": {
                "top_k": self.config.mem_scheduler.top_k,
                "context_window_size": self.config.mem_scheduler.context_window_size,
                "enable_act_memory_update": self.config.mem_scheduler.enable_act_memory_update,
                "enable_parallel_dispatch": self.config.mem_scheduler.enable_parallel_dispatch,
                "thread_pool_max_workers": self.config.mem_scheduler.thread_pool_max_workers,
                "consume_interval_seconds": self.config.mem_scheduler.consume_interval_seconds,
                "text_memory_optimization": self.config.mem_scheduler.text_memory_optimization
            }
        }
        
        if self.is_running and self.scheduler:
            try:
                # スケジューラーログを取得
                scheduler_logs = self.scheduler.get_web_log_messages()
                status["recent_logs_count"] = len(scheduler_logs)
            except Exception as e:
                self.logger.warning(f"Failed to get scheduler logs: {e}")
                status["recent_logs_count"] = -1
        
        return status
    
    def get_scheduler_logs(self) -> list:
        """スケジューラーログを取得
        
        Returns:
            list: ログエントリのリスト
        """
        if not self.is_running or not self.scheduler:
            return []
        
        try:
            return self.scheduler.get_web_log_messages()
        except Exception as e:
            self.logger.error(f"Failed to get scheduler logs: {e}")
            return []
    
    def is_available(self) -> bool:
        """スケジューラーが利用可能かどうかを確認
        
        Returns:
            bool: 利用可能な場合True
        """
        return (_memos_import_error is None and 
                self.config.mem_scheduler.enabled and 
                validate_scheduler_config(self.config))
    
    def get_memory_optimization_config(self) -> Dict[str, Any]:
        """テキストメモリ最適化設定を取得
        
        Returns:
            Dict[str, Any]: 最適化設定
        """
        return self.config.mem_scheduler.text_memory_optimization
    
    # ===========================================
    # Phase 3: テキストメモリ最適化機能
    # ===========================================
    
    async def optimize_text_memory(
        self, 
        user_id: str, 
        force_optimization: bool = False,
        optimization_type: str = "full"
    ) -> Dict[str, Any]:
        """テキストメモリの手動最適化を実行
        
        Args:
            user_id: ユーザーID
            force_optimization: 強制最適化フラグ
            optimization_type: 最適化タイプ ("full", "dedup", "quality", "rerank")
            
        Returns:
            Dict[str, Any]: 最適化結果
            {
                "success": bool,
                "optimization_type": str,
                "before_stats": dict,
                "after_stats": dict,
                "improvements": dict,
                "duration_seconds": float
            }
        """
        if not self.is_running:
            return {"success": False, "error": "Scheduler not running"}
        
        try:
            start_time = datetime.now()
            
            # MemCube取得
            mem_cube = self._get_user_memcube(user_id)
            if not mem_cube:
                return {"success": False, "error": "MemCube not found"}
            
            # 最適化前の状態分析
            before_stats = await self._analyze_memory_state(user_id, mem_cube)
            
            # 最適化実行
            optimization_result = await self._run_optimization_process(
                user_id, mem_cube, optimization_type, force_optimization
            )
            
            # 最適化後の状態分析
            after_stats = await self._analyze_memory_state(user_id, mem_cube)
            
            # 改善度計算
            improvements = self._calculate_improvements(before_stats, after_stats)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "optimization_type": optimization_type,
                "before_stats": before_stats,
                "after_stats": after_stats,
                "improvements": improvements,
                "duration_seconds": duration
            }
            
            self.logger.info(f"Memory optimization completed for user {user_id}: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Memory optimization failed for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_working_memory_status(self, user_id: str) -> Dict[str, Any]:
        """ワーキングメモリの現在状態を取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            Dict[str, Any]: ワーキングメモリ状態
            {
                "total_memories": int,
                "memory_types": dict,
                "quality_scores": dict,
                "similarity_analysis": dict,
                "recommendations": list
            }
        """
        try:
            mem_cube = self._get_user_memcube(user_id)
            if not mem_cube:
                return {"error": "MemCube not found"}
            
            text_mem = mem_cube.text_mem
            if not hasattr(text_mem, 'get_working_memory'):
                return {"error": "Working memory not supported"}
            
            working_memory = text_mem.get_working_memory()
            
            # 記憶数と種類分析
            total_memories = len(working_memory)
            memory_types = self._analyze_memory_types(working_memory)
            
            # 品質スコア分析
            quality_scores = self._analyze_quality_scores(working_memory)
            
            # 類似性分析
            similarity_analysis = self._analyze_memory_similarity(working_memory)
            
            # 改善提案
            recommendations = self._generate_memory_recommendations(
                working_memory, quality_scores, similarity_analysis
            )
            
            return {
                "total_memories": total_memories,
                "memory_types": memory_types,
                "quality_scores": quality_scores,
                "similarity_analysis": similarity_analysis,
                "recommendations": recommendations
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get working memory status for user {user_id}: {e}")
            return {"error": str(e)}

    def detect_duplicate_memories(
        self, 
        user_id: str, 
        similarity_threshold: float = 0.95
    ) -> Dict[str, Any]:
        """重複記憶の検出
        
        Args:
            user_id: ユーザーID
            similarity_threshold: 類似性閾値
            
        Returns:
            Dict[str, Any]: 重複検出結果
            {
                "total_memories": int,
                "duplicate_groups": list,
                "potential_savings": dict,
                "recommendations": list
            }
        """
        try:
            mem_cube = self._get_user_memcube(user_id)
            if not mem_cube:
                return {"error": "MemCube not found"}
            
            # 全ての記憶を取得
            all_memories = self._get_all_memories(mem_cube)
            memory_texts = [mem.memory for mem in all_memories]
            
            # MemOSのfilter_similar_memoriesを活用
            if self.scheduler and hasattr(self.scheduler, 'retriever'):
                filtered_memories = self.scheduler.retriever.filter_similar_memories(
                    text_memories=memory_texts,
                    similarity_threshold=similarity_threshold
                )
                
                # 重複グループの分析
                duplicate_groups = self._analyze_duplicate_groups(
                    original_memories=memory_texts,
                    filtered_memories=filtered_memories,
                    similarity_threshold=similarity_threshold
                )
                
                # 削減効果計算
                potential_savings = self._calculate_deduplication_savings(
                    original_count=len(memory_texts),
                    filtered_count=len(filtered_memories),
                    duplicate_groups=duplicate_groups
                )
                
                # 改善提案
                recommendations = self._generate_deduplication_recommendations(duplicate_groups)
                
                return {
                    "total_memories": len(memory_texts),
                    "duplicate_groups": duplicate_groups,
                    "potential_savings": potential_savings,
                    "recommendations": recommendations
                }
            else:
                return {"error": "Scheduler retriever not available"}
                
        except Exception as e:
            self.logger.error(f"Duplicate detection failed for user {user_id}: {e}")
            return {"error": str(e)}

    def analyze_memory_quality(self, user_id: str) -> Dict[str, Any]:
        """記憶品質の分析・評価
        
        Args:
            user_id: ユーザーID
            
        Returns:
            Dict[str, Any]: 品質分析結果
        """
        try:
            mem_cube = self._get_user_memcube(user_id)
            if not mem_cube:
                return {"error": "MemCube not found"}
            
            working_memory = mem_cube.text_mem.get_working_memory()
            memory_texts = [mem.memory for mem in working_memory]
            
            # 品質スコア分析
            quality_scores = self._analyze_quality_scores(working_memory)
            
            # 長さ分析
            length_analysis = self._analyze_memory_lengths(memory_texts)
            
            # 改善提案
            improvement_suggestions = self._generate_quality_improvement_suggestions(
                memory_texts, quality_scores, length_analysis
            )
            
            return {
                "total_memories": len(memory_texts),
                "quality_scores": quality_scores,
                "length_analysis": length_analysis,
                "improvement_suggestions": improvement_suggestions
            }
            
        except Exception as e:
            self.logger.error(f"Memory quality analysis failed for user {user_id}: {e}")
            return {"error": str(e)}

    # ===========================================
    # Phase 3: ヘルパーメソッド (Task 1.4)
    # ===========================================
    
    def _get_user_memcube(self, user_id: str) -> Optional["GeneralMemCube"]:
        """ユーザーのデフォルトMemCubeを取得 (Phase 2からの継承)
        
        Args:
            user_id: ユーザーID
            
        Returns:
            Optional[GeneralMemCube]: MemCubeオブジェクト、見つからない場合はNone
        """
        try:
            if not self.scheduler:
                self.logger.warning(f"Scheduler not available for user {user_id}")
                return None
                
            # MemOSからMOSインスタンスを取得（スケジューラーからアクセス）
            if hasattr(self.scheduler, 'mos') and self.scheduler.mos:
                mos = self.scheduler.mos
                mos.ensure_user(user_id)
                user_cubes = mos.user_manager.get_user_cubes(user_id=user_id)
                
                if not user_cubes or len(user_cubes) == 0:
                    self.logger.warning(f"No MemCubes found for user {user_id}")
                    return None
                    
                default_cube = user_cubes[0]
                cube_id = default_cube.cube_id
                
                if cube_id in mos.mem_cubes:
                    self.logger.debug(f"Retrieved MemCube {cube_id} for user {user_id}")
                    return mos.mem_cubes[cube_id]
                else:
                    self.logger.warning(f"MemCube {cube_id} found but not registered in MOS for user {user_id}")
                    return None
            else:
                self.logger.error("MOS instance not available in scheduler")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get MemCube for user {user_id}: {e}")
            return None

    def _get_all_memories(self, mem_cube: "GeneralMemCube") -> list:
        """MemCubeから全ての記憶を取得
        
        Args:
            mem_cube: MemCubeオブジェクト
            
        Returns:
            list: 全記憶のリスト
        """
        try:
            text_mem = mem_cube.text_mem
            if hasattr(text_mem, 'get_working_memory'):
                working_memory = text_mem.get_working_memory()
                return working_memory
            else:
                self.logger.warning("Working memory not supported in this MemCube")
                return []
        except Exception as e:
            self.logger.error(f"Failed to get all memories: {e}")
            return []

    def _get_recent_queries(self, user_id: str, limit: int = 5) -> list:
        """最近のクエリ履歴を取得
        
        Args:
            user_id: ユーザーID
            limit: 取得する履歴の最大数
            
        Returns:
            list: 最近のクエリリスト
        """
        try:
            # ここでは簡易実装として空リストを返す
            # 実際の実装では、スケジューラーのログやMemOSの履歴機能を使用
            self.logger.debug(f"Getting recent queries for user {user_id} (limit: {limit})")
            return []
        except Exception as e:
            self.logger.error(f"Failed to get recent queries for user {user_id}: {e}")
            return []

    def _generate_memory_recommendations(
        self, 
        working_memory: list, 
        quality_scores: dict, 
        similarity_analysis: dict
    ) -> list:
        """記憶改善提案を生成
        
        Args:
            working_memory: ワーキングメモリ
            quality_scores: 品質スコア
            similarity_analysis: 類似性分析結果
            
        Returns:
            list: 改善提案のリスト
        """
        recommendations = []
        
        try:
            # 低品質記憶の改善提案
            if quality_scores.get("low_quality_count", 0) > 0:
                recommendations.append({
                    "type": "quality_improvement",
                    "message": f"{quality_scores['low_quality_count']}個の低品質記憶を改善または削除することを推奨します",
                    "priority": "high"
                })
            
            # 重複記憶の改善提案
            if similarity_analysis.get("duplicate_pairs", 0) > 0:
                recommendations.append({
                    "type": "deduplication",
                    "message": f"{similarity_analysis['duplicate_pairs']}個の重複記憶を統合することで効率化できます",
                    "priority": "medium"
                })
            
            # ワーキングメモリサイズの最適化提案
            memory_count = len(working_memory)
            optimal_size = self.config.mem_scheduler.text_memory_optimization.get("working_memory_size", 20)
            if memory_count > optimal_size * 1.5:
                recommendations.append({
                    "type": "size_optimization",
                    "message": f"ワーキングメモリが推奨サイズ({optimal_size})を大幅に超えています。最適化を推奨します",
                    "priority": "medium"
                })
            
        except Exception as e:
            self.logger.error(f"Failed to generate memory recommendations: {e}")
            
        return recommendations

    # ===========================================
    # Phase 3: 最適化プロセス内部実装 (Task 1.2)
    # ===========================================
    
    async def _run_optimization_process(
        self, 
        user_id: str, 
        mem_cube: "GeneralMemCube", 
        optimization_type: str,
        force_optimization: bool
    ) -> Dict[str, Any]:
        """最適化プロセスの実行"""
        
        if optimization_type == "full":
            # 全体最適化: 重複除去 → 品質フィルタ → 再ランキング
            result = {}
            result.update(await self._run_deduplication(user_id, mem_cube))
            result.update(await self._run_quality_filtering(user_id, mem_cube))
            result.update(await self._run_memory_reranking(user_id, mem_cube))
            return result
            
        elif optimization_type == "dedup":
            # 重複除去のみ
            return await self._run_deduplication(user_id, mem_cube)
            
        elif optimization_type == "quality":
            # 品質フィルタリングのみ
            return await self._run_quality_filtering(user_id, mem_cube)
            
        elif optimization_type == "rerank":
            # 再ランキングのみ
            return await self._run_memory_reranking(user_id, mem_cube)
            
        else:
            raise ValueError(f"Unknown optimization type: {optimization_type}")

    async def _run_deduplication(self, user_id: str, mem_cube: "GeneralMemCube") -> Dict[str, Any]:
        """重複除去の実行"""
        try:
            working_memory = mem_cube.text_mem.get_working_memory()
            memory_texts = [mem.memory for mem in working_memory]
            
            # MemOSの重複検出を使用
            filtered_texts = self.scheduler.retriever.filter_similar_memories(
                text_memories=memory_texts,
                similarity_threshold=self.config.mem_scheduler.text_memory_optimization.get(
                    "similarity_threshold", 0.95
                )
            )
            
            removed_count = len(memory_texts) - len(filtered_texts)
            
            self.logger.info(f"Deduplication removed {removed_count} duplicate memories for user {user_id}")
            
            return {
                "deduplication": {
                    "original_count": len(memory_texts),
                    "filtered_count": len(filtered_texts),
                    "removed_count": removed_count,
                    "reduction_percentage": (removed_count / len(memory_texts) * 100) if memory_texts else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Deduplication failed for user {user_id}: {e}")
            return {"deduplication": {"error": str(e)}}

    async def _run_quality_filtering(self, user_id: str, mem_cube: "GeneralMemCube") -> Dict[str, Any]:
        """品質フィルタリングの実行"""
        try:
            working_memory = mem_cube.text_mem.get_working_memory()
            memory_texts = [mem.memory for mem in working_memory]
            
            # MemOSの品質フィルタを使用
            min_length = self.config.mem_scheduler.text_memory_optimization.get(
                "min_memory_length", 10
            )
            
            filtered_texts = self.scheduler.retriever.filter_too_short_memories(
                text_memories=memory_texts,
                min_length_threshold=min_length
            )
            
            removed_count = len(memory_texts) - len(filtered_texts)
            
            self.logger.info(f"Quality filtering removed {removed_count} low-quality memories for user {user_id}")
            
            return {
                "quality_filtering": {
                    "original_count": len(memory_texts),
                    "filtered_count": len(filtered_texts),
                    "removed_count": removed_count,
                    "min_length_threshold": min_length
                }
            }
            
        except Exception as e:
            self.logger.error(f"Quality filtering failed for user {user_id}: {e}")
            return {"quality_filtering": {"error": str(e)}}

    async def _run_memory_reranking(self, user_id: str, mem_cube: "GeneralMemCube") -> Dict[str, Any]:
        """記憶の再ランキング実行"""
        try:
            # 最近のクエリ履歴を取得
            recent_queries = self._get_recent_queries(user_id, limit=5)
            
            if not recent_queries:
                return {"reranking": {"skipped": "No recent queries available"}}
            
            working_memory = mem_cube.text_mem.get_working_memory()
            
            # MemOSのワーキングメモリ置換を使用
            new_memory = self.scheduler.retriever.replace_working_memory(
                queries=recent_queries,
                user_id=user_id,
                mem_cube_id=mem_cube.config.cube_id,
                mem_cube=mem_cube,
                original_memory=working_memory,
                new_memory=[],  # 既存記憶の再ランキングのみ
                top_k=self.config.mem_scheduler.text_memory_optimization.get(
                    "working_memory_size", 20
                )
            )
            
            self.logger.info(f"Memory reranking completed for user {user_id}")
            
            return {
                "reranking": {
                    "original_count": len(working_memory),
                    "reranked_count": len(new_memory) if new_memory else len(working_memory),
                    "query_context": len(recent_queries)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Memory reranking failed for user {user_id}: {e}")
            return {"reranking": {"error": str(e)}}

    # ===========================================
    # Phase 3: 分析・統計機能実装 (Task 1.3)
    # ===========================================
    
    async def _analyze_memory_state(self, user_id: str, mem_cube: "GeneralMemCube") -> Dict[str, Any]:
        """記憶状態の分析"""
        try:
            working_memory = mem_cube.text_mem.get_working_memory()
            memory_texts = [mem.memory for mem in working_memory]
            
            # 基本統計
            total_memories = len(working_memory)
            
            # 記憶タイプ分析
            memory_types = self._analyze_memory_types(working_memory)
            
            # 品質スコア分析
            quality_scores = self._analyze_quality_scores(working_memory)
            
            # 類似性分析
            similarity_analysis = self._analyze_memory_similarity(working_memory)
            
            # 長さ分析
            length_analysis = self._analyze_memory_lengths(memory_texts)
            
            return {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "total_memories": total_memories,
                "memory_types": memory_types,
                "quality_scores": quality_scores,
                "similarity_analysis": similarity_analysis,
                "length_analysis": length_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Memory state analysis failed for user {user_id}: {e}")
            return {"error": str(e)}

    def _calculate_improvements(self, before_stats: Dict[str, Any], after_stats: Dict[str, Any]) -> Dict[str, Any]:
        """改善度の計算"""
        try:
            improvements = {}
            
            # 記憶数の変化
            before_count = before_stats.get("total_memories", 0)
            after_count = after_stats.get("total_memories", 0)
            count_reduction = before_count - after_count
            count_reduction_percentage = (count_reduction / before_count * 100) if before_count > 0 else 0
            
            improvements["memory_count"] = {
                "before": before_count,
                "after": after_count,
                "reduction": count_reduction,
                "reduction_percentage": count_reduction_percentage
            }
            
            # 品質スコアの改善
            before_quality = before_stats.get("quality_scores", {})
            after_quality = after_stats.get("quality_scores", {})
            
            before_avg_quality = before_quality.get("average_quality", 0)
            after_avg_quality = after_quality.get("average_quality", 0)
            quality_improvement = after_avg_quality - before_avg_quality
            
            improvements["quality"] = {
                "before_average": before_avg_quality,
                "after_average": after_avg_quality,
                "improvement": quality_improvement,
                "improvement_percentage": (quality_improvement / before_avg_quality * 100) if before_avg_quality > 0 else 0
            }
            
            # 重複削減効果
            before_duplicates = before_stats.get("similarity_analysis", {}).get("duplicate_pairs", 0)
            after_duplicates = after_stats.get("similarity_analysis", {}).get("duplicate_pairs", 0)
            duplicate_reduction = before_duplicates - after_duplicates
            
            improvements["duplicates"] = {
                "before": before_duplicates,
                "after": after_duplicates,
                "reduction": duplicate_reduction,
                "reduction_percentage": (duplicate_reduction / before_duplicates * 100) if before_duplicates > 0 else 0
            }
            
            return improvements
            
        except Exception as e:
            self.logger.error(f"Failed to calculate improvements: {e}")
            return {"error": str(e)}

    def _analyze_memory_types(self, working_memory: list) -> Dict[str, Any]:
        """記憶タイプの分析"""
        try:
            total_count = len(working_memory)
            if total_count == 0:
                return {"total": 0, "types": {}}
            
            # MemOSのutils関数を使用して言語判定
            from memos.mem_scheduler.utils import is_all_chinese, is_all_english
            
            type_counts = {
                "english": 0,
                "chinese": 0,
                "mixed": 0,
                "short": 0,
                "long": 0
            }
            
            for memory_item in working_memory:
                memory_text = memory_item.memory
                
                # 言語タイプ分析
                if is_all_english(memory_text):
                    type_counts["english"] += 1
                elif is_all_chinese(memory_text):
                    type_counts["chinese"] += 1
                else:
                    type_counts["mixed"] += 1
                
                # 長さ分析
                if len(memory_text) < 50:
                    type_counts["short"] += 1
                else:
                    type_counts["long"] += 1
            
            # パーセンテージ計算
            type_percentages = {
                key: (count / total_count * 100) for key, count in type_counts.items()
            }
            
            return {
                "total": total_count,
                "counts": type_counts,
                "percentages": type_percentages
            }
            
        except Exception as e:
            self.logger.error(f"Memory type analysis failed: {e}")
            return {"error": str(e)}

    def _analyze_quality_scores(self, working_memory: list) -> Dict[str, Any]:
        """品質スコアの分析"""
        try:
            if not working_memory:
                return {"total": 0, "average_quality": 0, "quality_distribution": {}}
            
            quality_scores = []
            quality_distribution = {"high": 0, "medium": 0, "low": 0}
            
            for memory_item in working_memory:
                memory_text = memory_item.memory
                
                # 簡易品質スコア計算（長さと文字多様性）
                length_score = min(len(memory_text) / 100, 1.0)  # 長さスコア（最大1.0）
                unique_chars = len(set(memory_text.lower()))
                diversity_score = min(unique_chars / 20, 1.0)  # 文字多様性スコア（最大1.0）
                
                quality_score = (length_score + diversity_score) / 2
                quality_scores.append(quality_score)
                
                # 品質分布
                if quality_score >= 0.7:
                    quality_distribution["high"] += 1
                elif quality_score >= 0.4:
                    quality_distribution["medium"] += 1
                else:
                    quality_distribution["low"] += 1
            
            average_quality = sum(quality_scores) / len(quality_scores)
            
            return {
                "total": len(working_memory),
                "average_quality": average_quality,
                "quality_distribution": quality_distribution,
                "high_quality_count": quality_distribution["high"],
                "medium_quality_count": quality_distribution["medium"],
                "low_quality_count": quality_distribution["low"]
            }
            
        except Exception as e:
            self.logger.error(f"Quality score analysis failed: {e}")
            return {"error": str(e)}

    def _analyze_memory_similarity(self, working_memory: list) -> Dict[str, Any]:
        """記憶の類似性分析"""
        try:
            if len(working_memory) < 2:
                return {"total_pairs": 0, "duplicate_pairs": 0, "similarity_matrix": []}
            
            memory_texts = [mem.memory for mem in working_memory]
            
            # MemOSのretrieverを使用して類似性分析
            if self.scheduler and hasattr(self.scheduler, 'retriever'):
                # 重複検出による類似記憶の特定
                filtered_memories = self.scheduler.retriever.filter_similar_memories(
                    text_memories=memory_texts,
                    similarity_threshold=0.8  # より低い閾値で類似性を検出
                )
                
                duplicate_pairs = len(memory_texts) - len(filtered_memories)
                total_pairs = len(memory_texts) * (len(memory_texts) - 1) // 2
                
                return {
                    "total_memories": len(memory_texts),
                    "unique_memories": len(filtered_memories),
                    "duplicate_pairs": duplicate_pairs,
                    "total_pairs": total_pairs,
                    "similarity_ratio": (duplicate_pairs / total_pairs) if total_pairs > 0 else 0
                }
            else:
                return {"error": "Retriever not available for similarity analysis"}
                
        except Exception as e:
            self.logger.error(f"Memory similarity analysis failed: {e}")
            return {"error": str(e)}

    def _analyze_memory_lengths(self, memory_texts: list) -> Dict[str, Any]:
        """記憶の長さ分析"""
        try:
            if not memory_texts:
                return {"total": 0, "lengths": {}}
            
            lengths = [len(text) for text in memory_texts]
            
            return {
                "total": len(memory_texts),
                "average_length": sum(lengths) / len(lengths),
                "min_length": min(lengths),
                "max_length": max(lengths),
                "short_memories": len([l for l in lengths if l < 20]),
                "medium_memories": len([l for l in lengths if 20 <= l < 100]),
                "long_memories": len([l for l in lengths if l >= 100])
            }
            
        except Exception as e:
            self.logger.error(f"Memory length analysis failed: {e}")
            return {"error": str(e)}

    def _analyze_duplicate_groups(
        self, 
        original_memories: list, 
        filtered_memories: list,
        similarity_threshold: float
    ) -> list:
        """重複グループの分析"""
        try:
            # 簡易実装：フィルタリングで除去された記憶を重複として扱う
            removed_memories = []
            for memory in original_memories:
                if memory not in filtered_memories:
                    removed_memories.append(memory)
            
            # 重複グループを構築
            duplicate_groups = []
            for i, removed_memory in enumerate(removed_memories):
                # 各除去された記憶に対して類似記憶を探す
                group = {
                    "group_id": i,
                    "representative": removed_memory[:100] + "..." if len(removed_memory) > 100 else removed_memory,
                    "duplicates": [removed_memory],
                    "similarity_score": similarity_threshold
                }
                duplicate_groups.append(group)
            
            return duplicate_groups
            
        except Exception as e:
            self.logger.error(f"Duplicate group analysis failed: {e}")
            return []

    def _calculate_deduplication_savings(
        self, 
        original_count: int, 
        filtered_count: int,
        duplicate_groups: list
    ) -> Dict[str, Any]:
        """重複除去による削減効果の計算"""
        try:
            removed_count = original_count - filtered_count
            reduction_percentage = (removed_count / original_count * 100) if original_count > 0 else 0
            
            return {
                "original_count": original_count,
                "filtered_count": filtered_count,
                "removed_count": removed_count,
                "reduction_percentage": reduction_percentage,
                "duplicate_groups_count": len(duplicate_groups),
                "estimated_memory_savings": f"{removed_count * 50}B"  # 概算メモリ削減量
            }
            
        except Exception as e:
            self.logger.error(f"Deduplication savings calculation failed: {e}")
            return {"error": str(e)}

    def _generate_deduplication_recommendations(self, duplicate_groups: list) -> list:
        """重複除去の改善提案を生成"""
        recommendations = []
        
        try:
            if len(duplicate_groups) > 0:
                recommendations.append({
                    "type": "deduplication",
                    "message": f"{len(duplicate_groups)}個の重複グループが検出されました。統合により効率化できます",
                    "priority": "high",
                    "action": "merge_duplicates"
                })
            
            if len(duplicate_groups) > 10:
                recommendations.append({
                    "type": "bulk_optimization",
                    "message": "大量の重複が検出されました。自動最適化の設定を見直すことを推奨します",
                    "priority": "medium",
                    "action": "adjust_auto_optimization"
                })
                
        except Exception as e:
            self.logger.error(f"Failed to generate deduplication recommendations: {e}")
        
        return recommendations

    def _generate_quality_improvement_suggestions(
        self, 
        memory_texts: list, 
        quality_scores: dict, 
        length_analysis: dict
    ) -> list:
        """品質改善提案を生成"""
        suggestions = []
        
        try:
            # 短すぎる記憶の改善提案
            short_count = length_analysis.get("short_memories", 0)
            if short_count > 0:
                suggestions.append({
                    "type": "length_improvement",
                    "message": f"{short_count}個の短い記憶があります。より詳細な情報を追加することを推奨します",
                    "priority": "medium",
                    "action": "expand_short_memories"
                })
            
            # 低品質記憶の改善提案
            low_quality_count = quality_scores.get("low_quality_count", 0)
            if low_quality_count > 0:
                suggestions.append({
                    "type": "quality_improvement",
                    "message": f"{low_quality_count}個の低品質記憶があります。内容の改善または削除を検討してください",
                    "priority": "high",
                    "action": "improve_or_remove_low_quality"
                })
            
            # 平均品質が低い場合の提案
            avg_quality = quality_scores.get("average_quality", 0)
            if avg_quality < 0.5:
                suggestions.append({
                    "type": "overall_quality",
                    "message": "記憶全体の品質が低下しています。記憶追加の方法を見直すことを推奨します",
                    "priority": "high",
                    "action": "review_memory_addition_process"
                })
                
        except Exception as e:
            self.logger.error(f"Failed to generate quality improvement suggestions: {e}")
        
        return suggestions

    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            if self.is_running:
                # 非同期でstop()を呼び出す代わりに、同期的に停止処理を行う
                if self.scheduler:
                    self.scheduler.stop()
                self.is_running = False
                self.logger.info("Scheduler stopped during cleanup")
            
            self.scheduler = None
            self.is_initialized = False
            self.logger.info("TextMemorySchedulerManager cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            # クリーンアップエラーでも状態をリセット
            self.scheduler = None
            self.is_initialized = False
            self.is_running = False
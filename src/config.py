"""
CocoroCore2 Configuration Management

MemOS統合による設定管理システム
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ValidationError, validator

# MemOS関連インポート（遅延インポートで対応）
# from memos.configs.mem_os import MOSConfig


class ServerConfig(BaseModel):
    """FastAPIサーバー設定"""
    host: str = "127.0.0.1"
    port: int = 55601
    workers: int = 1
    reload: bool = False
    debug: bool = False


class CharacterConfig(BaseModel):
    """キャラクター設定"""
    name: str = "つくよみちゃん"
    personality: str = "friendly"
    voice_model: str = "tsukuyomi"


class VADConfig(BaseModel):
    """Voice Activity Detection設定"""
    auto_adjustment: bool = True
    fixed_threshold: float = -40.0
    silence_duration_threshold: float = 2.0
    max_duration: float = 30.0


class STTConfig(BaseModel):
    """Speech-To-Text設定"""
    engine: str = "openai"
    model: str = "whisper-1"
    language: str = "ja"
    api_key: Optional[str] = None


class SpeechConfig(BaseModel):
    """音声処理設定"""
    enabled: bool = True
    vad: VADConfig = Field(default_factory=VADConfig)
    stt: STTConfig = Field(default_factory=STTConfig)


# Neo4jConfigはMemOS設定ファイルに移動


class ShellIntegrationConfig(BaseModel):
    """CocoroShell統合設定"""
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 55605
    auto_tts: bool = True
    timeout: int = 30


class MCPConfig(BaseModel):
    """Model Context Protocol設定"""
    enabled: bool = True
    config_file: str = "../UserData2/CocoroAiMcp.json"
    timeout: int = 30


class LoggingConfig(BaseModel):
    """ログ設定"""
    level: str = "INFO"
    file: str = "logs/cocoro_core2.log"
    max_size_mb: int = 10
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class SessionConfig(BaseModel):
    """セッション管理設定"""
    timeout_seconds: int = 300
    max_sessions: int = 1000
    cleanup_interval_seconds: int = 30



class CocoroCore2Config(BaseModel):
    """CocoroCore2統合設定"""
    version: str = "2.0.0"
    environment: str = "production"
    server: ServerConfig = Field(default_factory=ServerConfig)
    mos_config: Dict[str, Any] = Field(default_factory=dict)
    neo4j_config: Dict[str, Any] = Field(default_factory=dict)
    character: CharacterConfig = Field(default_factory=CharacterConfig)
    speech: SpeechConfig = Field(default_factory=SpeechConfig)
    shell_integration: ShellIntegrationConfig = Field(default_factory=ShellIntegrationConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None, environment: str = "development") -> "CocoroCore2Config":
        """設定ファイルから設定を読み込む
        
        Args:
            config_path: 設定ファイルパス（指定がない場合は自動検索）
            environment: 環境名（development/production）
            
        Returns:
            CocoroCore2Config: 設定オブジェクト
        """
        if config_path is None:
            config_path = find_config_file(environment)
        
        # 設定ファイル読み込み
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        # 環境変数置換
        config_data = substitute_env_variables(config_data)
        
        # MemOS設定の検証・補完
        config_data = validate_and_complete_mos_config(config_data)
        
        try:
            return cls(**config_data)
        except ValidationError as e:
            raise ConfigurationError(f"設定ファイルの検証に失敗しました: {e}")


class ConfigurationError(Exception):
    """設定関連エラー"""
    pass


def parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する"""
    parser = argparse.ArgumentParser(description="CocoroCore2設定ローダー")
    parser.add_argument("--config-dir", "-c", help="設定ファイルのディレクトリパス")
    parser.add_argument("--config-file", "-f", help="設定ファイルパス")
    parser.add_argument("--environment", "-e", default="development", 
                       choices=["development", "production"], help="実行環境")
    return parser.parse_args()


def find_config_file(environment: str = "development") -> str:
    """CocoroCore2設定ファイルを自動検索する
    
    検索順序:
    1. ../UserData2/cocoro_config.json (ユーザー設定）
    2. ./config/{environment}.json (環境別設定)
    3. ./config/cocoro_config.json (デフォルト設定)
    
    Args:
        environment: 環境名
        
    Returns:
        str: 設定ファイルパス
        
    Raises:
        ConfigurationError: 設定ファイルが見つからない場合
    """
    # 実行ディレクトリの決定
    if getattr(sys, "frozen", False):
        # PyInstallerなどで固められたexeの場合
        base_dir = Path(sys.executable).parent
    else:
        # 通常のPythonスクリプトとして実行された場合
        base_dir = Path(__file__).parent.parent
    
    # 検索パスのリスト
    search_paths = [
        base_dir.parent / "UserData2" / "cocoro_config.json",  # ユーザー設定（優先）
        base_dir / "config" / f"{environment}.json",          # 環境別設定
        base_dir / "config" / "cocoro_config.json",           # デフォルト設定
    ]
    
    for path in search_paths:
        if path.exists():
            return str(path)
    
    raise ConfigurationError(f"CocoroCore2設定ファイルが見つかりません。検索パス: {[str(p) for p in search_paths]}")


def substitute_env_variables(data: Any) -> Any:
    """設定データ内の環境変数を置換する
    
    ${VAR_NAME} 形式の環境変数参照を実際の値に置き換える
    
    Args:
        data: 設定データ（dict, list, str等）
        
    Returns:
        Any: 環境変数が置換された設定データ
    """
    if isinstance(data, str):
        # ${VAR_NAME} パターンを検索・置換
        def replace_env_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))  # 見つからない場合は元の文字列を返す
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, data)
    
    elif isinstance(data, dict):
        return {key: substitute_env_variables(value) for key, value in data.items()}
    
    elif isinstance(data, list):
        return [substitute_env_variables(item) for item in data]
    
    else:
        return data


def load_memos_config() -> Dict[str, Any]:
    """MemOS設定ファイルを読み込む
    
    Returns:
        Dict[str, Any]: MemOS設定データ
        
    Raises:
        ConfigurationError: 設定ファイルが見つからない場合
    """
    # 実行ディレクトリの決定
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent
    
    userdata_dir = base_dir.parent / "UserData2"
    config_dir = base_dir / "config"
    
    # MemOS設定ファイルを検索（優先順位順）
    search_paths = [
        userdata_dir / "memos_config.json",     # ユーザー設定（優先）
        config_dir / "memos_config.json",       # デフォルト設定
    ]
    
    for config_path in search_paths:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                return substitute_env_variables(config_data)
            except json.JSONDecodeError as e:
                raise ConfigurationError(f"MemOS設定ファイルの形式が不正です ({config_path}): {e}")
            except Exception as e:
                raise ConfigurationError(f"MemOS設定ファイルの読み込みに失敗しました ({config_path}): {e}")
    
    raise ConfigurationError(f"MemOS設定ファイルが見つかりません。検索パス: {[str(p) for p in search_paths]}")


def load_neo4j_config() -> Dict[str, Any]:
    """Neo4j設定ファイルを読み込む
    
    Returns:
        Dict[str, Any]: Neo4j設定データ
        
    Raises:
        ConfigurationError: 設定ファイルが見つからない場合
    """
    # 実行ディレクトリの決定
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent
    
    userdata_dir = base_dir.parent / "UserData2"
    config_dir = base_dir / "config"
    
    # Neo4j設定ファイルを検索（優先順位順）
    search_paths = [
        userdata_dir / "neo4j_config.json",     # ユーザー設定（優先）
        config_dir / "neo4j_config.json",       # デフォルト設定
    ]
    
    for config_path in search_paths:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                return substitute_env_variables(config_data)
            except json.JSONDecodeError as e:
                raise ConfigurationError(f"Neo4j設定ファイルの形式が不正です ({config_path}): {e}")
            except Exception as e:
                raise ConfigurationError(f"Neo4j設定ファイルの読み込みに失敗しました ({config_path}): {e}")
    
    raise ConfigurationError(f"Neo4j設定ファイルが見つかりません。検索パス: {[str(p) for p in search_paths]}")


def validate_and_complete_mos_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """MemOS設定の検証と補完を行う
    
    Args:
        config_data: 設定データ
        
    Returns:
        Dict[str, Any]: 検証・補完済み設定データ
        
    Raises:
        ConfigurationError: 必須設定が不足している場合
    """
    if "mos_config" not in config_data:
        # MemOS設定を別ファイルから読み込み
        config_data["mos_config"] = load_memos_config()
    
    # Neo4j設定を別途追加（MOSConfigには含めない）
    config_data["neo4j_config"] = load_neo4j_config()
    
    # 必須フィールドの検証
    mos_config = config_data["mos_config"]
    required_fields = ["chat_model", "mem_reader"]
    
    for field in required_fields:
        if field not in mos_config:
            raise ConfigurationError(f"MemOS設定に必須フィールド '{field}' がありません")
    
    # デフォルト値の補完
    mos_defaults = {
        "max_turns_window": 20,
        "top_k": 5,
        "enable_textual_memory": True,
        "enable_activation_memory": False,
        "enable_parametric_memory": False,
    }
    
    for key, default_value in mos_defaults.items():
        if key not in mos_config:
            mos_config[key] = default_value
    
    return config_data


def load_legacy_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """既存のCocoroAI設定ファイル（setting.json）を読み込む
    
    互換性のためのヘルパー関数
    
    Args:
        config_dir: 設定ディレクトリパス
        
    Returns:
        Dict[str, Any]: 設定データ
    """
    if config_dir:
        config_path = Path(config_dir) / "setting.json"
    else:
        # 実行ディレクトリの決定
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent.parent
        
        config_path = base_dir / "UserData2" / "setting.json"
    
    if not config_path.exists():
        raise ConfigurationError(f"CocoroAI設定ファイルが見つかりません: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    return substitute_env_variables(config_data)


def create_mos_config_from_dict(mos_config_dict: Dict[str, Any]):
    """辞書からMOSConfigオブジェクトを作成する
    
    Args:
        mos_config_dict: MemOS設定辞書
        
    Returns:
        MOSConfig: MOSConfigオブジェクト
        
    Raises:
        ConfigurationError: MOSConfig作成に失敗した場合
    """
    try:
        # 遅延インポートでMemOSの循環依存を回避
        from memos.configs.mem_os import MOSConfig
        
        # 辞書からMOSConfigオブジェクトを作成
        return MOSConfig(**mos_config_dict)
        
    except ImportError as e:
        raise ConfigurationError(f"MemOSライブラリが利用できません: {e}")
    except Exception as e:
        raise ConfigurationError(f"MOSConfig作成に失敗しました: {e}")


def load_mos_config_from_file(config_path: str):
    """ファイルからMOSConfigオブジェクトを作成する
    
    Args:
        config_path: 設定ファイルパス
        
    Returns:
        MOSConfig: MOSConfigオブジェクト
        
    Raises:
        ConfigurationError: 設定ファイル読み込みまたはMOSConfig作成に失敗した場合
    """
    try:
        # 遅延インポートでMemOSの循環依存を回避
        from memos.configs.mem_os import MOSConfig
        
        # ファイルから直接MOSConfigオブジェクトを作成
        return MOSConfig.from_json_file(config_path)
        
    except ImportError as e:
        raise ConfigurationError(f"MemOSライブラリが利用できません: {e}")
    except Exception as e:
        raise ConfigurationError(f"MOSConfig読み込みに失敗しました: {e}")


def get_mos_config(config: "CocoroCore2Config"):
    """CocoroCore2ConfigからMOSConfigオブジェクトを取得する
    
    Args:
        config: CocoroCore2設定オブジェクト
        
    Returns:
        MOSConfig: MOSConfigオブジェクト
        
    Raises:
        ConfigurationError: MOSConfig作成に失敗した場合
    """
    if not config.mos_config:
        raise ConfigurationError("MemOS設定が見つかりません")
    
    return create_mos_config_from_dict(config.mos_config)
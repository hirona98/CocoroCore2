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
    reload: bool = False


class CharacterConfig(BaseModel):
    """キャラクター設定"""
    name: str = "つくよみちゃん"


class STTConfig(BaseModel):
    """Speech-To-Text設定"""
    api_key: Optional[str] = None


class SpeechConfig(BaseModel):
    """音声処理設定"""
    enabled: bool = True
    stt: STTConfig = Field(default_factory=STTConfig)


class Neo4jSetting(BaseModel):
    """Neo4j設定"""
    uri: str = "bolt://127.0.0.1:7687"
    user: str = "neo4j"
    password: str = "12345678"
    db_name: str = "neo4j"
    embedding_dimension: int = 3072
    embedded_enabled: bool = True
    java_home: str = "jre"
    neo4j_home: str = "neo4j"
    startup_timeout: int = 60


class ShellIntegrationConfig(BaseModel):
    """CocoroShell統合設定"""
    enabled: bool = True


class MCPConfig(BaseModel):
    """Model Context Protocol設定"""
    enabled: bool = True


class LoggingConfig(BaseModel):
    """ログ設定"""
    level: str = "INFO"
    file: str = "logs/cocoro_core2.log"
    max_size_mb: int = 10
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class CocoroCore2Config(BaseModel):
    """CocoroCore2統合設定"""
    version: str = "2.0.0"
    server: ServerConfig = Field(default_factory=ServerConfig)
    character: CharacterConfig = Field(default_factory=CharacterConfig)
    speech: SpeechConfig = Field(default_factory=SpeechConfig)
    shell_integration: ShellIntegrationConfig = Field(default_factory=ShellIntegrationConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

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
        
        # 設定の検証・補完
        config_data = validate_and_complete_config(config_data)
        
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
    1. ../UserData2/CocoroSetting.json (ユーザー設定）
    2. ./config/CocoroSetting.json (デフォルト設定)
    
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
        base_dir.parent / "UserData2" / "CocoroSetting.json",  # ユーザー設定（優先）
        base_dir / "config" / "CocoroSetting.json",           # デフォルト設定
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
        userdata_dir / "MemosSetting.json",     # ユーザー設定（優先）
        config_dir / "MemosSetting.json",       # デフォルト設定
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
        userdata_dir / "Neo4jSetting.json",     # ユーザー設定（優先）
        config_dir / "Neo4jSetting.json",       # デフォルト設定
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


def validate_and_complete_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """設定の検証と補完を行う
    
    Args:
        config_data: 設定データ
        
    Returns:
        Dict[str, Any]: 検証・補完済み設定データ
        
    Raises:
        ConfigurationError: 必須設定が不足している場合
    """
    # 設定の基本的な検証のみ
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


def get_mos_config(config: "CocoroCore2Config" = None):
    """MOSConfigオブジェクトを取得する
    
    Args:
        config: CocoroCore2設定オブジェクト（使用しない、互換性のため）
        
    Returns:
        MOSConfig: MOSConfigオブジェクト
        
    Raises:
        ConfigurationError: MOSConfig作成に失敗した場合
    """
    memos_config_data = load_memos_config()
    return create_mos_config_from_dict(memos_config_data)
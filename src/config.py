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

class CharacterData(BaseModel):
    """キャラクター設定データ"""
    isReadOnly: bool = False
    modelName: str = "つくよみちゃん"
    isUseLLM: bool = False
    apiKey: str = ""
    llmModel: str = "gemini/gemini-2.0-flash"
    localLLMBaseUrl: str = ""
    systemPromptFilePath: str = ""
    isEnableMemory: bool = False
    userId: str = ""
    embeddedApiKey: str = ""
    embeddedModel: str = "ollama/nomic-embed-text"

class LoggingConfig(BaseModel):
    """ログ設定"""
    level: str = "INFO"
    file: str = "logs/cocoro_core2.log"
    max_size_mb: int = 10
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class CocoroAIConfig(BaseModel):
    """CocoroAI統合設定（Setting.json形式）"""
    cocoroDockPort: int = 55600
    cocoroCorePort: int = 55601
    cocoroMemoryPort: int = 55602
    cocoroMemoryDBPort: int = 55603
    cocoroShellPort: int = 55605
    isEnableMcp: bool = True

    # キャラクター設定
    currentCharacterIndex: int = 0
    characterList: list[CharacterData] = Field(default_factory=list)
    
    # CocoroCore2用の追加設定
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @property
    def current_character(self) -> Optional[CharacterData]:
        """現在選択されているキャラクターを取得"""
        if 0 <= self.currentCharacterIndex < len(self.characterList):
            return self.characterList[self.currentCharacterIndex]
        return None
    
    
    @property
    def character_name(self) -> str:
        """現在のキャラクター名"""
        char = self.current_character
        return char.modelName if char else "つくよみちゃん"

    @classmethod
    def load(cls, config_path: Optional[str] = None, environment: str = "development") -> "CocoroAIConfig":
        """設定ファイルから設定を読み込む
        
        Args:
            config_path: 設定ファイルパス（指定がない場合は自動検索）
            environment: 環境名（development/production）
            
        Returns:
            CocoroAIConfig: 設定オブジェクト
        """
        if config_path is None:
            config_path = find_config_file(environment)
        
        # 設定ファイル読み込み
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        # 環境変数置換
        config_data = substitute_env_variables(config_data)
        
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
    """CocoroAI設定ファイルを自動検索する
    
    検索順序:
    1. ../UserData2/Setting.json (統合設定ファイル)
    
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
    
    # Setting.jsonのパス
    config_path = base_dir.parent / "UserData2" / "Setting.json"
    
    if config_path.exists():
        return str(config_path)
    
    raise ConfigurationError(f"Setting.jsonが見つかりません。パス: {config_path}")


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


def get_mos_config(config: "CocoroAIConfig" = None):
    """MOSConfigオブジェクトを取得する
    
    Args:
        config: CocoroAI設定オブジェクト（使用しない、互換性のため）
        
    Returns:
        MOSConfig: MOSConfigオブジェクト
        
    Raises:
        ConfigurationError: MOSConfig作成に失敗した場合
    """
    memos_config_data = load_memos_config()
    return create_mos_config_from_dict(memos_config_data)
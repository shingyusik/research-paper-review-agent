import json
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import ValidationError

from ..models.schemas import Settings
from ..utils.exceptions import ConfigValidationError


_config: Optional[Settings] = None


def load_env() -> None:
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def load_config(config_path: str = None) -> Settings:
    """Load and validate configuration from JSON file.

    Args:
        config_path: Path to the configuration file. If None, uses default path.

    Returns:
        Validated Settings object.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ConfigValidationError: If the config file has invalid structure or values.
        json.JSONDecodeError: If the config file contains invalid JSON.
    """
    global _config

    load_env()

    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        resolved_path = project_root / "config" / "settings.json"
    else:
        resolved_path = Path(config_path)

    resolved_path = resolved_path.expanduser()

    if not resolved_path.exists():
        raise FileNotFoundError(f"Config file not found: {resolved_path}")

    try:
        with open(resolved_path, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in config file '{resolved_path}': {e.msg}",
            e.doc,
            e.pos
        )

    if 'input_path' in raw_config:
        raw_config['input_path'] = os.path.expanduser(raw_config['input_path'])
    if 'output_path' in raw_config:
        raw_config['output_path'] = os.path.expanduser(raw_config['output_path'])

    try:
        settings = Settings(**raw_config)
    except ValidationError as e:
        raise ConfigValidationError(e.errors(), resolved_path)

    _config = settings
    return settings


def set_config(settings: Settings) -> None:
    """Set configuration directly (used by GUI)."""
    global _config
    load_env()
    _config = settings


def get_config() -> Settings:
    """Get the current configuration, loading it if necessary.

    Returns:
        Validated Settings object.
    """
    if _config is None:
        return load_config()
    return _config


def get_config_dict() -> dict:
    """Get the current configuration as a dictionary.

    Returns:
        Configuration as a dictionary (for backward compatibility).
    """
    config = get_config()
    return config.model_dump()


def get_llm_model(node_name: str) -> str:
    """Get the LLM model for a specific node.

    Args:
        node_name: Name of the node.

    Returns:
        LLM model string in format 'provider:model_name'.
    """
    config = get_config()
    node_model = getattr(config.llm.nodes, node_name, None)

    if node_model is not None:
        return node_model

    return config.llm.default_model


def get_target_language() -> str:
    """Get the target language for translation.

    Returns:
        Language code (e.g., 'ko', 'en').
    """
    config = get_config()
    return config.target_language


def get_max_analysis_length() -> int:
    """Get the maximum character length for analysis outputs.

    Returns:
        Maximum character length.
    """
    config = get_config()
    return config.max_analysis_length


def get_paper_type() -> str:
    """Get the configured paper type setting.

    Returns:
        Paper type: 'auto', 'standard', or 'review'.
    """
    config = get_config()
    return config.paper_type


def get_keyword_file_path() -> Optional[str]:
    """Get the keyword file path from configuration.

    Returns:
        Path to keyword file, or None if not specified.
    """
    config = get_config()
    if hasattr(config, 'keyword_file_path'):
        return config.keyword_file_path
    return None

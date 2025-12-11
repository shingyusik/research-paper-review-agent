from typing import Dict
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from .config_service import get_llm_model
from ..utils.logger import get_logger

logger = get_logger("llm_service")

_llm_cache: Dict[str, BaseChatModel] = {}


def get_llm(node_name: str) -> BaseChatModel:
    if node_name in _llm_cache:
        logger.debug(f"LLM 캐시 히트: {node_name}")
        return _llm_cache[node_name]

    model_name = get_llm_model(node_name)
    logger.debug(f"LLM 초기화: {node_name} -> {model_name}")
    llm = init_chat_model(model_name)
    _llm_cache[node_name] = llm

    return llm


def clear_llm_cache() -> None:
    _llm_cache.clear()


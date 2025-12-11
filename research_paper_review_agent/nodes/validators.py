from typing import Dict, List, Union, Literal

from langgraph.types import Send
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from ..core.state import State
from ..services.llm_service import get_llm
from ..services.config_service import get_max_analysis_length
from ..utils.logger import get_logger


@tool
def count_characters(text: str) -> int:
    """Count the number of characters in the given text."""
    return len(text)

ANALYSIS_FIELDS = ["background", "research_purpose", "methodologies", "results", "keypoints"]


def check_analysis_length(state: State) -> Dict[str, List[str]]:
    logger = get_logger("check_analysis_length")
    logger.info("분석 결과 글자수 체크 시작")

    max_length = get_max_analysis_length()
    exceeded_fields = []
    paper_type = state.get("paper_type", "standard")
    
    if paper_type == "standard":
        for field in ANALYSIS_FIELDS:
            content = state.get(field, "")
            length = len(content)
            logger.info(f"{field}: {length}자")
            if length > max_length:
                exceeded_fields.append(field)
                logger.warning(f"{field}이(가) {max_length}자를 초과했습니다 ({length}자)")
    else:
        section_analyses = state.get("section_analyses", {})
        for section_name, content in section_analyses.items():
            length = len(content)
            field_key = f"section:{section_name}"
            logger.info(f"{section_name}: {length}자")
            if length > max_length:
                exceeded_fields.append(field_key)
                logger.warning(f"섹션 '{section_name}'이(가) {max_length}자를 초과했습니다 ({length}자)")

    logger.info(f"글자수 체크 완료. 초과 필드: {exceeded_fields}")
    return {"exceeded_fields": exceeded_fields}


def route_truncate(state: State) -> Union[List[Send], Literal["translate_analysis"]]:
    logger = get_logger("route_truncate")
    exceeded_fields = state.get("exceeded_fields", [])

    if not exceeded_fields:
        logger.info("축소할 필드 없음, translate_analysis로 이동")
        return "translate_analysis"

    logger.info(f"초과 필드 병렬 축소 시작: {exceeded_fields}")
    
    sends = []
    section_analyses = state.get("section_analyses", {})
    
    for field in exceeded_fields:
        if field.startswith("section:"):
            section_name = field[8:]
            content = section_analyses.get(section_name, "")
        else:
            content = state.get(field, "")
        
        sends.append(Send("truncate_single_field", {
            "truncate_field": field,
            "truncate_content": content
        }))
    
    return sends


def truncate_single_field(state: State) -> Dict:
    logger = get_logger("truncate_single_field")
    field = state.get("truncate_field", "")
    content = state.get("truncate_content", "")

    if not field or not content:
        logger.warning(f"truncate_field 또는 truncate_content가 비어있음 (field={field}, content_len={len(content)})")
        return {}

    max_length = get_max_analysis_length()
    llm = get_llm("truncate_single_field")
    llm_with_tools = llm.bind_tools([count_characters])

    prompt = f"""Condense the following analysis to under {max_length} characters.

Requirements:
- Keep bullet point format
- Preserve only the most critical information
- Use the same language as the original

**CRITICAL - DO NOT VIOLATE:**
1. DO NOT reduce too much below the limit. Target length should be close to {max_length} characters (e.g., {int(max_length * 0.8)}-{max_length} characters).
2. NEVER change the structure of the text. Keep the exact same headings, bullet points, and hierarchy.

**IMPORTANT - USE THE TOOL:**
- You have access to the `count_characters` tool to check character count.
- Use the tool to verify your condensed version meets the requirement.
- After checking, provide the final condensed version.

Original ({len(content)} characters):
{content}

Condensed version ({int(max_length * 0.8)}-{max_length} characters, same structure):"""

    messages = [HumanMessage(content=prompt)]
    response = llm_with_tools.invoke(messages)

    if response.tool_calls:
        shortened = response.tool_calls[0]["args"]["text"]
        char_count = len(shortened)
        logger.debug(f"Tool 호출: count_characters -> {char_count}자")
    else:
        shortened = response.content.strip()

    logger.info(f"{field} 축소 완료: {len(content)}자 → {len(shortened)}자")

    if field.startswith("section:"):
        section_name = field[8:]
        return {"section_analyses": {section_name: shortened}}
    
    return {field: shortened}


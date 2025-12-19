from typing import Dict

from ..core.state import State
from ..services.llm_service import get_llm
from ..services.config_service import get_max_analysis_length
from ..utils.helpers import _get_full_text
from ..utils.logger import get_logger


def _get_section_or_full_text(state: State, section_name: str) -> str:
    """Get specific section if available, otherwise return full text."""
    sections = state.get("extracted_sections", {})
    if section_name in sections and sections[section_name]:
        return sections[section_name]
    return _get_full_text(state)


def analize_background(state: State) -> Dict[str, str]:
    logger = get_logger("analize_background")
    logger.info("연구 배경 분석 시작")
    llm = get_llm("analize_background")
    max_length = get_max_analysis_length()
    section_text = _get_section_or_full_text(state, "introduction")
    title = state.get("title", "")
    abstract = state.get("abstract", "")
    prompt = f"""Analyze the research background and context of this academic paper.

Include:
- The problem domain and its importance
- Previous work and literature context
- Gaps in existing research that this paper addresses
- Motivation for conducting this research

**Output Requirements:**
- Use bullet points (structured format, not prose)
- Keep under {max_length} characters
- Use the same language as the paper

Title: {title}

Abstract:
{abstract}

Paper Content:
{section_text}

Research Background Analysis:"""

    response = llm.invoke(prompt)
    background = response.content.strip()
    logger.info("연구 배경 분석 완료")

    return {"background": background}


def analize_research_purpose(state: State) -> Dict[str, str]:
    logger = get_logger("analize_research_purpose")
    logger.info("연구 목적 분석 시작")
    llm = get_llm("analize_research_purpose")
    max_length = get_max_analysis_length()
    section_text = _get_section_or_full_text(state, "introduction")
    title = state.get("title", "")
    abstract = state.get("abstract", "")

    prompt = f"""Analyze and clearly state the research purpose and objectives of this academic paper.

Include:
- Main research questions or hypotheses
- Specific goals and objectives
- Scope and limitations of the research
- Expected contributions

**Output Requirements:**
- Use bullet points (structured format, not prose)
- Keep under {max_length} characters
- Use the same language as the paper

Title: {title}

Abstract:
{abstract}

Paper Content:
{section_text}

Research Purpose Analysis:"""

    response = llm.invoke(prompt)
    research_purpose = response.content.strip()
    logger.info("연구 목적 분석 완료")

    return {"research_purpose": research_purpose}


def analize_methodologies(state: State) -> Dict[str, str]:
    logger = get_logger("analize_methodologies")
    logger.info("방법론 분석 시작")
    llm = get_llm("analize_methodologies")
    max_length = get_max_analysis_length()
    section_text = _get_section_or_full_text(state, "methods")
    title = state.get("title", "")
    abstract = state.get("abstract", "")

    prompt = f"""Analyze the methodologies used in this academic paper.

Include:
- Research design and approach
- Data collection methods
- Analysis techniques
- Tools, frameworks, or systems used
- Experimental setup (if applicable)

**Output Requirements:**
- Use bullet points (structured format, not prose)
- Keep under {max_length} characters
- Use the same language as the paper

Title: {title}

Abstract:
{abstract}

Paper Content:
{section_text}

Methodology Analysis:"""

    response = llm.invoke(prompt)
    methodologies = response.content.strip()
    logger.info("방법론 분석 완료")

    return {"methodologies": methodologies}


def analize_result(state: State) -> Dict[str, str]:
    logger = get_logger("analize_result")
    logger.info("결과 분석 시작")
    llm = get_llm("analize_result")
    max_length = get_max_analysis_length()
    section_text = _get_section_or_full_text(state, "results")
    title = state.get("title", "")
    abstract = state.get("abstract", "")

    prompt = f"""Analyze the results and findings of this academic paper.

Include:
- Key experimental or analytical results
- Statistical findings (if applicable)
- Comparisons with baseline or previous work
- Validation of hypotheses
- Unexpected or notable findings

**Output Requirements:**
- Use bullet points (structured format, not prose)
- Keep under {max_length} characters
- Use the same language as the paper

Title: {title}

Abstract:
{abstract}

Paper Content:
{section_text}

Results Analysis:"""

    response = llm.invoke(prompt)
    results = response.content.strip()
    logger.info("결과 분석 완료")

    return {"results": results}


def analize_identify_keypoints(state: State) -> Dict[str, str]:
    logger = get_logger("analize_identify_keypoints")
    logger.info("핵심 포인트 분석 시작")
    llm = get_llm("analize_identify_keypoints")
    max_length = get_max_analysis_length()
    section_text = _get_section_or_full_text(state, "discussion")
    title = state.get("title", "")
    abstract = state.get("abstract", "")

    prompt = f"""Identify the key contributions and differentiators of this academic paper.

Include:
- Novel contributions to the field
- What makes this work unique compared to prior research
- Practical implications and applications
- Theoretical advancements
- Future research directions suggested

**Output Requirements:**
- Use bullet points (structured format, not prose)
- Keep under {max_length} characters
- Use the same language as the paper

Title: {title}

Abstract:
{abstract}

Paper Content:
{section_text}

Key Contributions and Differentiators:"""

    response = llm.invoke(prompt)
    keypoints = response.content.strip()
    logger.info("핵심 포인트 분석 완료")

    return {"keypoints": keypoints}


def analyze_dynamic_section(state: State) -> Dict[str, Dict[str, str]]:
    """Analyze a single dynamic section (called via Send for parallel processing)."""
    logger = get_logger("analyze_dynamic_section")
    
    section_name = state.get("current_section_name", "")
    section_content = state.get("current_section_content", "")
    
    if not section_name or not section_content:
        logger.warning("섹션 이름 또는 내용이 비어있음")
        return {}
    
    logger.info(f"동적 섹션 분석 시작: '{section_name}'")
    
    llm = get_llm("analyze_dynamic_section")
    max_length = get_max_analysis_length()
    title = state.get("title", "")
    abstract = state.get("abstract", "")
    
    prompt = f"""Analyze and summarize this section from an academic review/survey paper.

Section Name: {section_name}

Provide a comprehensive summary that includes:
- Main topics and concepts covered in this section
- Key findings, insights, or arguments presented
- Important classifications, categories, or frameworks mentioned
- Notable examples or case studies discussed
- Connections to other topics or sections

**Output Requirements:**
- Use bullet points (structured format, not prose)
- Keep under {max_length} characters
- Use the same language as the paper
- Focus on the most important information

Paper Title: {title}

Abstract:
{abstract}

Section Content:
{section_content}

Section Summary:"""

    response = llm.invoke(prompt)
    analysis = response.content.strip()
    
    logger.info(f"동적 섹션 분석 완료: '{section_name}' ({len(analysis)}자)")
    
    return {"section_analyses": {section_name: analysis}}

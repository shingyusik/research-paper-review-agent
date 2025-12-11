from typing import Dict, List

from ..core.state import State
from ..services.llm_service import get_llm
from ..services.config_service import get_paper_type
from ..models.schemas import SectionRange, SectionRanges, PaperTypeModel, DynamicSectionRanges
from ..utils.helpers import _get_full_text, _get_first_pages
from ..utils.logger import get_logger


def extract_sections(state: State) -> Dict[str, Dict[str, str]]:
    """Extract paper sections using LLM to identify line ranges."""
    logger = get_logger("extract_sections")
    logger.info("섹션 추출 시작 (LLM)")
    
    llm = get_llm("extract_sections")
    structured_llm = llm.with_structured_output(SectionRanges)
    
    full_text = _get_full_text(state)
    lines = full_text.split('\n')
    
    numbered_lines = "\n".join(f"{i+1}|{line}" for i, line in enumerate(lines))
    
    prompt = f"""Identify the EXACT line ranges for each major section category in this academic paper.

CRITICAL RULES:
- Line numbers are shown at the beginning of each line (e.g., "27|I. INTRODUCTION" means line 27)
- start_line: The EXACT line number where the FIRST relevant section header appears
- end_line: The line BEFORE the next category's section starts (NOT the next subsection within the same category)
- Multiple consecutive paper sections may belong to ONE category. Include ALL of them in the range.

SECTION CATEGORIES (each may contain MULTIPLE paper sections):

1. introduction:
   - Includes: Introduction, Background, Literature Review, Related Work, Problem Statement
   - Usually the first major section (I., 1., etc.)
   - Range: From first introduction-related header to just before methods-related content

2. methods:
   - Includes: Methods, Methodology, Approach, Theory, Governing Equations, Mathematical Model, Numerical Modeling, Simulation Setup, Experimental Setup, System Design, Implementation, Simulation Conditions
   - Often spans MULTIPLE numbered sections (e.g., II, III, or 2, 3)
   - Range: From first methods-related header to just before results-related content

3. results:
   - Includes: Results, Findings, Experiments, Evaluation, Analysis, Simulation Results, Performance, Validation
   - Range: From first results-related header to just before discussion/conclusion

4. discussion:
   - Includes: Discussion, Conclusion, Summary, Future Work, Limitations
   - Usually the final content section
   - Range: From first discussion/conclusion header to end of main content (before References/Acknowledgments)

If a category doesn't exist in the paper, leave start_line and end_line as null.

Paper content (with line numbers):
{numbered_lines}"""

    result = structured_llm.invoke(prompt)
    
    sections = {}
    section_names = ["introduction", "methods", "results", "discussion"]
    
    for name in section_names:
        section_range: SectionRange = getattr(result, name)
        if section_range.start_line is not None and section_range.end_line is not None:
            start = max(0, section_range.start_line - 1)
            end = min(len(lines), section_range.end_line)
            section_text = '\n'.join(lines[start:end]).strip()
            sections[name] = section_text
            logger.debug(f"{name} 섹션 추출: 라인 {section_range.start_line}-{section_range.end_line}, {len(section_text)}자")
        else:
            sections[name] = ""
            logger.debug(f"{name} 섹션을 찾을 수 없음")
    
    found_sections = [k for k, v in sections.items() if v]
    logger.info(f"섹션 추출 완료: {found_sections}")
    
    return {"extracted_sections": sections}


def detect_paper_type(state: State) -> Dict[str, str]:
    """Detect paper type: standard research paper or review/survey paper."""
    logger = get_logger("detect_paper_type")
    logger.info("논문 타입 감지 시작")
    
    configured_type = get_paper_type()
    
    if configured_type != "auto":
        logger.info(f"설정된 논문 타입 사용: {configured_type}")
        return {"paper_type": configured_type}
    
    llm = get_llm("detect_paper_type")
    structured_llm = llm.with_structured_output(PaperTypeModel)
    
    first_pages = _get_first_pages(state, 5)
    
    prompt = f"""Analyze this academic paper and determine its type.

PAPER TYPES:
1. "standard" - Original research paper with typical structure:
   - Has clear Introduction, Methods/Methodology, Results, Discussion/Conclusion
   - Presents original experiments, simulations, or theoretical work
   - Reports new findings from the authors' own research

2. "review" - Review, survey, or overview paper:
   - Summarizes and synthesizes existing literature
   - May have sections organized by topics/themes rather than methodology
   - Examples: Literature review, Systematic review, Survey paper, Tutorial, Overview
   - Does NOT follow the standard Introduction-Methods-Results structure

Analyze the paper structure and content to classify it.

Paper content (first pages):
{first_pages}"""

    result = structured_llm.invoke(prompt)
    paper_type = result.paper_type.lower()
    
    if paper_type not in ["standard", "review"]:
        paper_type = "standard"
    
    logger.info(f"논문 타입 감지 완료: {paper_type} (이유: {result.reasoning[:100]}...)")
    
    return {"paper_type": paper_type}


def extract_dynamic_sections(state: State) -> Dict[str, Dict[str, str]]:
    """Extract dynamic sections from review/survey papers using LLM."""
    logger = get_logger("extract_dynamic_sections")
    logger.info("동적 섹션 추출 시작 (리뷰 논문)")
    
    llm = get_llm("extract_dynamic_sections")
    structured_llm = llm.with_structured_output(DynamicSectionRanges)
    
    full_text = _get_full_text(state)
    lines = full_text.split('\n')
    
    numbered_lines = "\n".join(f"{i+1}|{line}" for i, line in enumerate(lines))
    
    prompt = f"""Identify ALL major content sections in this review/survey paper.

CRITICAL RULES:
- Line numbers are shown at the beginning of each line (e.g., "27|II. TYPES OF AGENTS" means line 27)
- Extract EVERY major section header with its exact name as written in the paper
- Include numbered sections (e.g., "II. Background", "3. Classification Methods")
- start_line: The line number where the section header appears
- end_line: The line BEFORE the next section starts

EXCLUDE these sections (do NOT include):
- Abstract
- References/Bibliography
- Acknowledgments
- Appendix

INCLUDE sections like:
- Background, Literature Review, Related Work
- Any thematic/topic sections (e.g., "Types of AI Agents", "Applications in Healthcare")
- Methodology sections if present
- Discussion sections in the middle of the paper
- Any other content sections

Paper content (with line numbers):
{numbered_lines}"""

    result = structured_llm.invoke(prompt)
    
    dynamic_sections = {}
    
    for section in result.sections:
        start = max(0, section.start_line - 1)
        end = min(len(lines), section.end_line)
        section_text = '\n'.join(lines[start:end]).strip()
        
        if section_text:
            dynamic_sections[section.name] = section_text
            logger.debug(f"'{section.name}' 섹션 추출: 라인 {section.start_line}-{section.end_line}, {len(section_text)}자")
    
    logger.info(f"동적 섹션 추출 완료: {len(dynamic_sections)}개 섹션")
    
    return {"dynamic_sections": dynamic_sections}

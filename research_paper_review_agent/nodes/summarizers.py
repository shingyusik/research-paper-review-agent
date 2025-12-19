import pathlib
import re
import shutil
from typing import Dict, List

from ..core.state import State
from ..utils.logger import get_logger


def _generate_frontmatter(title: str, basic_info: dict, keywords: List[str], pdf_filename: str = "") -> str:
    authors = basic_info.get('authors', [])
    first_author = authors[0] if authors else ""
    year = basic_info.get('year', '') or ""
    journal = basic_info.get('journal', '') or ""

    def sanitize_keyword(kw: str) -> str:
        kw = re.sub(r'\([^)]*\)', '', kw)
        kw = re.sub(r'\[[^\]]*\]', '', kw)
        kw = re.sub(r'\{[^}]*\}', '', kw)
        kw = kw.replace("'", '')
        kw = kw.replace('–', '-')
        kw = kw.replace('+', '')
        kw = kw.replace(' ', '_').strip('_')
        return kw
    tags_str = "\n".join(f"  - {sanitize_keyword(kw)}" for kw in keywords) if keywords else ""
    paper_link = f"[[{pdf_filename}.pdf]]" if pdf_filename else ""

    frontmatter = f"""---
title: "{title}"
first_author: {first_author}
year: {year}
journal: "{journal}"
DOI: ""
paper_link: "{paper_link}"
tags:
{tags_str}
---"""

    return frontmatter


def final_summarize(state: State) -> Dict[str, str]:
    logger = get_logger("final_summarize")
    logger.info("최종 요약 및 보고서 생성 시작")
    
    paper_type = state.get("paper_type", "standard")
    title = state.get("title", "")
    basic_info = state.get("basic_info", {})
    keywords = state.get("keywords", [])
    conclusion = state.get("conclusion", "")
    output_path = state.get("output_path", "")
    input_path = state.get("input_path", "")

    authors = basic_info.get('authors', [])
    first_author = authors[0] if authors else "Unknown"
    year = basic_info.get('year', '') or "Unknown"
    safe_author = "".join(c if c.isalnum() or c in "-_" else "_" if c == " " else "" for c in first_author)
    base_name = f"{safe_author}{year}"

    final_pdf_name = base_name
    output_file = None
    output_pdf = None

    if output_path:
        output_dir = pathlib.Path(output_path)
        logger.debug(f"출력 경로: {output_dir}")
        if output_dir.is_dir():
            output_file = output_dir / f"{base_name}.md"
            counter = 1
            while output_file.exists():
                logger.debug(f"파일 중복, 카운터 증가: {output_file}")
                output_file = output_dir / f"{base_name}_{counter}.md"
                counter += 1
            logger.debug(f"마크다운 파일명 결정: {output_file.name}")
            
            if input_path:
                input_pdf = pathlib.Path(input_path)
                if input_pdf.exists() and input_pdf.suffix.lower() == ".pdf":
                    output_pdf = input_pdf.parent / f"{base_name}.pdf"
                    pdf_counter = 1
                    while output_pdf.exists() and output_pdf.resolve() != input_pdf.resolve():
                        logger.debug(f"PDF 파일 중복, 카운터 증가: {output_pdf}")
                        output_pdf = input_pdf.parent / f"{base_name}_{pdf_counter}.pdf"
                        pdf_counter += 1
                    final_pdf_name = output_pdf.stem
                    logger.debug(f"PDF 파일명 결정: {output_pdf.name}")
        else:
            output_file = output_dir
            logger.debug(f"출력 파일 직접 지정: {output_file}")

    frontmatter = _generate_frontmatter(title, basic_info, keywords, final_pdf_name)

    if paper_type == "review":
        final_report = _generate_review_report(state, frontmatter, conclusion, logger)
    else:
        final_report = _generate_standard_report(state, frontmatter, conclusion, logger)

    if output_path and output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(final_report, encoding="utf-8")
        logger.info(f"보고서 저장 완료: {output_file}")
        
        if output_pdf and input_path:
            input_pdf = pathlib.Path(input_path)
            if input_pdf.exists() and output_pdf.resolve() != input_pdf.resolve():
                shutil.move(input_pdf, output_pdf)
                logger.info(f"PDF 파일명 변경 완료: {output_pdf}")
            elif input_pdf.exists():
                logger.debug(f"PDF 파일명 이미 일치: {output_pdf}")

    logger.info("최종 요약 완료")
    return {"final_report": final_report}


def _generate_standard_report(state: State, frontmatter: str, conclusion: str, logger) -> str:
    """Generate report for standard research papers."""
    background = state.get("background", "")
    research_purpose = state.get("research_purpose", "")
    methodologies = state.get("methodologies", "")
    results = state.get("results", "")
    keypoints = state.get("keypoints", "")

    logger.debug("일반 논문 형식 보고서 생성")
    
    return f"""{frontmatter}

## Summary
### Research Background
{background}

### Research Purpose
{research_purpose}

### Methodology
{methodologies}

### Results
{results}

### Key Contributions
{keypoints}

### Conclusion
{conclusion}

---
## Link
- """


def _generate_review_report(state: State, frontmatter: str, conclusion: str, logger) -> str:
    """Generate report for review/survey papers with dynamic sections."""
    section_analyses = state.get("section_analyses", {})
    
    logger.debug(f"리뷰 논문 형식 보고서 생성 ({len(section_analyses)}개 섹션)")
    
    sections_content = ""
    for section_name, analysis in section_analyses.items():
        sections_content += f"### {section_name}\n{analysis}\n\n"
    
    return f"""{frontmatter}

## Summary
{sections_content}
### Conclusion
{conclusion}

---
## Link
- """


import json
import re
from typing import Dict, List

from ..core.state import State, BasicInfo
from ..services.llm_service import get_llm
from ..services.config_service import get_keyword_file_path
from ..models.schemas import BasicInfoModel, KeywordsModel
from ..utils.helpers import _get_first_pages, _get_full_text
from ..utils.logger import get_logger
from ..utils.keyword_loader import load_keywords_from_file


def extract_title(state: State) -> Dict[str, str]:
    logger = get_logger("extract_title")
    logger.info("제목 추출 시작")
    llm = get_llm("extract_title")
    first_pages = _get_first_pages(state, 2)

    prompt = f"""Extract the title of this academic paper. Return ONLY the title text, nothing else.

Paper content (first pages):
{first_pages}

Title:"""

    response = llm.invoke(prompt)
    title = response.content.strip()
    logger.info(f"제목 추출 완료: {title[:50]}...")

    return {"title": title}


def extract_abstract(state: State) -> Dict[str, str]:
    logger = get_logger("extract_abstract")
    logger.info("초록 추출 시작")
    llm = get_llm("extract_abstract")
    first_pages = _get_first_pages(state, 3)

    prompt = f"""Extract the abstract of this academic paper. Return ONLY the abstract text, nothing else.
If there is no explicit abstract section, return the introductory summary paragraph.

Paper content (first pages):
{first_pages}

Abstract:"""

    response = llm.invoke(prompt)
    abstract = response.content.strip()
    logger.info("초록 추출 완료")

    return {"abstract": abstract}


def extract_conclusion(state: State) -> Dict[str, str]:
    logger = get_logger("extract_conclusion")
    logger.info("결론 추출 시작")
    llm = get_llm("extract_conclusion")
    full_text = _get_full_text(state)

    prompt = f"""Extract the conclusion section of this academic paper. Return ONLY the conclusion text, nothing else.
Look for sections titled "Conclusion", "Conclusions", "Discussion", "Summary", or similar.

Paper content:
{full_text}

Conclusion:"""

    response = llm.invoke(prompt)
    conclusion = response.content.strip()
    logger.info("결론 추출 완료")

    return {"conclusion": conclusion}


def extract_basic_info(state: State) -> Dict[str, BasicInfo]:
    logger = get_logger("extract_basic_info")
    logger.info("기본 정보 추출 시작")
    llm = get_llm("extract_basic_info")
    structured_llm = llm.with_structured_output(BasicInfoModel)
    first_pages = _get_first_pages(state, 2)

    prompt = f"""Extract the basic information from this academic paper.

Paper content (first pages):
{first_pages}"""

    basic_info = structured_llm.invoke(prompt)
    logger.info(f"기본 정보 추출 완료: {basic_info.authors[0] if basic_info.authors else 'Unknown'} ({basic_info.year})")

    return {"basic_info": basic_info.model_dump()}


def extract_keywords(state: State) -> Dict[str, List[str]]:
    logger = get_logger("extract_keywords")
    logger.info("키워드 추출 시작")
    llm = get_llm("extract_keywords")
    structured_llm = llm.with_structured_output(KeywordsModel)
    first_pages = _get_first_pages(state, 3)
    abstract = state.get("abstract", "")

    prompt = f"""Extract or identify the keywords from this academic paper.
If explicit keywords are listed, extract them. Otherwise, identify 5-10 key terms that best describe this paper.

Abstract:
{abstract}

Paper content (first pages):
{first_pages}"""

    result = structured_llm.invoke(prompt)
    logger.info(f"키워드 추출 완료: {len(result.keywords)}개")

    return {"keywords": result.keywords}


def load_keyword_file(state: State) -> Dict:
    """Load keywords and synonyms from keyword file."""
    logger = get_logger("load_keyword_file")
    logger.info("키워드 파일 로드 시작")
    
    keyword_file_path = get_keyword_file_path()
    original_keywords, keyword_synonyms = load_keywords_from_file(keyword_file_path)
    
    logger.info(f"키워드 파일 로드 완료: {len(original_keywords)}개 키워드, {len(keyword_synonyms)}개 동의어 매핑")
    
    return {
        "original_keywords": original_keywords,
        "keyword_synonyms": keyword_synonyms
    }


def re_extract_keywords(state: State) -> Dict[str, List[str]]:
    """Re-extract keywords from paper using extracted keywords and original keywords."""
    logger = get_logger("re_extract_keywords")
    logger.info("키워드 재추출 시작")
    
    extracted_keywords = state.get("keywords", [])
    original_keywords = state.get("original_keywords", [])
    
    if not original_keywords:
        logger.info("원래 키워드가 없어 재추출 단계를 건너뜁니다")
        return {"keywords": extracted_keywords}
    
    llm = get_llm("re_extract_keywords")
    structured_llm = llm.with_structured_output(KeywordsModel)
    
    title = state.get("title", "")
    abstract = state.get("abstract", "")
    
    prompt = f"""Based on the following keywords, title, and abstract, extract additional relevant keywords from the paper.
    
Existing keywords (extracted from paper):
{', '.join(extracted_keywords) if extracted_keywords else 'None'}

Reference keywords (from keyword file for context):
{', '.join(original_keywords) if original_keywords else 'None'}

Title:
{title}

Abstract:
{abstract}

Extract additional relevant keywords that are related to the existing keywords and appear in the title or abstract. 
Return only keywords that are actually mentioned in the title or abstract."""

    result = structured_llm.invoke(prompt)
    re_extracted_keywords = result.keywords
    
    extracted_keywords_set = set(extracted_keywords)
    new_keywords = [kw for kw in re_extracted_keywords if kw not in extracted_keywords_set]
    
    all_keywords = extracted_keywords + new_keywords
    
    logger.info(f"키워드 재추출 완료: 기존 {len(extracted_keywords)}개 + 신규 {len(new_keywords)}개 = 총 {len(all_keywords)}개")
    
    return {"keywords": all_keywords}


def add_synonyms_to_keywords(state: State) -> Dict[str, List[str]]:
    """Add synonyms to keywords based on keyword file."""
    logger = get_logger("add_synonyms_to_keywords")
    logger.info("동의어 추가 시작")
    
    keywords = state.get("keywords", [])
    keyword_synonyms = state.get("keyword_synonyms", {})
    
    final_keywords = list(keywords)
    
    for keyword in keywords:
        if keyword in keyword_synonyms:
            synonyms = keyword_synonyms[keyword]
            for synonym in synonyms:
                if synonym not in final_keywords:
                    final_keywords.append(synonym)
    
    logger.info(f"동의어 추가 완료: 기존 {len(keywords)}개 + 동의어 추가 = 총 {len(final_keywords)}개")
    
    return {"keywords": final_keywords}


def add_new_keywords_to_file(state: State) -> Dict:
    """Add new keywords that are not in the original keyword file to the keyword file."""
    logger = get_logger("add_new_keywords_to_file")
    logger.info("새로운 키워드 파일 추가 시작")
    
    keywords = state.get("keywords", [])
    original_keywords = state.get("original_keywords", [])
    
    if not keywords:
        logger.info("추가할 키워드가 없습니다")
        return {}
    
    original_keywords_set = set(original_keywords)
    new_keywords = []
    
    for keyword in keywords:
        if keyword not in original_keywords_set:
            new_keywords.append(keyword)
    
    if not new_keywords:
        logger.info("새로운 키워드가 없습니다")
        return {}
    
    keyword_file_path = get_keyword_file_path()
    if not keyword_file_path:
        logger.warning("키워드 파일 경로가 설정되지 않아 새로운 키워드를 추가할 수 없습니다")
        return {}
    
    try:
        with open(keyword_file_path, "r", encoding="utf-8") as f:
            keyword_data = json.load(f)
        
        added_count = 0
        for new_keyword in new_keywords:
            cleaned_keyword = re.sub(r'\([^)]*\)|\[[^\]]*\]|\{[^}]*\}', '', new_keyword)
            cleaned_keyword = re.sub(r'\s+', ' ', cleaned_keyword).strip()
            if cleaned_keyword and cleaned_keyword not in keyword_data:
                keyword_data[cleaned_keyword] = []
                added_count += 1
        
        if added_count > 0:
            with open(keyword_file_path, "w", encoding="utf-8") as f:
                json.dump(keyword_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"새로운 키워드 {added_count}개를 키워드 파일에 추가: {', '.join(new_keywords[:5])}{'...' if len(new_keywords) > 5 else ''}")
        else:
            logger.info("모든 키워드가 이미 키워드 파일에 존재합니다")
        
        return {}
    except FileNotFoundError:
        logger.error(f"키워드 파일을 찾을 수 없습니다: {keyword_file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"키워드 파일 JSON 파싱 오류: {e}")
        return {}
    except Exception as e:
        logger.error(f"키워드 파일에 새로운 키워드 추가 실패: {e}")
        return {}


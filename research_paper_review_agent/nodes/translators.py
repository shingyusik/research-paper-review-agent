from typing import Dict, List, Optional
import unicodedata

from langdetect import detect, LangDetectException

from ..core.state import State
from ..services.llm_service import get_llm
from ..services.config_service import get_target_language
from ..models.schemas import TranslatedAnalysisModel, TranslationList
from ..utils.logger import get_logger


LANGUAGE_NAMES = {
    "ko": "Korean",
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
}

ANALYSIS_FIELDS = ["background", "research_purpose", "methodologies", "results", "keypoints", "conclusion"]


def _normalize_key(text: str) -> str:
    """Normalize text by converting ligatures to standard characters."""
    return unicodedata.normalize('NFKC', text)


def _match_key_to_original(returned_key: str, original_keys: List[str]) -> Optional[str]:
    """Match a returned key to original keys using normalization."""
    normalized_returned = _normalize_key(returned_key)
    
    for orig_key in original_keys:
        if _normalize_key(orig_key) == normalized_returned:
            return orig_key
    
    return None


def _detect_language(text: str) -> Optional[str]:
    """Detect language of text using langdetect."""
    if not text or len(text.strip()) < 20:
        return None
    try:
        detected = detect(text)
        if detected.startswith("zh"):
            return "zh"
        return detected
    except LangDetectException:
        return None


def _is_target_language(text: str, target_lang: str) -> bool:
    """Check if text is already in target language."""
    detected = _detect_language(text)
    if detected is None:
        return False
    if detected == target_lang:
        return True
    if target_lang == "zh" and detected.startswith("zh"):
        return True
    return False


def translate_analysis(state: State) -> Dict:
    logger = get_logger("translate_analysis")
    target_language = get_target_language()
    paper_type = state.get("paper_type", "standard")

    if not target_language:
        logger.debug("번역 대상 언어가 설정되지 않음, 건너뜀")
        return {}

    language_name = LANGUAGE_NAMES.get(target_language, target_language)
    
    if paper_type == "review":
        return _translate_dynamic_sections(state, target_language, language_name, logger)
    
    return _translate_standard_analysis(state, target_language, language_name, logger)


def _translate_standard_analysis(state: State, target_language: str, language_name: str, logger) -> Dict[str, str]:
    """Translate standard paper analysis fields."""
    fields_to_translate = {}
    fields_already_translated = []
    
    for field_name in ANALYSIS_FIELDS:
        content = state.get(field_name, "")
        if not content:
            continue
            
        if _is_target_language(content, target_language):
            fields_already_translated.append(field_name)
        else:
            fields_to_translate[field_name] = content
    
    if fields_already_translated:
        logger.info(f"이미 목표 언어인 필드 (번역 건너뜀): {fields_already_translated}")
    
    if not fields_to_translate:
        logger.info("모든 필드가 이미 목표 언어입니다. 번역 건너뜀")
        return {}
    
    logger.info(f"번역할 필드: {list(fields_to_translate.keys())}")
    logger.info(f"분석 결과 번역 시작 ({language_name})")

    llm = get_llm("translate_analysis")
    
    if set(fields_to_translate.keys()) == set(ANALYSIS_FIELDS):
        structured_llm = llm.with_structured_output(TranslatedAnalysisModel)
        
        prompt = f"""Translate the following academic paper analysis sections into {language_name}.
Maintain the academic tone and technical terminology.

[Background]
{fields_to_translate.get('background', '')}

[Research Purpose]
{fields_to_translate.get('research_purpose', '')}

[Methodologies]
{fields_to_translate.get('methodologies', '')}

[Results]
{fields_to_translate.get('results', '')}

[Key Points]
{fields_to_translate.get('keypoints', '')}

[Conclusion]
{fields_to_translate.get('conclusion', '')}"""

        result = structured_llm.invoke(prompt)
        logger.info("분석 결과 번역 완료")

        return {
            "background": result.background,
            "research_purpose": result.research_purpose,
            "methodologies": result.methodologies,
            "results": result.results,
            "keypoints": result.keypoints,
            "conclusion": result.conclusion,
        }
    else:
        logger.debug(f"부분 번역 시작: {list(fields_to_translate.keys())}")
        
        try:
            batch_translations = _translate_batch_sections(llm, fields_to_translate, language_name, logger)
            logger.info("분석 결과 번역 완료")
            return batch_translations
        except Exception as e:
            logger.error(f"부분 번역 실패: {e}")
            return {}


def _translate_batch_sections(llm, batch: Dict[str, str], language_name: str, logger) -> Dict[str, str]:
    """Translate a batch of sections using structured output."""
    batch_keys = list(batch.keys())
    
    sections_text = "\n\n".join(
        f"[{section_name}]\n{content}" 
        for section_name, content in batch.items()
    )
    
    prompt = f"""Translate the following academic paper section analyses into {language_name}.
Maintain the academic tone and technical terminology.

You MUST translate ALL {len(batch_keys)} sections below.
For each section, return an item with:
- key: the EXACT section name as provided (e.g., "{batch_keys[0]}")
- value: the translated text in {language_name}

Sections to translate:

{sections_text}"""

    structured_llm = llm.with_structured_output(TranslationList)
    result = structured_llm.invoke(prompt)
    
    translations = {}
    for item in result.items:
        matched_key = _match_key_to_original(item.key, batch_keys)
        if matched_key:
            translations[matched_key] = item.value
            logger.debug(f"'{matched_key}' 번역 완료: {len(item.value)}자")
        else:
            translations[item.key] = item.value
            logger.warning(f"키 매칭 실패, 원본 키 사용: '{item.key}'")
    
    return translations


def _translate_dynamic_sections(state: State, target_language: str, language_name: str, logger) -> Dict:
    """Translate dynamic section analyses for review papers."""
    section_analyses = state.get("section_analyses", {})
    conclusion = state.get("conclusion", "")
    
    sections_to_translate = {}
    sections_already_translated = []
    
    for section_name, content in section_analyses.items():
        if not content:
            continue
            
        if _is_target_language(content, target_language):
            sections_already_translated.append(section_name)
        else:
            sections_to_translate[section_name] = content
    
    if conclusion and not _is_target_language(conclusion, target_language):
        sections_to_translate["__conclusion__"] = conclusion
    
    if sections_already_translated:
        logger.info(f"이미 목표 언어인 섹션 (번역 건너뜀): {sections_already_translated}")
    
    if not sections_to_translate:
        logger.info("모든 섹션이 이미 목표 언어입니다. 번역 건너뜀")
        return {}
    
    logger.info(f"번역할 섹션: {list(sections_to_translate.keys())}")
    logger.info(f"동적 섹션 분석 결과 번역 시작 ({language_name})")

    llm = get_llm("translate_analysis")
    
    all_translations = {}
    section_items = list(sections_to_translate.items())
    batch_size = 3
    
    for i in range(0, len(section_items), batch_size):
        batch = dict(section_items[i:i + batch_size])
        batch_num = i // batch_size + 1
        
        logger.debug(f"배치 {batch_num} 번역 중: {list(batch.keys())}")
        
        try:
            batch_translations = _translate_batch_sections(llm, batch, language_name, logger)
            
            if not batch_translations:
                logger.warning(f"배치 {batch_num} 번역 결과가 비어있습니다")
            else:
                all_translations.update(batch_translations)
                logger.debug(f"배치 {batch_num} 번역 완료: {len(batch_translations)}개")
        except Exception as e:
            logger.error(f"배치 {batch_num} 번역 실패: {e}")
    
    logger.info(f"동적 섹션 분석 결과 번역 완료: {len(all_translations)}개 섹션")
    
    translated_sections = {}
    translated_conclusion = None
    
    for key, value in all_translations.items():
        if key == "__conclusion__":
            translated_conclusion = value
        else:
            translated_sections[key] = value
    
    output = {}
    if translated_sections:
        output["section_analyses"] = translated_sections
    if translated_conclusion:
        output["conclusion"] = translated_conclusion
    
    return output

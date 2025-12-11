import json
import pathlib
from typing import Dict, List, Tuple

from ..utils.logger import get_logger


def load_keywords_from_file(file_path: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Load keywords and synonyms from a JSON file.
    
    Args:
        file_path: Path to the JSON keyword file
        
    Returns:
        Tuple of (keyword_list, synonym_dict):
        - keyword_list: List of keywords (keys from the JSON object)
        - synonym_dict: Dictionary mapping keywords to their synonyms
        
    Example JSON format:
        {
            "SPH": ["Smoothed Particle Hydrynamics"],
            "machine learning": ["ML", "artificial intelligence"]
        }
    """
    logger = get_logger("keyword_loader")
    
    if not file_path:
        logger.debug("키워드 파일 경로가 제공되지 않음, 빈 리스트 반환")
        return [], {}
    
    keyword_file = pathlib.Path(file_path)
    
    if not keyword_file.exists():
        logger.warning(f"키워드 파일이 존재하지 않음: {file_path}")
        return [], {}
    
    try:
        with open(keyword_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            logger.error(f"키워드 파일 형식 오류: 딕셔너리 형식이 아님")
            return [], {}
        
        keyword_list = list(data.keys())
        synonym_dict = {}
        
        for key, value in data.items():
            if isinstance(value, list):
                synonym_dict[key] = value
            elif isinstance(value, str):
                synonym_dict[key] = [value]
            else:
                logger.warning(f"키워드 '{key}'의 동의어 형식이 올바르지 않음, 빈 리스트로 처리")
                synonym_dict[key] = []
        
        logger.info(f"키워드 파일 로드 완료: {len(keyword_list)}개 키워드")
        return keyword_list, synonym_dict
        
    except json.JSONDecodeError as e:
        logger.error(f"키워드 파일 JSON 파싱 오류: {e}")
        return [], {}
    except Exception as e:
        logger.error(f"키워드 파일 읽기 오류: {e}")
        return [], {}


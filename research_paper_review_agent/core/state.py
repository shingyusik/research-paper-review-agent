from typing import TypedDict, List, Optional, Dict, Annotated
from operator import add


def merge_dicts(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    """Merge two dictionaries, with right values taking precedence."""
    result = left.copy() if left else {}
    if right:
        result.update(right)
    return result


class BasicInfo(TypedDict):
    authors: List[str]
    year: Optional[str]
    affiliations: List[str]
    journal: Optional[str]


class State(TypedDict, total=False):
    input_path: str
    output_path: str

    pages: List[str]
    page_count: int
    extracted_sections: Dict[str, str]

    title: str
    abstract: str
    keywords: List[str]
    original_keywords: List[str]
    keyword_synonyms: Dict[str, List[str]]
    conclusion: str
    basic_info: BasicInfo

    # Standard paper analysis fields
    background: str
    research_purpose: str
    methodologies: str
    results: str
    keypoints: str

    # Dynamic section analysis fields (for review papers)
    paper_type: str
    dynamic_sections: Dict[str, str]
    section_analyses: Annotated[Dict[str, str], merge_dicts]
    current_section_name: str
    current_section_content: str

    exceeded_fields: List[str]
    truncate_field: str
    truncate_content: str

    final_report: str


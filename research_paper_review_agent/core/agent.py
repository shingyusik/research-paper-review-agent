from typing import List, Literal, Union

from langgraph.graph import START, END, StateGraph
from langgraph.graph.state import CompiledStateGraph, StateT, ContextT, InputT, OutputT
from langgraph.types import Send

from .state import State
from ..models.schemas import Settings
from ..nodes.convert import convert_md
from ..nodes.extractors import (
    extract_title,
    extract_abstract,
    extract_conclusion,
    extract_basic_info,
    extract_keywords,
    load_keyword_file,
    re_extract_keywords,
    add_synonyms_to_keywords,
    add_new_keywords_to_file,
)
from ..nodes.analyzers import (
    analize_background,
    analize_research_purpose,
    analize_methodologies,
    analize_result,
    analize_identify_keypoints,
    analyze_dynamic_section,
)
from ..nodes.validators import check_analysis_length, route_truncate, truncate_single_field
from ..nodes.summarizers import final_summarize
from ..nodes.translators import translate_analysis
from ..nodes.preprocessors import extract_sections, detect_paper_type, extract_dynamic_sections
from ..utils.logger import get_logger


EXTRACT_NODES_PARALLEL = ["extract_conclusion", "extract_basic_info"]
STANDARD_ANALYZE_NODES = [
    "analize_background",
    "analize_research_purpose",
    "analize_methodologies",
    "analize_result",
    "analize_identify_keypoints",
]


def sync_extraction(state: State) -> dict:
    logger = get_logger("sync_extraction")
    logger.info("추출 단계 동기화 완료")
    return {}


def route_paper_type(state: State) -> Literal["extract_sections", "extract_dynamic_sections"]:
    """Route based on detected paper type."""
    paper_type = state.get("paper_type", "standard")
    if paper_type == "review":
        return "extract_dynamic_sections"
    return "extract_sections"


def route_to_analysis(state: State) -> Union[List[Send], Literal["check_analysis_length"]]:
    """Route to appropriate analysis based on paper type."""
    paper_type = state.get("paper_type", "standard")
    
    if paper_type == "review":
        dynamic_sections = state.get("dynamic_sections", {})
        
        if not dynamic_sections:
            return "check_analysis_length"
        
        return [
            Send("analyze_dynamic_section", {
                "current_section_name": section_name,
                "current_section_content": section_content,
                "title": state.get("title", ""),
                "abstract": state.get("abstract", ""),
            })
            for section_name, section_content in dynamic_sections.items()
        ]
    
    common_state = {
        "extracted_sections": state.get("extracted_sections", {}),
        "pages": state.get("pages", []),
        "title": state.get("title", ""),
        "abstract": state.get("abstract", ""),
    }
    return [
        Send("analize_background", common_state),
        Send("analize_research_purpose", common_state),
        Send("analize_methodologies", common_state),
        Send("analize_result", common_state),
        Send("analize_identify_keypoints", common_state),
    ]


def build_agent() -> CompiledStateGraph[StateT, ContextT, InputT, OutputT]:
    graph_builder = StateGraph(State)

    graph_builder.add_node("convert_md", convert_md)
    graph_builder.add_node("detect_paper_type", detect_paper_type)
    graph_builder.add_node("extract_sections", extract_sections)
    graph_builder.add_node("extract_dynamic_sections", extract_dynamic_sections)
    graph_builder.add_node("extract_title", extract_title)
    graph_builder.add_node("extract_abstract", extract_abstract)
    graph_builder.add_node("extract_conclusion", extract_conclusion)
    graph_builder.add_node("extract_basic_info", extract_basic_info)
    graph_builder.add_node("extract_keywords", extract_keywords)
    graph_builder.add_node("load_keyword_file", load_keyword_file)
    graph_builder.add_node("re_extract_keywords", re_extract_keywords)
    graph_builder.add_node("add_synonyms_to_keywords", add_synonyms_to_keywords)
    graph_builder.add_node("add_new_keywords_to_file", add_new_keywords_to_file)
    graph_builder.add_node("sync_extraction", sync_extraction)
    graph_builder.add_node("final_summarize", final_summarize)
    graph_builder.add_node("analize_background", analize_background)
    graph_builder.add_node("analize_research_purpose", analize_research_purpose)
    graph_builder.add_node("analize_methodologies", analize_methodologies)
    graph_builder.add_node("analize_result", analize_result)
    graph_builder.add_node("analize_identify_keypoints", analize_identify_keypoints)
    graph_builder.add_node("analyze_dynamic_section", analyze_dynamic_section)
    graph_builder.add_node("check_analysis_length", check_analysis_length)
    graph_builder.add_node("truncate_single_field", truncate_single_field)
    graph_builder.add_node("translate_analysis", translate_analysis)

    graph_builder.add_edge(START, "convert_md")
    graph_builder.add_edge("convert_md", "detect_paper_type")
    
    graph_builder.add_conditional_edges(
        "detect_paper_type",
        route_paper_type,
        ["extract_sections", "extract_dynamic_sections"]
    )

    section_extraction_nodes = ["extract_sections", "extract_dynamic_sections"]
    
    for section_node in section_extraction_nodes:
        graph_builder.add_edge(section_node, "extract_title")
        graph_builder.add_edge(section_node, "extract_abstract")
        for extract_node in EXTRACT_NODES_PARALLEL:
            graph_builder.add_edge(section_node, extract_node)
    
    graph_builder.add_edge("extract_title", "extract_keywords")
    graph_builder.add_edge("extract_abstract", "extract_keywords")
    
    graph_builder.add_edge("extract_keywords", "load_keyword_file")
    graph_builder.add_edge("load_keyword_file", "re_extract_keywords")
    graph_builder.add_edge("re_extract_keywords", "add_synonyms_to_keywords")
    graph_builder.add_edge("add_synonyms_to_keywords", "add_new_keywords_to_file")
    graph_builder.add_edge("add_new_keywords_to_file", "sync_extraction")
    
    graph_builder.add_edge("extract_conclusion", END)
    graph_builder.add_edge("extract_basic_info", END)

    graph_builder.add_conditional_edges(
        "sync_extraction",
        route_to_analysis,
        [
            "analize_background",
            "analize_research_purpose",
            "analize_methodologies",
            "analize_result",
            "analize_identify_keypoints",
            "analyze_dynamic_section",
            "check_analysis_length",
        ]
    )
    
    for analyze_node in STANDARD_ANALYZE_NODES:
        graph_builder.add_edge(analyze_node, "check_analysis_length")
    
    graph_builder.add_edge("analyze_dynamic_section", "check_analysis_length")
    
    graph_builder.add_conditional_edges(
        "check_analysis_length",
        route_truncate,
        ["truncate_single_field", "translate_analysis"]
    )
    graph_builder.add_edge("truncate_single_field", "translate_analysis")
    graph_builder.add_edge("translate_analysis", "final_summarize")
    graph_builder.add_edge("final_summarize", END)

    return graph_builder.compile()


def run_agent(config: Settings) -> None:
    """
    Run the research paper review agent with provided configuration.

    Args:
        config: Validated Settings object containing input_path and output_path
    """
    agent = build_agent()
    agent.invoke({
        "input_path": config.input_path,
        "output_path": config.output_path
    })

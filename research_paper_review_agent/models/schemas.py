from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class LLMNodesConfig(BaseModel):
    """Pydantic model for LLM node-specific configurations."""
    extract_title: Optional[str] = Field(default=None, description="LLM model for title extraction")
    extract_abstract: Optional[str] = Field(default=None, description="LLM model for abstract extraction")
    extract_conclusion: Optional[str] = Field(default=None, description="LLM model for conclusion extraction")
    extract_basic_info: Optional[str] = Field(default=None, description="LLM model for basic info extraction")
    extract_keywords: Optional[str] = Field(default=None, description="LLM model for keywords extraction")
    analize_background: Optional[str] = Field(default=None, description="LLM model for background analysis")
    analize_research_purpose: Optional[str] = Field(default=None, description="LLM model for research purpose analysis")
    analize_methodologies: Optional[str] = Field(default=None, description="LLM model for methodology analysis")
    analize_result: Optional[str] = Field(default=None, description="LLM model for result analysis")
    analize_identify_keypoints: Optional[str] = Field(default=None, description="LLM model for keypoints identification")
    translate_analysis: Optional[str] = Field(default=None, description="LLM model for translation")
    detect_paper_type: Optional[str] = Field(default=None, description="LLM model for paper type detection")
    extract_dynamic_sections: Optional[str] = Field(default=None, description="LLM model for dynamic section extraction")
    analyze_dynamic_section: Optional[str] = Field(default=None, description="LLM model for dynamic section analysis")

    class Config:
        extra = "allow"


class LLMConfig(BaseModel):
    """Pydantic model for LLM configuration."""
    default_model: str = Field(description="Default LLM model to use (format: 'provider:model_name')")
    nodes: LLMNodesConfig = Field(default_factory=LLMNodesConfig, description="Node-specific LLM model configurations")

    @field_validator("default_model")
    @classmethod
    def validate_model_format(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError(
                f"Invalid model format '{v}'. Expected format: 'provider:model_name' (e.g., 'openai:gpt-4o-mini')"
            )
        provider, model = v.split(":", 1)
        if not provider or not model:
            raise ValueError(
                f"Invalid model format '{v}'. Both provider and model name are required (e.g., 'openai:gpt-4o-mini')"
            )
        return v


class Settings(BaseModel):
    """Pydantic model for application settings configuration."""
    input_path: str = Field(description="Path to input PDF file")
    output_path: str = Field(description="Path to output directory for generated markdown files")
    target_language: str = Field(default="ko", description="Target language for translation (e.g., 'ko', 'en', 'ja')")
    max_analysis_length: int = Field(default=500, description="Maximum character length for analysis outputs")
    paper_type: str = Field(default="auto", description="Paper type: 'auto' (LLM detection), 'standard' (research paper), 'review' (review/survey paper)")
    keyword_file_path: Optional[str] = Field(default=None, description="Path to JSON file containing keywords and synonyms")
    llm: LLMConfig = Field(description="LLM configuration settings")

    @field_validator("target_language")
    @classmethod
    def validate_language_code(cls, v: str) -> str:
        valid_languages = {"ko", "en", "ja", "zh", "de", "fr", "es", "pt", "ru"}
        if v.lower() not in valid_languages:
            raise ValueError(
                f"Invalid target_language '{v}'. Supported languages: {', '.join(sorted(valid_languages))}"
            )
        return v.lower()

    @field_validator("paper_type")
    @classmethod
    def validate_paper_type(cls, v: str) -> str:
        valid_types = {"auto", "standard", "review"}
        if v.lower() not in valid_types:
            raise ValueError(
                f"Invalid paper_type '{v}'. Supported types: {', '.join(sorted(valid_types))}"
            )
        return v.lower()

    @model_validator(mode="after")
    def validate_paths(self) -> "Settings":
        if not self.input_path:
            raise ValueError("input_path cannot be empty")
        if not self.output_path:
            raise ValueError("output_path cannot be empty")
        return self


class BasicInfoModel(BaseModel):
    """Pydantic model for structured output extraction of basic paper info."""
    authors: List[str] = Field(default_factory=list, description="List of author names")
    year: Optional[str] = Field(default=None, description="Publication year")
    affiliations: List[str] = Field(default_factory=list, description="List of author affiliations/institutions")
    journal: Optional[str] = Field(default=None, description="Journal or conference name")


class KeywordsModel(BaseModel):
    """Pydantic model for structured output extraction of keywords."""
    keywords: List[str] = Field(default_factory=list, description="List of keywords extracted from the paper")


class TranslatedAnalysisModel(BaseModel):
    """Pydantic model for structured output of translated analysis sections."""
    background: str = Field(description="Translated research background analysis")
    research_purpose: str = Field(description="Translated research purpose analysis")
    methodologies: str = Field(description="Translated methodology analysis")
    results: str = Field(description="Translated results analysis")
    keypoints: str = Field(description="Translated key contributions and differentiators")
    conclusion: str = Field(description="Translated conclusion")


class TranslationItem(BaseModel):
    """Single translation item with key-value pair."""
    key: str = Field(description="Original section/field name")
    value: str = Field(description="Translated text")


class TranslationList(BaseModel):
    """List of translation items for structured output."""
    items: List[TranslationItem] = Field(default_factory=list, description="List of translated items")


class SectionRange(BaseModel):
    """Line range for a section."""
    start_line: Optional[int] = Field(default=None, description="Start line number (1-indexed, inclusive)")
    end_line: Optional[int] = Field(default=None, description="End line number (1-indexed, inclusive)")


class SectionRanges(BaseModel):
    """Line ranges for each paper section."""
    introduction: SectionRange = Field(default_factory=SectionRange, description="Introduction/Background section range")
    methods: SectionRange = Field(default_factory=SectionRange, description="Methods/Methodology section range")
    results: SectionRange = Field(default_factory=SectionRange, description="Results/Experiments section range")
    discussion: SectionRange = Field(default_factory=SectionRange, description="Discussion/Conclusion section range")


class PaperTypeModel(BaseModel):
    """Model for paper type detection result."""
    paper_type: str = Field(description="Detected paper type: 'standard' or 'review'")
    reasoning: str = Field(description="Brief explanation for the classification")


class DynamicSection(BaseModel):
    """Dynamic section with name and line range."""
    name: str = Field(description="Section name/title as it appears in the paper")
    start_line: int = Field(description="Start line number (1-indexed, inclusive)")
    end_line: int = Field(description="End line number (1-indexed, inclusive)")


class DynamicSectionRanges(BaseModel):
    """List of dynamically detected sections."""
    sections: List[DynamicSection] = Field(default_factory=list, description="List of detected sections")
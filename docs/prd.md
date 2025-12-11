# **Product Requirements Document (PRD): AI-Powered Academic Paper Summarization Agent**

## **# Overview**

An AI agent that automatically analyzes academic papers in PDF format and generates structured Markdown summaries. Designed for researchers, graduate students, and R&D professionals who need to quickly grasp a paper's core problem, methodology, and results without reading the entire document.

## **# Core Features**

All features use LLM processing except the initial PDF conversion. The workflow is orchestrated via LangGraph.

* **1. PDF to Markdown Conversion (convert_md)**
  Converts PDF to Markdown using `PyMuPDF` and `PyMuPDF4LLM`. Cleans complex layouts (multi-column, footnotes, figures) into LLM-readable text.

* **2. Paper Type Detection (detect_paper_type)**
  Uses LLM to classify papers as "standard" (research) or "review" (survey), determining subsequent processing paths.

* **3. Section Extraction (extract_sections / extract_dynamic_sections)**
  Extracts structured sections via LLM: predefined sections (introduction, methods, results, discussion) for standard papers, or dynamically identified sections for review papers.

* **4. Parallel Metadata Extraction (extract\_...)**
  Concurrently extracts title, authors, abstract, keywords, and conclusion using parallel LLM calls with optimized prompts.

* **5. Enhanced Keyword Processing (load_keyword_file, re_extract_keywords, add_synonyms_to_keywords, add_new_keywords_to_file)**
  Loads domain-specific keywords, re-extracts with enhanced context, adds synonyms, and automatically updates the keyword file with new terms found in papers.

* **6. In-depth Content Analysis (analyze\_...)**
  Parallel LLM analysis of background, purpose, methodologies, results, and key contributions. For review papers, analyzes each detected section separately.

* **7. Analysis Length Validation (check_analysis_length, truncate_single_field)**
  Validates outputs against `max_analysis_length` and intelligently truncates exceeding fields using LLM while preserving key information.

* **8. Translation (translate_analysis)**
  Translates all analysis fields into the configured target language, preserving technical accuracy.

* **9. Final Report Generation (final_summarize)**
  Consolidates all extracted and analyzed information into a coherent, well-structured Markdown report with logical flow.

## **# User Experience**

* **User Personas:**
  * **Researchers/Graduate Students:** Quickly assess paper relevance and key contributions without reading entire papers.
  * **R&D Professionals:** Track competitor technology and latest AI models, sharing summaries with teams.

* **User Flow:**
  1. Configure `config/settings.json` with `input_path` (PDF file) and `output_path` (output directory).
  2. Optionally set `target_language`, `max_analysis_length`, `paper_type`, `llm` config, and `keyword_file_path`.
  3. Set up `.env` file with LLM API keys.
  4. Run `python main.py` (or `python main.py -c path/to/settings.json`).
  5. Agent validates config, processes PDF, and saves Markdown summary to output directory.

* **UI/UX:**
  * CLI with structured logging (configurable levels: DEBUG, INFO, WARNING, ERROR).
  * Pydantic-based config validation with clear error messages.
  * CLI options: `-c/--config` (custom settings path), `--log-level` (logging verbosity).
  * Comprehensive error handling with actionable feedback.

## **# Technical Architecture**

* **System Components:**
  * **Orchestration:** `LangGraph` with conditional routing and parallel execution.
  * **Core:** Python with modular package structure (`research_paper_review_agent`).
  * **PDF Processing:** `PyMuPDF` and `PyMuPDF4LLM` for PDF parsing and Markdown conversion.
  * **LLM Interface:** `LangChain` with unified format `provider:model_name` (e.g., `openai:gpt-4o-mini`).
  * **Config Management:** `Pydantic` validation with path expansion, env variable loading, and node-specific LLM config.
  * **Dependencies:** `uv` package manager with `pyproject.toml`.
  * **Logging:** Structured logging with configurable levels.
  * **CLI:** `argparse`-based interface.

* **Data Models:**
  * **`config/settings.json`:** Contains `input_path`, `output_path`, `target_language`, `max_analysis_length`, `paper_type`, `llm` config, and optional `keyword_file_path`.
  * **`State` (TypedDict):** Manages graph state with fields for input/output, PDF processing, metadata, analysis results, dynamic sections, validation, and final report.
  * **Pydantic Schemas:** `Settings`, `LLMConfig`, `BasicInfoModel`, `KeywordsModel`, `TranslatedAnalysisModel`, `PaperTypeModel`, `DynamicSectionRanges`.

* **APIs and Infrastructure:**
  * LLM provider APIs (OpenAI, Google, Anthropic) via environment variables (`.env` file).
  * Node-specific model configuration for fine-tuning.
  * Requirements: Python 3.9+, `uv`, internet connection, LLM API keys.

## **# Development Roadmap**

* **MVP Status (Completed):**
  * ✅ Full LangGraph workflow with Pydantic-based config validation
  * ✅ All LLM nodes implemented (extraction, analysis, validation, translation, final report)
  * ✅ Paper type detection, dynamic section handling, enhanced keyword processing
  * ✅ Analysis length validation, multi-language translation, node-specific LLM config
  * ✅ CLI interface, error handling, structured logging
  * ✅ `pyproject.toml` and `uv.lock` for reproducible builds

* **Future Enhancements:**
  * Batch processing for multiple PDFs
  * Web UI (Streamlit/Gradio)
  * Quality check node with feedback loop
  * URL-based paper processing (ArXiv)
  * LLM call caching
  * Additional output formats (JSON, HTML, LaTeX)
  * Reference management integration (Zotero, Mendeley)
  * Multi-document comparison

## **# Logical Dependency Chain**

**Flow:** `convert_md` → `detect_paper_type` → `extract_sections/extract_dynamic_sections` → parallel metadata extraction (`extract_title`, `extract_abstract`, `extract_conclusion`, `extract_basic_info`) → keyword processing (`extract_keywords` → `load_keyword_file` → `re_extract_keywords` → `add_synonyms_to_keywords` → `add_new_keywords_to_file`) → `sync_extraction` → conditional analysis routing (standard: parallel `analize_*` nodes; review: `analyze_dynamic_section` per section) → `check_analysis_length` → `truncate_single_field` (if needed) → `translate_analysis` → `final_summarize`.

**Architecture:** Modular design with low coupling. Each node is independently testable and improvable, supporting incremental development.

## **# Risks and Mitigations**

* **Technical:**
  * **PDF parsing errors:** Tested with various formats; future: robust preprocessing for edge cases (two-column, complex tables).
  * **LLM hallucination:** Structured output (Pydantic models) and prompt engineering reduce errors; future: cross-validation against original text.
  * **Output length:** `max_analysis_length` with automatic LLM-based truncation.

* **Configuration:**
  * **User errors:** Pydantic validation with clear error messages, path expansion, sample config file.
  * **Model inconsistency:** Unified `provider:model_name` format with node-specific config; cost-effective defaults.

* **Resources:**
  * **API costs:** Cost-effective default models (`gpt-4o-mini`), node-specific config for strategic upgrades; future: caching.
  * **Processing time:** Parallel execution, length validation; future: progress tracking, resumable processing.

* **Maintenance:**
  * **Scalability:** Modular architecture (nodes, services, models, utils) with independent, testable nodes and structured logging.

# Academic Paper Review Agent

학술 논문 PDF를 자동으로 분석하여 구조화된 Markdown 요약을 생성하는 AI 에이전트입니다.

## 주요 기능

- PDF를 Markdown으로 자동 변환
- 논문 타입 자동 감지 (연구 논문 / 리뷰 논문)
- 메타데이터 추출 (제목, 저자, 초록, 키워드, 결론)
- 심층 분석 (배경, 연구 목적, 방법론, 결과, 핵심 기여점)
- 다국어 번역 지원
- 키워드 자동 확장 및 학습

## 설치

### 요구사항

- Python 3.12+
- `uv` 패키지 매니저

### 설치 방법

```bash
# uv 설치 (미설치 시)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync
```

## 사용 방법

### 1. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 LLM API 키를 설정합니다:

```env
OPENAI_API_KEY=your_api_key_here
```

### 2. 설정 파일 구성

`config/settings.json` 파일을 생성하고 다음 내용을 작성합니다:

```json
{
    "input_path": "PDF/sample_01/2508.19205v1.pdf",
    "output_path": "PDF/sample_01",
    "keyword_file_path": "config/keywords.json",
    "target_language": "ko",
    "max_analysis_length": 1000,
    "paper_type": "auto",
    "llm": {
        "default_model": "openai:gpt-4o-mini",
        "nodes": {
            "extract_title": "openai:gpt-4o-mini"
        }
    }
}
```

**주요 설정 항목:**
- `input_path`: 분석할 PDF 파일 경로
- `output_path`: 결과 Markdown 파일이 저장될 디렉토리
- `target_language`: 번역 대상 언어 (ko, en, ja 등)
- `max_analysis_length`: 분석 결과 최대 길이 (문자 수)
- `paper_type`: "auto" (자동 감지), "standard" (연구 논문), "review" (리뷰 논문)
- `llm`: LLM 모델 설정 (기본 모델 및 노드별 모델 오버라이드)

### 3. 실행

```bash
# 기본 설정 파일 사용
python main.py

# 커스텀 설정 파일 지정
python main.py -c path/to/settings.json

# 로그 레벨 설정
python main.py --log-level DEBUG
```

## 아키텍처

이 프로젝트는 **LangGraph**를 사용하여 워크플로우를 구성합니다.

### 워크플로우

```
convert_md (PDF → Markdown)
    ↓
detect_paper_type (논문 타입 감지)
    ↓
extract_sections / extract_dynamic_sections (섹션 추출)
    ↓
[병렬] extract_title, extract_abstract, extract_conclusion, extract_basic_info
    ↓
extract_keywords → load_keyword_file → re_extract_keywords → add_synonyms_to_keywords → add_new_keywords_to_file
    ↓
sync_extraction (동기화)
    ↓
[조건부 라우팅]
    ├─ standard: [병렬] analize_background, analize_research_purpose, analize_methodologies, analize_result, analize_identify_keypoints
    └─ review: analyze_dynamic_section (각 섹션별)
    ↓
check_analysis_length (길이 검증)
    ↓
truncate_single_field (필요시 자동 축약)
    ↓
translate_analysis (번역)
    ↓
final_summarize (최종 보고서 생성)
```

### 주요 구성 요소

- **노드 (Nodes)**: 각 처리 단계를 담당하는 독립적인 함수들
- **상태 (State)**: LangGraph의 TypedDict로 정의된 워크플로우 상태 관리
- **조건부 라우팅**: 논문 타입에 따라 다른 분석 경로 선택
- **병렬 처리**: 독립적인 작업들을 동시에 실행하여 성능 최적화

### 프로젝트 구조

```
research_paper_review_agent/
├── core/           # 에이전트 및 상태 관리
├── nodes/          # 워크플로우 노드들
│   ├── convert.py          # PDF 변환
│   ├── extractors.py       # 메타데이터 추출
│   ├── analyzers.py        # 심층 분석
│   ├── translators.py      # 번역
│   ├── summarizers.py      # 최종 요약
│   ├── validators.py       # 검증
│   └── preprocessors.py    # 전처리
├── services/       # 설정 및 LLM 서비스
├── models/         # Pydantic 스키마
├── utils/          # 유틸리티 함수
└── interface/      # CLI 인터페이스
```

## 라이선스

MIT License


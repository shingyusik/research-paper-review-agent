import pymupdf
import pathlib
import re

from ..core.state import State
from ..utils.logger import get_logger

logger = get_logger("convert_md")


def convert_md(state: State) -> State:
    """
    Convert PDF to Markdown with page-by-page splitting

    Args:
        state: State object with input_path field

    Returns:
        Dict with keys:
            - 'output_path': Path to the combined markdown file
            - 'pages': List of markdown text for each page
            - 'page_count': Total number of pages
    """
    pdf_path = pathlib.Path(state['input_path']).expanduser()
    logger.info(f"PDF 변환 시작: {pdf_path.name}")

    current_file = pathlib.Path(__file__)
    output_dir = current_file.parent / "converted_md"
    output_dir.mkdir(exist_ok=True)

    pdf_filename = pdf_path.stem
    output_path = output_dir / "converted_md.md"

    page_texts = []

    doc = pymupdf.open(str(pdf_path))
    md_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        lines = text.split('\n')
        filtered_lines = []
        for line in lines:
            if re.match(r'^\s*\d{1,3}\s*$', line):
                continue
            filtered_lines.append(line)

        cleaned_text = '\n'.join(filtered_lines)

        if cleaned_text.strip():
            md_parts.append(f"# Page {page_num + 1}\n\n{cleaned_text}\n\n")
            page_texts.append(cleaned_text.strip())
        else:
            page_texts.append("")

    doc.close()
    md_text = ''.join(md_parts)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_text)

    result = {
        'pages': page_texts,
        'page_count': len(page_texts)
    }

    logger.info(f"총 {len(page_texts)} 페이지 변환 완료")
    
    return result


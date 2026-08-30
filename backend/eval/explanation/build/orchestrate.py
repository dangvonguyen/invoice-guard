"""IO glue for ``python -m eval.explanation.build``: read the PDF, write fixtures."""

import json

from app.services.extraction.text import PdfTextExtractor
from eval.explanation.build import schema
from eval.explanation.build.casefile import iter_case_dirs, load_case_dir
from eval.explanation.build.chunking import IdentifiedChunk, chunk_handbook
from eval.explanation.build.constants import CHUNKER
from eval.explanation.build.prompts import render_case_prompt
from eval.explanation.paths import (
    CHUNKS_JSON,
    GENERATED_SCHEMA_PATH,
    HANDBOOK_MD,
    HANDBOOK_PDF,
    INSTRUCTIONS_PATH,
    PROMPT_TXT,
)


def build() -> None:
    """Regenerate every artifact the diff gate covers for this task."""
    chunks = _build_handbook()
    _build_static_fixtures()
    _build_case_prompts(chunks)


def _build_handbook() -> list[IdentifiedChunk]:
    text = PdfTextExtractor().extract_text(HANDBOOK_PDF.read_bytes())
    HANDBOOK_MD.parent.mkdir(parents=True, exist_ok=True)
    HANDBOOK_MD.write_text(text)

    chunks = chunk_handbook(text)
    payload = {
        "chunker": CHUNKER,
        "chunks": [
            {"id": chunk.id, "label": chunk.label, "content": chunk.content}
            for chunk in chunks
        ],
    }
    CHUNKS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return chunks


def _build_static_fixtures() -> None:
    INSTRUCTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    INSTRUCTIONS_PATH.write_text(schema.render_instructions())
    GENERATED_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_SCHEMA_PATH.write_text(schema.render_output_schema())


def _build_case_prompts(chunks: list[IdentifiedChunk]) -> None:
    """Validate each case and write its ``prompt.txt``."""
    for case_dir in iter_case_dirs():
        case = load_case_dir(case_dir, chunks)
        (case_dir / PROMPT_TXT).write_text(render_case_prompt(case, chunks))

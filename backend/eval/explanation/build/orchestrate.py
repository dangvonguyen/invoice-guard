"""IO glue for ``python -m eval.explanation.build``: read the PDF, write fixtures."""

import json

from app.services.extraction.text import PdfTextExtractor
from eval.explanation.build import schema
from eval.explanation.build.chunking import chunk_handbook
from eval.explanation.build.constants import CHUNKER
from eval.explanation.paths import (
    CHUNKS_JSON,
    GENERATED_SCHEMA_PATH,
    HANDBOOK_MD,
    HANDBOOK_PDF,
    INSTRUCTIONS_PATH,
)


def build() -> None:
    """Regenerate every artifact the diff gate covers for this task."""
    _build_handbook()
    _build_static_fixtures()


def _build_handbook() -> None:
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


def _build_static_fixtures() -> None:
    INSTRUCTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    INSTRUCTIONS_PATH.write_text(schema.render_instructions())
    GENERATED_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_SCHEMA_PATH.write_text(schema.render_output_schema())

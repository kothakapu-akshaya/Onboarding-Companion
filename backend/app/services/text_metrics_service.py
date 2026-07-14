"""Service to compute text metrics from extracted text segments.

Computes word, sentence, and character counts from extracted text
segments and updates the ExtractedText model.
"""

import logging
import re
from typing import Any

from app.models.extracted_text import ExtractedText

logger = logging.getLogger(__name__)


def compute_text_metrics_from_segments(
    segments: list[dict[str, Any]] | None,
) -> tuple[int, int, int]:
    """Compute word, sentence, and character counts from segment texts.

    Returns (word_count, character_count, sentence_count).
    """
    if not segments:
        return (0, 0, 0)

    word_count = 0
    character_count = 0
    sentence_count = 0

    for segment in segments:
        text = segment.get("text", "")
        if not text:
            continue

        character_count += len(text)

        words = [w for w in re.split(r"\s+", text) if w]
        word_count += len(words)

        sentences = [s for s in re.split(r"[.!?]+\s*", text) if s]
        sentence_count += len(sentences)

    return (word_count, character_count, sentence_count)


def update_extracted_text_metrics(
    extracted_text: ExtractedText,
    segments: list[dict[str, Any]] | None,
) -> None:
    """Compute text metrics from segments and update ExtractedText in-place."""
    wc, cc, sc = compute_text_metrics_from_segments(segments)
    extracted_text.word_count = wc
    extracted_text.character_count = cc
    extracted_text.sentence_count = sc

    logger.info(
        f"Updated text metrics for extracted_text "
        f"{extracted_text.record_id}: "
        f"word_count={wc}, character_count={cc}, sentence_count={sc}"
    )

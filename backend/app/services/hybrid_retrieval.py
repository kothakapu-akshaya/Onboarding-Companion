"""Hybrid retrieval service for RAG functionality."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

# ── Telugu + English question / stop words ──────────────────────────
_TELUGU_STOP_WORDS: set[str] = {
    "ఎవరు",
    "ఏమిటి",
    "ఎక్కడ",
    "ఎప్పుడు",
    "ఎందుకు",
    "ఎలా",
    "ఎంత",
    "ఏమి",
    "ఎవరి",
    "ఎవరిని",
    "ఎవరినైనా",
    "ఎవరికైనా",
    "గురించి",
    "వివరించండి",
    "చెప్పండి",
    "వివరణ",
    "ఇవ్వండి",
    "ఉంది",
    "ఉన్నాయి",
    "ఉన్నది",
    "ఉంటుంది",
    "అనేది",
    "ఈ",
    "ఆ",
    "ఇది",
    "అది",
    "ఇక్కడ",
    "అక్కడ",
    "ఒక",
    "చాలా",
    "మరియు",
    "లేదా",
    "కానీ",
    "అందువల్ల",
    "గా",
    "ను",
    "ని",
    "కు",
    "లో",
    "కి",
    "వల్ల",
    "తో",
    "పై",
}

_ENGLISH_STOP_WORDS: set[str] = {
    "who",
    "what",
    "where",
    "when",
    "why",
    "how",
    "which",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "done",
    "doing",
    "tell",
    "about",
    "describe",
    "explain",
    "say",
    "the",
    "a",
    "an",
    "this",
    "that",
    "these",
    "those",
    "and",
    "or",
    "but",
    "so",
    "if",
    "then",
    "than",
    "of",
    "in",
    "on",
    "at",
    "to",
    "for",
    "with",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "under",
    "i",
    "me",
    "my",
    "myself",
    "we",
    "our",
    "you",
    "your",
    "he",
    "him",
    "his",
    "she",
    "her",
    "it",
    "its",
    "they",
    "them",
    "their",
    "there",
    "here",
}


class HybridRetrievalService:
    """Hybrid retrieval service combining FTS and trigram-based search."""

    # ── Query normalization ─────────────────────────────────────────

    @staticmethod
    def _strip_stop_words(query: str) -> str:
        """Remove Telugu and English question/stop words."""
        tokens = query.split()
        cleaned: list[str] = []
        for token in tokens:
            lower = token.lower().strip("?.,!;:")
            if lower in _TELUGU_STOP_WORDS or lower in _ENGLISH_STOP_WORDS:
                continue
            cleaned.append(token)
        return " ".join(cleaned)

    @staticmethod
    def _normalize_query(query: str) -> str:
        compact = re.sub(r"\s+", " ", query).strip()
        stripped = HybridRetrievalService._strip_stop_words(compact)
        # Collapse multiple spaces after stripping
        return re.sub(r"\s+", " ", stripped).strip()

    @staticmethod
    def _build_or_tsquery(query: str) -> str:
        """Build an explicit OR tsquery from query tokens.

        E.g. 'తెనాలి రామకృష్ణ' -> 'తెనాలి | రామకృష్ణ'
        """
        tokens = [t for t in query.split() if t]
        if not tokens:
            return ""
        return " | ".join(tokens)

    @staticmethod
    def _segments_cte_sql() -> str:
        """Shared SQL fragment for fetching extracted-text segments."""
        return """
            WITH segments AS (
                SELECT
                    (row_number() OVER ()) - 1 AS idx,
                    seg.text AS seg_text,
                    seg.page,
                    seg.start,
                    seg.end_time AS "end",
                    seg.bbox,
                    seg.type AS segment_type,
                    seg.reading_order
                FROM extractedtext,
                jsonb_to_recordset(extractedtext.segments) AS seg(
                    text text,
                    page text,
                    start float,
                    end_time float,
                    bbox jsonb,
                    type text,
                    reading_order int
                )
                WHERE extractedtext.record_id = :record_id
            )
        """

    # ── Core hybrid query using jsonb_to_recordset ──────────────────

    @staticmethod
    def _run_hybrid_query(
        session: Session,
        record_id: UUID,
        query: str,
        top_k: int,
        trigram_threshold: float,
        use_or_tsquery: bool = False,
    ) -> list[dict[str, Any]]:
        ts_query_func = (
            "to_tsquery" if use_or_tsquery else "websearch_to_tsquery"
        )
        search_term = (
            HybridRetrievalService._build_or_tsquery(query)
            if use_or_tsquery
            else query
        )

        if use_or_tsquery and not search_term:
            return []

        sql_template = """
            {segments_cte},
            ranked AS (
                SELECT
                    idx,
                    seg_text,
                    page,
                    start,
                    "end",
                    bbox,
                    segment_type,
                    reading_order,
                    ts_rank_cd(
                        to_tsvector('simple', seg_text),
                        {ts_query_func}('simple', :search_term)
                    ) AS fts_score,
                    similarity(seg_text, :query) AS trigram_score
                FROM segments
            )
            SELECT
                idx,
                seg_text,
                page,
                start,
                "end",
                bbox,
                segment_type,
                reading_order,
                fts_score,
                trigram_score,
                (0.75 * fts_score + 0.25 * trigram_score) AS hybrid_score
            FROM ranked
            WHERE
                to_tsvector('simple', seg_text)
                    @@ {ts_query_func}('simple', :search_term)
                OR trigram_score >= :trigram_threshold
            ORDER BY hybrid_score DESC, idx
            LIMIT :top_k
            """  # nosec B608
        query_sql = text(
            sql_template.replace(
                "{segments_cte}", HybridRetrievalService._segments_cte_sql()
            ).replace("{ts_query_func}", ts_query_func)
        )
        params = {
            "record_id": record_id,
            "query": query,
            "search_term": search_term,
            "top_k": top_k,
            "trigram_threshold": trigram_threshold,
        }

        rows = session.execute(query_sql, params=params).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def _run_fts_fallback_query(
        session: Session,
        record_id: UUID,
        query: str,
        top_k: int,
        use_or_tsquery: bool = False,
    ) -> list[dict[str, Any]]:
        ts_query_func = (
            "to_tsquery" if use_or_tsquery else "websearch_to_tsquery"
        )
        search_term = (
            HybridRetrievalService._build_or_tsquery(query)
            if use_or_tsquery
            else query
        )

        if use_or_tsquery and not search_term:
            return []

        sql_template = """
            {segments_cte}
            SELECT
                idx,
                seg_text,
                page,
                start,
                "end",
                bbox,
                segment_type,
                reading_order,
                ts_rank_cd(
                    to_tsvector('simple', seg_text),
                    {ts_query_func}('simple', :search_term)
                ) AS fts_score,
                0.0::float AS trigram_score,
                ts_rank_cd(
                    to_tsvector('simple', seg_text),
                    {ts_query_func}('simple', :search_term)
                ) AS hybrid_score
            FROM segments
            WHERE
                to_tsvector('simple', seg_text)
                    @@ {ts_query_func}('simple', :search_term)
            ORDER BY hybrid_score DESC, idx
            LIMIT :top_k
            """  # nosec B608
        query_sql = text(
            sql_template.replace(
                "{segments_cte}", HybridRetrievalService._segments_cte_sql()
            ).replace("{ts_query_func}", ts_query_func)
        )
        params = {
            "record_id": record_id,
            "search_term": search_term,
            "top_k": top_k,
        }

        rows = session.execute(query_sql, params=params).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def _run_tokenwise_fallback_query(
        session: Session,
        record_id: UUID,
        query: str,
        top_k: int,
        trigram_threshold: float = 0.1,
    ) -> list[dict[str, Any]]:
        tokens = [t for t in query.split() if len(t) >= 2]
        if not tokens:
            return []

        conditions = []
        for i, token in enumerate(tokens):
            case_expr = (
                f"CASE WHEN seg_text ILIKE :token_{i} "
                f"OR similarity(seg_text, :token_{i}) >= :trig_thresh "
                f"THEN 1 ELSE 0 END"
            )
            conditions.append(case_expr)

        score_expr = (
            " + ".join(conditions) if len(conditions) > 1 else conditions[0]
        )

        sql_template = """
            {segments_cte}
            SELECT
                idx,
                seg_text,
                page,
                start,
                "end",
                bbox,
                segment_type,
                reading_order,
                0.0::float AS fts_score,
                0.0::float AS trigram_score,
                ({score_expr})::float AS hybrid_score
            FROM segments
            WHERE ({score_expr}) > 0
            ORDER BY hybrid_score DESC, idx
            LIMIT :top_k
            """  # nosec B608
        query_sql = text(
            sql_template.replace(
                "{segments_cte}", HybridRetrievalService._segments_cte_sql()
            ).replace("{score_expr}", score_expr)
        )

        params: dict[str, Any] = {
            "record_id": record_id,
            "top_k": top_k,
            "trig_thresh": trigram_threshold,
        }
        for i, token in enumerate(tokens):
            params[f"token_{i}"] = f"%{token}%"

        rows = session.execute(query_sql, params=params).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def _expand_with_neighbors(
        session: Session,
        record_id: UUID,
        matches: list[dict[str, Any]],
        context_window: int,
    ) -> list[dict[str, Any]]:
        if not matches:
            return []

        match_scores = {
            int(match["idx"]): float(match.get("hybrid_score") or 0.0)
            for match in matches
        }

        context_indices: set[int] = set()
        for matched_idx in match_scores:
            for idx in range(
                matched_idx - context_window,
                matched_idx + context_window + 1,
            ):
                if idx >= 0:
                    context_indices.add(idx)

        # Fetch expanded segments from the JSONB array
        sql_template = """
            {segments_cte}
            SELECT * FROM segments
            WHERE idx IN :indices
            ORDER BY idx
            """  # nosec B608
        query_sql = text(
            sql_template.replace(
                "{segments_cte}", HybridRetrievalService._segments_cte_sql()
            )
        )

        params = {
            "record_id": record_id,
            "indices": tuple(context_indices),
        }

        rows = session.execute(query_sql, params=params).mappings().all()

        context_segments: list[dict[str, Any]] = []
        for row in rows:
            idx = int(row["idx"])
            context_segments.append(
                {
                    "segment_index": idx,
                    "text": row["seg_text"],
                    "page": row["page"],
                    "start": row["start"],
                    "end": row["end"],
                    "bbox": row.get("bbox"),
                    "type": row.get("segment_type"),
                    "reading_order": row.get("reading_order"),
                    "is_match": idx in match_scores,
                    "score": match_scores.get(idx),
                }
            )

        return context_segments

    # ── Main retrieve entry point ───────────────────────────────────

    @staticmethod
    def retrieve(
        session: Session,
        record_id: UUID,
        extracted_text: Any,
        query: str,
        top_k: int = 8,
        context_window: int = 1,
        trigram_threshold: float = 0.20,
        use_enhanced_retrieval: bool = False,
    ) -> dict[str, Any]:
        """Retrieve segments using hybrid search on extracted text.

        The ``extracted_text`` parameter is used as an early-exit guard:
        when the record has no segments, we return empty immediately
        without issuing database queries.
        """
        normalized_query = HybridRetrievalService._normalize_query(query)
        if (
            not normalized_query
            or not extracted_text
            or not extracted_text.segments
        ):
            return {
                "strategy": "hybrid_jsonb",
                "matched_segments": [],
                "context_segments": [],
                "stats": {
                    "total_segments": 0,
                    "matched_count": 0,
                    "context_count": 0,
                    "used_fallback": False,
                },
            }

        used_fallback = False
        matches: list[dict[str, Any]] = []

        if use_enhanced_retrieval:
            try:
                matches = HybridRetrievalService._run_hybrid_query(
                    session=session,
                    record_id=record_id,
                    query=normalized_query,
                    top_k=top_k,
                    trigram_threshold=max(0.05, trigram_threshold - 0.05),
                    use_or_tsquery=True,
                )
            except SQLAlchemyError:
                used_fallback = True
                matches = HybridRetrievalService._run_fts_fallback_query(
                    session=session,
                    record_id=record_id,
                    query=normalized_query,
                    top_k=top_k,
                    use_or_tsquery=True,
                )

            if not matches:
                used_fallback = True
                matches = HybridRetrievalService._run_tokenwise_fallback_query(
                    session=session,
                    record_id=record_id,
                    query=normalized_query,
                    top_k=top_k,
                    trigram_threshold=0.1,
                )
        else:
            try:
                matches = HybridRetrievalService._run_hybrid_query(
                    session=session,
                    record_id=record_id,
                    query=normalized_query,
                    top_k=top_k,
                    trigram_threshold=trigram_threshold,
                    use_or_tsquery=False,
                )
            except SQLAlchemyError:
                used_fallback = True
                matches = HybridRetrievalService._run_fts_fallback_query(
                    session=session,
                    record_id=record_id,
                    query=normalized_query,
                    top_k=top_k,
                    use_or_tsquery=False,
                )

        mapped_matches = [
            {
                "segment_index": int(match.get("idx", 0)),
                "text": match.get("seg_text", ""),
                "page": match.get("page"),
                "start": match.get("start"),
                "end": match.get("end"),
                "bbox": match.get("bbox"),
                "type": match.get("segment_type"),
                "reading_order": match.get("reading_order"),
                "fts_score": float(match.get("fts_score") or 0.0),
                "trigram_score": float(match.get("trigram_score") or 0.0),
                "hybrid_score": float(match.get("hybrid_score") or 0.0),
            }
            for match in matches
        ]

        context_segments = HybridRetrievalService._expand_with_neighbors(
            session=session,
            record_id=record_id,
            matches=matches,
            context_window=max(0, context_window),
        )

        # Get total segment count from JSONB for stats
        total_stmt = text(
            "SELECT COALESCE(jsonb_array_length(segments), 0) "
            "FROM extractedtext WHERE record_id = :record_id"
        )
        total_segments = (
            session.execute(total_stmt, {"record_id": record_id}).scalar() or 0
        )

        strategy = (
            "hybrid_jsonb" if use_enhanced_retrieval else "hybrid_jsonb_basic"
        )

        return {
            "strategy": strategy,
            "matched_segments": mapped_matches,
            "context_segments": context_segments,
            "stats": {
                "total_segments": total_segments,
                "matched_count": len(mapped_matches),
                "context_count": len(context_segments),
                "used_fallback": used_fallback,
            },
        }

"""Metadata indexing service for semantic RAG validation."""

from typing import Any


class MetadataIndexer:
    """Validates and optimizes semantic metadata for storage."""

    @staticmethod
    def validate_semantic_metadata(
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate and sanitize semantic metadata.

        Filters the metadata to ensure it only contains allowed catch-all
        fields.
        """
        # We only keep topics, key_concepts, themes, and content_classification
        # summary and named_entities are extracted separately at the API level
        allowed_keys = {
            "topics",
            "key_concepts",
            "themes",
            "content_classification",
        }

        sanitized = {}
        for key in allowed_keys:
            val = metadata.get(key)
            if val is not None:
                sanitized[key] = val

        return sanitized

"""Shared enums for change tracking (V1 and V2).

Central location to avoid duplicate definitions across
record_history.py and record_history_v2.py.
"""

import enum


class ChangeType(str, enum.Enum):
    """Change type enum for record history."""

    created = "created"
    updated = "updated"
    admin_override = "admin_override"
    system_update = "system_update"


class ChangeSource(str, enum.Enum):
    """Change source enum for record history."""

    user_edit = "user_edit"
    admin_action = "admin_action"
    system_process = "system_process"
    ai_processing = "ai_processing"
    migration = "migration"
    bulk_update = "bulk_update"

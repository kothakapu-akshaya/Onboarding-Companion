"""Backfill core module.

Provides modular infrastructure components for backfill operations.
"""

from typing import Any

# Import only the most commonly used components to avoid circular dependencies
from .cli_utils import create_common_cli_parser, handle_common_cli_setup

# Other components can be imported explicitly when needed
__all__ = ["create_common_cli_parser", "handle_common_cli_setup"]


# Lazy imports for backward compatibility
def __getattr__(name: str) -> Any:
    if name == "BaseBackfiller":
        from .base_backfiller import BaseBackfiller

        return BaseBackfiller
    elif name == "FileManager":
        from .file_manager import FileManager

        return FileManager
    elif name == "ProgressTracker":
        from .progress_tracker import ProgressTracker

        return ProgressTracker
    elif name == "StatisticsManager":
        from .statistics_manager import StatisticsManager

        return StatisticsManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

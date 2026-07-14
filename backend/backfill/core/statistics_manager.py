#!/usr/bin/env python3
"""Statistics management for backfill operations.

Provides thread-safe statistics tracking and reporting.
"""

import threading
import time
from typing import Any

type CounterMap = dict[str, int]
type ErrorSummary = dict[str, int]
type StatsSnapshot = dict[str, Any]


class StatisticsManager:
    """Thread-safe statistics manager for backfill operations.

    Responsibilities:
    - Track processing statistics (successful, failed, skipped)
    - Provide thread-safe updates
    - Calculate performance metrics
    - Store error messages
    """

    def __init__(self) -> None:
        """Initialize the statistics manager."""
        self._counters: CounterMap = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
        }
        self._errors: list[str] = []
        self._custom_stats: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._start_time: float = time.time()

    def update_stat(
        self, stat_key: str, increment: int = 1, error_msg: str | None = None
    ) -> None:
        """Thread-safe statistics updating.

        Args:
            stat_key: Key of the statistic to update
            increment: Amount to increment by (default: 1)
            error_msg: Optional error message to store
        """
        with self._lock:
            if stat_key in self._counters:
                self._counters[stat_key] += increment
            else:
                current_value = self._custom_stats.get(stat_key)
                if isinstance(current_value, int):
                    self._custom_stats[stat_key] = current_value + increment
                else:
                    self._custom_stats[stat_key] = increment

            if error_msg and stat_key == "failed":
                self._errors.append(error_msg)

    def get_stats(self) -> dict[str, Any]:
        """Get a copy of current statistics.

        Returns:
            Dictionary containing current statistics
        """
        with self._lock:
            return self._build_stats_snapshot()

    def get_stat(self, stat_key: str) -> int:
        """Get a specific statistic value.

        Args:
            stat_key: Key of the statistic to retrieve

        Returns:
            Value of the statistic, or 0 if not found
        """
        with self._lock:
            if stat_key in self._counters:
                return self._counters[stat_key]

            custom_value = self._custom_stats.get(stat_key)
            return custom_value if isinstance(custom_value, int) else 0

    def reset_stats(self) -> None:
        """Reset all statistics to initial state."""
        with self._lock:
            self._counters = {
                "total_processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
            }
            self._errors = []
            self._custom_stats = {}
            self._start_time = time.time()

    def calculate_performance_metrics(
        self, total_records: int
    ) -> dict[str, float]:
        """Calculate performance metrics.

        Args:
            total_records: Total number of records processed

        Returns:
            Dictionary containing performance metrics
        """
        current_time = time.time()
        total_time = current_time - self._start_time

        successful = self.get_stat("successful")
        failed = self.get_stat("failed")

        metrics = {
            "total_time_seconds": total_time,
            "average_time_per_record": total_time / total_records
            if total_records > 0
            else 0,
            "records_per_second": total_records / total_time
            if total_time > 0
            else 0,
            "success_rate": (successful / total_records * 100)
            if total_records > 0
            else 0,
            "failure_rate": (failed / total_records * 100)
            if total_records > 0
            else 0,
        }

        return metrics

    def add_custom_stat(self, key: str, value: Any) -> None:
        """Add a custom statistic.

        Args:
            key: Name of the custom statistic
            value: Value to set
        """
        with self._lock:
            self._custom_stats[key] = value

    def increment_custom_stat(self, key: str, increment: int = 1) -> None:
        """Increment a custom statistic.

        Args:
            key: Name of the custom statistic
            increment: Amount to increment by
        """
        with self._lock:
            current_value = self._custom_stats.get(key)
            if isinstance(current_value, int):
                self._custom_stats[key] = current_value + increment
            else:
                self._custom_stats[key] = increment

    def get_error_summary(self) -> ErrorSummary:
        """Get a summary of error types and their counts.

        Returns:
            Dictionary mapping error patterns to their occurrence counts
        """
        error_summary: ErrorSummary = {}

        with self._lock:
            for error in self._errors:
                # Simple pattern matching - could be enhanced
                if "download" in error.lower():
                    error_summary["download_errors"] = (
                        error_summary.get("download_errors", 0) + 1
                    )
                elif (
                    "calculation" in error.lower() or "compute" in error.lower()
                ):
                    error_summary["computation_errors"] = (
                        error_summary.get("computation_errors", 0) + 1
                    )
                elif "database" in error.lower() or "update" in error.lower():
                    error_summary["database_errors"] = (
                        error_summary.get("database_errors", 0) + 1
                    )
                else:
                    error_summary["other_errors"] = (
                        error_summary.get("other_errors", 0) + 1
                    )

        return error_summary

    def get_progress_percentage(self, total_records: int) -> float:
        """Calculate progress percentage.

        Args:
            total_records: Total number of records to process

        Returns:
            Progress percentage (0-100)
        """
        if total_records == 0:
            return 100.0

        return (self.get_stat("total_processed") / total_records) * 100

    def finalize_stats(self, total_records: int) -> dict[str, Any]:
        """Finalize statistics and calculate final metrics.

        Args:
            total_records: Total number of records processed

        Returns:
            Complete statistics including performance metrics
        """
        with self._lock:
            final_stats = self._build_stats_snapshot()
        final_stats.update(self.calculate_performance_metrics(total_records))
        final_stats["error_summary"] = self.get_error_summary()
        return final_stats

    def _build_stats_snapshot(self) -> StatsSnapshot:
        """Build a copy of the current statistics."""
        stats: StatsSnapshot = dict(self._counters)
        stats["errors"] = list(self._errors)
        stats.update(self._custom_stats)
        return stats

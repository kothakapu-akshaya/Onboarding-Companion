#!/usr/bin/env python3
# ruff: noqa: E402
"""Back-fill BCP47 codes on existing LanguageEntry rows.

Run this once after applying the 7dace91d953b migration if any rows were
inserted before the migration or if new rows have been added without a code.

Usage:
    uv run python -m scripts.seed_language_codes
    uv run python -m scripts.seed_language_codes --dry-run

Docker:
    docker compose exec app uv run python -m scripts.seed_language_codes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select

from app.core.language_utils import DEFAULT_LANGUAGE_CODES
from app.db.session import engine
from app.models.language import LanguageEntry


def seed(dry_run: bool = False) -> None:  # noqa: D103
    with Session(engine) as session:
        entries = session.exec(select(LanguageEntry)).all()

        updated = []
        flagged = []

        for entry in entries:
            if entry.code is not None:
                continue
            code = DEFAULT_LANGUAGE_CODES.get(entry.name)
            if code is not None:
                updated.append((entry.name, code))
                if not dry_run:
                    entry.code = code
                    session.add(entry)
            else:
                flagged.append(entry.name)

        if not dry_run:
            session.commit()

    prefix = "[DRY RUN] " if dry_run else ""

    if updated:
        print(f"{prefix}Seeded codes for {len(updated)} language(s):")
        for name, code in sorted(updated):
            print(f"  {name!r:30s} → {code!r}")
    else:
        print(f"{prefix}All rows already have codes.")

    if flagged:
        print(
            f"\n⚠  {len(flagged)} language(s) have no known BCP47 code "
            "— assign via the admin API (POST /api/v1/languages?code=...):"
        )
        for name in sorted(flagged):
            print(f"  {name!r}")
    else:
        print("All LanguageEntry rows now have BCP47 codes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated without writing to the database.",
    )
    args = parser.parse_args()
    seed(dry_run=args.dry_run)

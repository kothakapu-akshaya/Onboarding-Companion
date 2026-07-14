"""Live tests for verifying the load_dotenv removal migration."""

import os
import pathlib
import sys

results = []


def _check(label, passed, detail=""):
    """Record and print a single migration-test result."""
    mark = "PASS" if passed else "FAIL"
    results.append((label, passed))
    print(f"  [{mark}] {label}" + (f": {detail}" if detail else ""))


print("\n=== python-dotenv migration — live tests ===\n")

# T1-T6: no load_dotenv calls remain in source files
files_to_check = [
    ("app/core/config.py", "T1"),
    ("alembic/env.py", "T2"),
    ("setup_postgresql.py", "T3"),
    ("backfill/backfill_version_0.py", "T4"),
    ("app/utils/create_categories.py", "T5"),
]
for fpath, tid in files_to_check:
    src = pathlib.Path(fpath).read_text(encoding="utf-8", errors="ignore")
    has_dotenv = (
        "load_dotenv" in src or "from dotenv" in src or "import dotenv" in src
    )
    _check(
        f"{tid} no dotenv calls in {fpath}",
        not has_dotenv,
        "FOUND dotenv reference" if has_dotenv else "clean",
    )

# T6: python-dotenv not in pyproject.toml direct deps
toml_src = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
in_deps_section = False
found_direct = False
for line in toml_src.splitlines():
    if (
        "dependencies" in line
        and "[project" not in line
        and "optional" not in line
        and "group" not in line
    ):
        in_deps_section = True
    if in_deps_section and line.strip().startswith("]"):
        in_deps_section = False
    if in_deps_section and "python-dotenv" in line:
        found_direct = True
_check(
    "T6 python-dotenv removed from pyproject.toml [project.dependencies]",
    not found_direct,
)

# T7: pre-commit schemathesis hook uses --env-file
precommit_src = pathlib.Path(".pre-commit-config.yaml").read_text(
    encoding="utf-8"
)
hook_line = next(
    (
        line
        for line in precommit_src.splitlines()
        if "schemathesis" in line and "uv run" in line
    ),
    "",
)
_check(
    "T7 pre-commit schemathesis hook uses --env-file",
    "--env-file .env" in hook_line,
    hook_line.strip()[:80],
)

# T8: README seed commands use --env-file
readme_src = pathlib.Path("README.md").read_text(encoding="utf-8")
seed_lines = [
    line
    for line in readme_src.splitlines()
    if "seed_database" in line and "uv run" in line and "docker" not in line
]
all_have_envfile = all("--env-file" in line for line in seed_lines)
_check(
    "T8 README local seed commands use --env-file",
    all_have_envfile,
    f"{len(seed_lines)} commands checked",
)

# T9: docker compose seed commands do NOT have --env-file (Docker handles it)
docker_seed_lines = [
    line
    for line in readme_src.splitlines()
    if "seed_database" in line and "docker compose exec" in line
]
none_have_envfile = not any("--env-file" in line for line in docker_seed_lines)
_check(
    "T9 README docker compose commands do NOT have --env-file",
    none_have_envfile,
    f"{len(docker_seed_lines)} docker commands checked",
)

# T10: app still imports config without error (env vars from os.environ)
os.environ.setdefault(
    "DATABASE_URL", "postgresql://test:test@localhost:5432/test"
)
try:
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    from app.core import config

    _ = config.settings

    _check("T10 app.core.config imports without load_dotenv", True)
except Exception as e:
    _check("T10 app.core.config imports without load_dotenv", False, str(e))

# T11: alembic env.py has no dotenv import
alembic_src = pathlib.Path("alembic/env.py").read_text(encoding="utf-8")
_check("T11 alembic/env.py has no dotenv import", "dotenv" not in alembic_src)

# T12: setup_postgresql.py has no dotenv import
setup_src = pathlib.Path("setup_postgresql.py").read_text(
    encoding="utf-8", errors="ignore"
)
_check(
    "T12 setup_postgresql.py has no dotenv import",
    "dotenv" not in setup_src,
)

# T13: uv.lock still has python-dotenv as a transitive dependency.
lock_src = pathlib.Path("uv.lock").read_text(encoding="utf-8")
_check(
    "T13 python-dotenv still in uv.lock as transitive dep",
    "python-dotenv" in lock_src,
    "present as transitive dep of moviepy + pydantic-settings",
)

passed = sum(1 for _, p in results if p)
total = len(results)
print(f"\n=== {passed}/{total} PASS ===")
if passed < total:
    print("FAILED:", [n for n, p in results if not p])
    sys.exit(1)
else:
    print("ALL PASS")

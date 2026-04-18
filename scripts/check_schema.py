#!/usr/bin/env python3
"""
Schema-diff check — verify the API contract hasn't changed unexpectedly.

Run from the repo root before merging to master:

    python scripts/check_schema.py

Runs drf-spectacular to generate the current OpenAPI schema, diffs it against
the committed baseline at PartsTracker/schema.yaml, and exits non-zero if the
two differ.

When the diff is intentional (new endpoint, new field, changed response shape
you meant to change):

    cd PartsTracker && python manage.py spectacular --file schema.yaml
    git add PartsTracker/schema.yaml
    # then commit — and regenerate frontend types:
    cd ambac-tracker-ui && bun run generate-api

When the diff is unexpected: you introduced an API shape change you didn't
intend. Review the diff, reconcile.

Exit codes:
    0 — schema matches baseline
    1 — schema differs (printed as unified diff)
    2 — script error (baseline missing, schema generation failed)
"""
import difflib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = REPO_ROOT / "PartsTracker" / "schema.yaml"
MANAGE_PY_DIR = REPO_ROOT / "PartsTracker"


def generate_current_schema(out_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "manage.py", "spectacular", "--file", str(out_path)],
        cwd=MANAGE_PY_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: schema generation failed", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(2)


def main() -> int:
    if not BASELINE_PATH.exists():
        print(f"ERROR: baseline schema not found at {BASELINE_PATH}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmpdir:
        current_path = Path(tmpdir) / "current_schema.yaml"
        generate_current_schema(current_path)

        baseline_lines = BASELINE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
        current_lines = current_path.read_text(encoding="utf-8").splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        baseline_lines,
        current_lines,
        fromfile=str(BASELINE_PATH.relative_to(REPO_ROOT)),
        tofile="(current generated schema)",
    ))

    if not diff:
        print("OK: schema matches baseline")
        return 0

    print("DIFF: schema has changed vs baseline\n")
    sys.stdout.writelines(diff)
    print("\nIf the change is intentional, update the baseline:")
    print("  cd PartsTracker && python manage.py spectacular --file schema.yaml")
    print("  git add PartsTracker/schema.yaml")
    print("  # then regenerate frontend types:")
    print("  cd ambac-tracker-ui && bun run generate-api")
    return 1


if __name__ == "__main__":
    sys.exit(main())

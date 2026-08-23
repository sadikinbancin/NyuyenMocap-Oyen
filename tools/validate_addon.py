"""Static validation for NyuyenMocap/Oyen."""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures = []
    conflict_start = "<" * 7
    conflict_end = ">" * 7
    for path in ROOT.rglob("*.py"):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if conflict_start in text or conflict_end in text:
            failures.append(f"merge-conflict marker: {path.relative_to(ROOT)}")
        try:
            ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            failures.append(f"syntax error: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")

    for path in (ROOT / "src" / "cgt_transfer" / "data").glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"invalid JSON: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")

    if failures:
        print("VALIDATION FAILED")
        print("\n".join(failures))
        return 1
    print("Validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

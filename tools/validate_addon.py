"""Static validation for NyuyenMocap/Oyen.

This intentionally does not import Blender. It catches the installation class of
failures that caused the original fork to break: unresolved merge markers,
Python syntax errors, and invalid transfer JSON.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []

    for path in ROOT.rglob("*.py"):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "<<<<<<< HEAD" in text or ">>>>>>> " in text:
            failures.append(f"merge-conflict marker: {path.relative_to(ROOT)}")
        try:
            ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            failures.append(f"syntax error: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")

    data_dir = ROOT / "src" / "cgt_transfer" / "data"
    for path in data_dir.glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"invalid JSON: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")

    if failures:
        print("VALIDATION FAILED")
        print("\n".join(failures))
        return 1

    print("Validation OK: Python syntax and transfer JSON are valid; no merge-conflict markers remain in checked Python files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

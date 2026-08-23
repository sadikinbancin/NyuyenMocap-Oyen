"""Static validation for the safe adapter layer."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "src" / "nyuyen_adapter.py"
ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
text = path.read_text(encoding="utf-8")
required = (
    "discover_drivers",
    "hide_driver_viewport",
    "build_preview_skeleton",
    "get_transfer_source_collection",
    "prepare_for_transfer",
)
missing = [name for name in required if f"def {name}" not in text]
if missing:
    raise SystemExit(f"Missing adapter API: {missing}")
print("Nyuyen safe adapter validation: OK")

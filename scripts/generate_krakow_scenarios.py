"""Generuje 3 warianty mapy Starego Miasta Krakowa do scenarios/.

Uruchomienie z root projektu:
    python scripts/generate_krakow_scenarios.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.themed_maps import generate_krakow_old_town  # noqa: E402
from src.ui_io import save_map, validate_map  # noqa: E402


SCENARIOS = [
    ("easy",   "krakow_easy.json"),
    ("normal", "krakow.json"),
    ("hard",   "krakow_hard.json"),
]


def main() -> int:
    out_dir = ROOT / "scenarios"
    out_dir.mkdir(exist_ok=True)

    any_errors = False
    for variant, filename in SCENARIOS:
        data = generate_krakow_old_town(variant=variant, seed=7)
        path = out_dir / filename

        issues = validate_map(data)
        errors = [i for i in issues if i.level == "error"]
        warnings = [i for i in issues if i.level == "warning"]

        if errors:
            any_errors = True
            print(f"[ERROR] {filename}: {len(errors)} validation errors:")
            for e in errors:
                print(f"  - {e.message}")
            continue

        save_map(path, data)
        print(f"[OK] Wrote {path.relative_to(ROOT)} ({len(data['attractions'])} atrakcji, budget={data['budget']})")
        for w in warnings:
            print(f"  warning: {w.message}")

    return 1 if any_errors else 0


if __name__ == "__main__":
    sys.exit(main())

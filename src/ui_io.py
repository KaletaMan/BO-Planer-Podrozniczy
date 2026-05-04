from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set


SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


@dataclass
class ValidationIssue:
    level: str  # "error" | "warning"
    message: str


def list_maps() -> List[Path]:
    SCENARIOS_DIR.mkdir(exist_ok=True)
    return sorted(SCENARIOS_DIR.glob("*.json"))


def load_map(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_map(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_map(data: Dict[str, Any]) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    width = data.get("width")
    height = data.get("height")
    weights = data.get("weights")
    attractions = data.get("attractions")
    start = data.get("start")
    end = data.get("end")
    time_limit = data.get("time_limit")
    budget = data.get("budget")

    if not isinstance(width, int) or width <= 0:
        issues.append(ValidationIssue("error", f"'width' musi być dodatnim int-em, jest: {width}."))
    if not isinstance(height, int) or height <= 0:
        issues.append(ValidationIssue("error", f"'height' musi być dodatnim int-em, jest: {height}."))
    if not isinstance(time_limit, (int, float)) or time_limit <= 0:
        issues.append(ValidationIssue("error", f"'time_limit' musi być > 0 (minuty), jest: {time_limit}."))
    if not isinstance(budget, (int, float)) or budget < 0:
        issues.append(ValidationIssue("error", f"'budget' musi być >= 0 (budżet pieniężny), jest: {budget}."))

    w = width if isinstance(width, int) and width > 0 else None
    h = height if isinstance(height, int) and height > 0 else None

    # Validate weights matrix
    if not isinstance(weights, list):
        issues.append(ValidationIssue("error", "'weights' musi być listą list."))
    elif w and h:
        if len(weights) != h:
            issues.append(ValidationIssue("error", f"'weights' ma {len(weights)} wierszy, oczekiwano {h}."))
        else:
            for y, row in enumerate(weights):
                if not isinstance(row, list) or len(row) != w:
                    issues.append(ValidationIssue("error", f"Wiersz {y} 'weights' ma złą długość (oczekiwano {w})."))
                    break
                for x, val in enumerate(row):
                    if not isinstance(val, (int, float)) or val < 0:
                        issues.append(ValidationIssue("error", f"Waga [{y}][{x}] = {val} musi być >= 0."))
                        break

    # Validate start/end
    def _check_point(pt: Any, label: str) -> None:
        if pt is None:
            return
        if not isinstance(pt, dict):
            issues.append(ValidationIssue("error", f"'{label}' musi być słownikiem {{x, y}}."))
            return
        px, py = pt.get("x"), pt.get("y")
        if w and h:
            if not (isinstance(px, int) and isinstance(py, int) and 0 <= px < w and 0 <= py < h):
                issues.append(ValidationIssue("error", f"'{label}' ({px}, {py}) poza mapą {w}x{h}."))

    _check_point(start, "start")
    _check_point(end, "end")

    if (
        isinstance(start, dict) and isinstance(end, dict)
        and start.get("x") == end.get("x") and start.get("y") == end.get("y")
    ):
        issues.append(ValidationIssue("warning", "start i end są w tej samej komórce."))

    # Validate attractions
    if attractions is None or (isinstance(attractions, list) and len(attractions) == 0):
        issues.append(ValidationIssue("warning", "Brak atrakcji — trasa nie zbierze punktów."))
    elif not isinstance(attractions, list):
        issues.append(ValidationIssue("error", "'attractions' musi być listą."))
    else:
        seen_ids: Set[str] = set()
        for i, a in enumerate(attractions):
            if not isinstance(a, dict):
                issues.append(ValidationIssue("error", f"Atrakcja [{i}] nie jest słownikiem."))
                continue
            aid = str(a.get("id", f"a{i}"))
            if aid in seen_ids:
                issues.append(ValidationIssue("error", f"Duplikat id atrakcji: '{aid}'."))
            seen_ids.add(aid)
            ax, ay = a.get("x"), a.get("y")
            if w and h and not (isinstance(ax, int) and isinstance(ay, int) and 0 <= ax < w and 0 <= ay < h):
                issues.append(ValidationIssue("error", f"Atrakcja '{aid}' ({ax}, {ay}) poza mapą {w}x{h}."))
            val = a.get("value")
            if not isinstance(val, (int, float)) or val < 0:
                issues.append(ValidationIssue("warning", f"Atrakcja '{aid}': wartość {val} powinna być >= 0."))

            if "cost" not in a:
                issues.append(ValidationIssue("error", f"Atrakcja '{aid}': brakuje pola 'cost' (cena)."))
            else:
                cost = a.get("cost")
                if not isinstance(cost, (int, float)) or cost < 0:
                    issues.append(ValidationIssue("error", f"Atrakcja '{aid}': cena {cost} musi być >= 0."))

        if w and h and len(attractions) > 0:
            density = len(attractions) / (w * h)
            if density > 0.3:
                issues.append(ValidationIssue("warning", f"Gęstość atrakcji {density:.0%} > 30% — mapa jest bardzo gęsta."))

    # Time limit feasibility hint (rough lower bound for start->end)
    if w and h and isinstance(time_limit, (int, float)) and isinstance(start, dict) and isinstance(end, dict):
        try:
            from src.map_generator import _chebyshev
            dist = _chebyshev(start["x"], start["y"], end["x"], end["y"])
            if isinstance(weights, list) and len(weights) == h:
                flat = [v for row in weights for v in row if isinstance(v, (int, float))]
                if flat:
                    min_w = min(flat)
                    rough_min = dist * min_w
                    if rough_min > time_limit:
                        issues.append(ValidationIssue("warning", f"Szacowany min. czas ruchu ({rough_min}) > limit czasu ({time_limit}) — instancja może być infeasible."))
        except Exception:
            pass

    return issues

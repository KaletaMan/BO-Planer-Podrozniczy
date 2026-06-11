"""Eksport danych do wykresow pgfplots (LaTeX).

Czyta zapisane wyniki eksperymentu (``results/experiment_krakow50_abc_bee.json``)
i generuje pliki ``.dat`` czytane przez ``\\addplot table`` w dokumentacji:

* ``conv_abc.dat``   - best_value po iteracjach, kolumna na kazdy seed (ABC),
* ``conv_bee.dat``   - jak wyzej dla Bee,
* ``conv_band.dat``  - srednia oraz min/max po iteracjach dla obu algorytmow,
* ``final_values.dat`` - koncowe wartosci rozwiazan (kolumny: abc, bee).

Mozna uruchomic samodzielnie::

    python experiments/export_pgfplots.py

albo jest wolany automatycznie na koncu ``run_experiments.py``.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS = REPO_ROOT / "results" / "experiment_krakow50_abc_bee.json"
DEFAULT_OUT_DIR = REPO_ROOT / "dokumentacja" / "grafiki"


def _series(run: dict) -> list[float]:
    return [h.get("best_value", 0) for h in run["history"]]


def export_pgfplots_data(results_path: Path = DEFAULT_RESULTS, out_dir: Path = DEFAULT_OUT_DIR) -> list[Path]:
    """Generuje pliki .dat dla pgfplots. Zwraca liste zapisanych sciezek."""
    data = json.loads(Path(results_path).read_text(encoding="utf-8"))
    runs = data["runs"]

    by_algo: dict[str, list[dict]] = {}
    for r in runs:
        by_algo.setdefault(r["algo"], []).append(r)
    for algo_runs in by_algo.values():
        algo_runs.sort(key=lambda r: r["seed"])

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    # Po jednej kolumnie na seed (krzywe zbieznosci pojedynczych powtorzen).
    for algo, fname in (("ABC", "conv_abc.dat"), ("Bee", "conv_bee.dat")):
        algo_runs = by_algo[algo]
        series = [_series(r) for r in algo_runs]
        n = min(len(s) for s in series)
        header = "iter " + " ".join(f"s{r['seed']}" for r in algo_runs)
        lines = [header]
        for i in range(n):
            lines.append(" ".join([str(i + 1)] + [f"{s[i]:g}" for s in series]))
        path = out_dir / fname
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)

    # Srednia + pasmo min-max dla wykresu porownawczego.
    abc_series = [_series(r) for r in by_algo["ABC"]]
    bee_series = [_series(r) for r in by_algo["Bee"]]
    n = min(min(len(s) for s in abc_series), min(len(s) for s in bee_series))
    lines = ["iter abc_mean abc_min abc_max bee_mean bee_min bee_max"]
    for i in range(n):
        av = [s[i] for s in abc_series]
        bv = [s[i] for s in bee_series]
        lines.append(
            f"{i + 1} "
            f"{statistics.fmean(av):.2f} {min(av):g} {max(av):g} "
            f"{statistics.fmean(bv):.2f} {min(bv):g} {max(bv):g}"
        )
    path = out_dir / "conv_band.dat"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written.append(path)

    # Koncowe wartosci do boxplota (wiersz = para sparowana po seedzie).
    lines = ["abc bee"]
    for ra, rb in zip(by_algo["ABC"], by_algo["Bee"]):
        lines.append(
            f"{ra['evaluation']['value_collected']:g} {rb['evaluation']['value_collected']:g}"
        )
    path = out_dir / "final_values.dat"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written.append(path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Eksport danych .dat dla pgfplots")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    for p in export_pgfplots_data(args.results, args.out_dir):
        print(f"  - {p}")


if __name__ == "__main__":
    main()

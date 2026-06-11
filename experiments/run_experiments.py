"""Eksperyment porownawczy ABC vs Bee Algorithm.

Uruchamia oba algorytmy rojowe wielokrotnie (rozne seedy) na tej samej instancji
problemu, zbiera metryki, liczy statystyki opisowe oraz test Wilcoxona, zapisuje
wyniki do katalogu ``results/`` (format zgodny z aplikacja) i generuje wykresy
zbieznosci oraz zmiennosci do ``dokumentacja/grafiki/``.

Uruchomienie (z katalogu repozytorium)::

    python experiments/run_experiments.py

Domyslnie: mapa krakow_50x50, 5 powtorzen po 500 iteracji dla kazdego algorytmu.
Parametry mozna zmienic argumentami CLI (--iterations, --seeds, --population-size).
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend bez okna, do zapisu PNG
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.export_pgfplots import export_pgfplots_data  # noqa: E402
from src.abc_ui_adapter import solve_abc_ui  # noqa: E402
from src.bee_ui_adapter import solve_bee_ui  # noqa: E402

DEFAULT_MAP = REPO_ROOT / "krakow_50x50_balanced_fixed_types.json"
DEFAULT_RESULTS_DIR = REPO_ROOT / "results"
DEFAULT_FIGURES_DIR = REPO_ROOT / "dokumentacja" / "grafiki"

PREFIX = "experiment_krakow50"


# ---------------------------------------------------------------------------
# Uruchamianie pojedynczych algorytmow
# ---------------------------------------------------------------------------

def _best_iteration(history: list[dict]) -> int:
    """Iteracja, w ktorej osiagnieto koncowa najlepsza wartosc.

    ``best_value`` w historii jest niemalejace (best-so-far), wiec szukamy
    pierwszej iteracji, w ktorej osiagnieto wartosc maksymalna.
    """
    if not history:
        return 0
    final = max(h.get("best_value", 0) for h in history)
    for h in history:
        if h.get("best_value", 0) >= final:
            return int(h.get("iteration", 0))
    return int(history[-1].get("iteration", 0))


def _run_one(algo: str, map_data: dict, *, iterations: int, population_size: int, seed: int) -> dict:
    if algo == "ABC":
        out = solve_abc_ui(
            map_data,
            population_size=population_size,
            iterations=iterations,
            seed=seed,
        )
    elif algo == "Bee":
        out = solve_bee_ui(
            map_data,
            population_size=population_size,
            iterations=iterations,
            seed=seed,
        )
    else:
        raise ValueError(f"Nieznany algorytm: {algo}")

    best = out["best"]
    history = out["history"]

    evaluation = {
        "value_collected": best.get("total_value", 0),
        "total_time": best.get("total_time", 0.0),
        "movement_time": best.get("movement_time", 0.0),
        "attraction_cost": best.get("attraction_cost", 0),
        "visited_count": len(best.get("visited_attractions", [])),
        "path_length": len(out["path"]),
        "feasible": bool(best.get("feasible", False)),
    }

    return {
        "algo": algo,
        "seed": seed,
        "iterations": iterations,
        "population_size": population_size,
        "path": out["path"],
        "history": history,
        "best_iteration": _best_iteration(history),
        "objective_calls_total": out.get("objective_calls_total", 0),
        "objective_calls_to_best": out.get("objective_calls_to_best", 0),
        "evaluation": evaluation,
    }


# ---------------------------------------------------------------------------
# Statystyki
# ---------------------------------------------------------------------------

def _describe(values: list[float]) -> dict:
    vals = [float(v) for v in values]
    return {
        "n": len(vals),
        "mean": statistics.fmean(vals) if vals else 0.0,
        "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals) if vals else 0.0,
        "max": max(vals) if vals else 0.0,
        "median": statistics.median(vals) if vals else 0.0,
    }


def _wilcoxon(abc_vals: list[float], bee_vals: list[float]) -> dict:
    """Test Wilcoxona dla par (ABC_i, Bee_i). Bezpieczny na przypadki brzegowe."""
    try:
        from scipy.stats import wilcoxon
    except ImportError:
        return {"available": False, "reason": "scipy nie jest zainstalowane"}

    diffs = [a - b for a, b in zip(abc_vals, bee_vals)]
    if all(d == 0 for d in diffs):
        return {
            "available": True,
            "statistic": 0.0,
            "p_value": 1.0,
            "n_pairs": len(diffs),
            "note": "Wszystkie roznice rowne 0 - brak roznic miedzy algorytmami.",
        }
    try:
        stat, p = wilcoxon(abc_vals, bee_vals)
        return {
            "available": True,
            "statistic": float(stat),
            "p_value": float(p),
            "n_pairs": len(diffs),
            "alpha": 0.05,
            "significant": bool(p < 0.05),
            "note": "Mala proba (n=5) - wynik traktowac orientacyjnie.",
        }
    except ValueError as exc:
        return {"available": True, "error": str(exc), "n_pairs": len(diffs)}


def _build_summary(runs: list[dict]) -> dict:
    summary = {"per_algo": {}, "metrics": ["value_collected", "objective_calls_to_best", "best_iteration"]}

    by_algo: dict[str, list[dict]] = {}
    for r in runs:
        by_algo.setdefault(r["algo"], []).append(r)

    for algo, algo_runs in by_algo.items():
        algo_runs = sorted(algo_runs, key=lambda r: r["seed"])
        summary["per_algo"][algo] = {
            "seeds": [r["seed"] for r in algo_runs],
            "value_collected": _describe([r["evaluation"]["value_collected"] for r in algo_runs]),
            "movement_time": _describe([r["evaluation"]["movement_time"] for r in algo_runs]),
            "attraction_cost": _describe([r["evaluation"]["attraction_cost"] for r in algo_runs]),
            "visited_count": _describe([r["evaluation"]["visited_count"] for r in algo_runs]),
            "objective_calls_to_best": _describe([r["objective_calls_to_best"] for r in algo_runs]),
            "best_iteration": _describe([r["best_iteration"] for r in algo_runs]),
            "feasible_all": all(r["evaluation"]["feasible"] for r in algo_runs),
        }

    if "ABC" in by_algo and "Bee" in by_algo:
        abc_sorted = sorted(by_algo["ABC"], key=lambda r: r["seed"])
        bee_sorted = sorted(by_algo["Bee"], key=lambda r: r["seed"])
        abc_vals = [r["evaluation"]["value_collected"] for r in abc_sorted]
        bee_vals = [r["evaluation"]["value_collected"] for r in bee_sorted]
        summary["wilcoxon_value_collected"] = _wilcoxon(abc_vals, bee_vals)
        summary["paired_values"] = {
            "seeds": [r["seed"] for r in abc_sorted],
            "ABC": abc_vals,
            "Bee": bee_vals,
        }

    return summary


# ---------------------------------------------------------------------------
# Wykresy
# ---------------------------------------------------------------------------

_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]


def _history_xy(history: list[dict]) -> tuple[list[int], list[float]]:
    xs = [h.get("iteration", i + 1) for i, h in enumerate(history)]
    ys = [h.get("best_value", 0) for h in history]
    return xs, ys


def _plot_convergence_single(runs: list[dict], algo: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, r in enumerate(sorted(runs, key=lambda r: r["seed"])):
        xs, ys = _history_xy(r["history"])
        ax.plot(xs, ys, color=_COLORS[i % len(_COLORS)], linewidth=1.6, label=f"seed={r['seed']}")
    ax.set_xlabel("Iteracja")
    ax.set_ylabel("Najlepsza wartosc (best_value)")
    ax.set_title(f"Zbieznosc {algo} - 5 powtorzen")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def _mean_band(runs: list[dict]) -> tuple[list[int], list[float], list[float], list[float]]:
    """Srednia oraz min/max best_value po iteracjach (po wszystkich powtorzeniach)."""
    series = [_history_xy(r["history"])[1] for r in runs]
    n = min(len(s) for s in series)
    xs = list(range(1, n + 1))
    mean = [statistics.fmean(s[i] for s in series) for i in range(n)]
    lo = [min(s[i] for s in series) for i in range(n)]
    hi = [max(s[i] for s in series) for i in range(n)]
    return xs, mean, lo, hi


def _plot_convergence_compare(abc_runs: list[dict], bee_runs: list[dict], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for runs, name, color in ((abc_runs, "ABC", "#1f77b4"), (bee_runs, "Bee", "#ff7f0e")):
        xs, mean, lo, hi = _mean_band(runs)
        ax.plot(xs, mean, color=color, linewidth=2.0, label=f"{name} (srednia)")
        ax.fill_between(xs, lo, hi, color=color, alpha=0.18, label=f"{name} (min-max)")
    ax.set_xlabel("Iteracja")
    ax.set_ylabel("Najlepsza wartosc (best_value)")
    ax.set_title("Porownanie zbieznosci ABC vs Bee (srednia z 5 powtorzen)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def _plot_final_box(abc_runs: list[dict], bee_runs: list[dict], out_path: Path) -> None:
    abc_vals = [r["evaluation"]["value_collected"] for r in abc_runs]
    bee_vals = [r["evaluation"]["value_collected"] for r in bee_runs]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    bp = ax.boxplot([abc_vals, bee_vals], labels=["ABC", "Bee"], patch_artist=True, showmeans=True)
    for patch, color in zip(bp["boxes"], ["#1f77b4", "#ff7f0e"]):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    # punkty surowe
    for x, vals in ((1, abc_vals), (2, bee_vals)):
        ax.scatter([x] * len(vals), vals, color="black", zorder=3, s=18)
    ax.set_ylabel("Koncowa wartosc rozwiazania")
    ax.set_title("Zmiennosc wynikow koncowych (5 powtorzen)")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Zapis wynikow
# ---------------------------------------------------------------------------

def _save_results_json(map_data: dict, runs: list[dict], path: Path) -> None:
    """Zapis w formacie zgodnym z aplikacja (app.py): map_name, map_data, runs."""
    slim_runs = []
    for r in runs:
        slim_runs.append(
            {
                "algo": r["algo"],
                "seed": r["seed"],
                "iterations": r["iterations"],
                "population_size": r["population_size"],
                "path": r["path"],
                "history": r["history"],
                "best_iteration": r["best_iteration"],
                "objective_calls_total": r["objective_calls_total"],
                "objective_calls_to_best": r["objective_calls_to_best"],
                "evaluation": r["evaluation"],
            }
        )
    payload = {
        "map_name": map_data.get("name", "Mapa"),
        "map_data": map_data,
        "runs": slim_runs,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _save_runs_csv(runs: list[dict], path: Path) -> None:
    fields = [
        "algo", "seed", "iterations", "population_size",
        "value_collected", "movement_time", "attraction_cost", "visited_count",
        "path_length", "feasible", "best_iteration",
        "objective_calls_total", "objective_calls_to_best",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in runs:
            ev = r["evaluation"]
            w.writerow(
                {
                    "algo": r["algo"],
                    "seed": r["seed"],
                    "iterations": r["iterations"],
                    "population_size": r["population_size"],
                    "value_collected": ev["value_collected"],
                    "movement_time": round(ev["movement_time"], 3),
                    "attraction_cost": ev["attraction_cost"],
                    "visited_count": ev["visited_count"],
                    "path_length": ev["path_length"],
                    "feasible": ev["feasible"],
                    "best_iteration": r["best_iteration"],
                    "objective_calls_total": r["objective_calls_total"],
                    "objective_calls_to_best": r["objective_calls_to_best"],
                }
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Eksperyment ABC vs Bee")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--population-size", type=int, default=30)
    parser.add_argument("--out-results", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--out-figures", type=Path, default=DEFAULT_FIGURES_DIR)
    args = parser.parse_args()

    args.out_results.mkdir(parents=True, exist_ok=True)
    args.out_figures.mkdir(parents=True, exist_ok=True)

    map_data = json.loads(args.map.read_text(encoding="utf-8"))
    print(
        f"Mapa: {map_data.get('name')} ({map_data.get('width')}x{map_data.get('height')}), "
        f"atrakcje={len(map_data.get('attractions', []))}, "
        f"time_limit={map_data.get('time_limit')}, budget={map_data.get('budget')}"
    )
    print(
        f"Schemat: {len(args.seeds)} powtorzen x {args.iterations} iteracji, "
        f"populacja={args.population_size}, seedy={args.seeds}\n"
    )

    runs: list[dict] = []
    for algo in ("ABC", "Bee"):
        for seed in args.seeds:
            print(f"[{algo} seed={seed}] start ...", flush=True)
            r = _run_one(
                algo,
                map_data,
                iterations=args.iterations,
                population_size=args.population_size,
                seed=seed,
            )
            ev = r["evaluation"]
            print(
                f"[{algo} seed={seed}] done: value={ev['value_collected']}, "
                f"atrakcje={ev['visited_count']}, czas={ev['movement_time']:.1f}, "
                f"koszt={ev['attraction_cost']}, feasible={ev['feasible']}, "
                f"best_iter={r['best_iteration']}, calls_to_best={r['objective_calls_to_best']}",
                flush=True,
            )
            runs.append(r)

    abc_runs = sorted([r for r in runs if r["algo"] == "ABC"], key=lambda r: r["seed"])
    bee_runs = sorted([r for r in runs if r["algo"] == "Bee"], key=lambda r: r["seed"])

    # --- Statystyki ---
    summary = _build_summary(runs)
    summary["map"] = {
        "name": map_data.get("name"),
        "width": map_data.get("width"),
        "height": map_data.get("height"),
        "attractions": len(map_data.get("attractions", [])),
        "time_limit": map_data.get("time_limit"),
        "budget": map_data.get("budget"),
    }
    summary["config"] = {
        "iterations": args.iterations,
        "seeds": args.seeds,
        "population_size": args.population_size,
    }

    # --- Zapis wynikow ---
    results_json = args.out_results / f"{PREFIX}_abc_bee.json"
    summary_json = args.out_results / f"{PREFIX}_summary.json"
    runs_csv = args.out_results / f"{PREFIX}_runs.csv"
    _save_results_json(map_data, runs, results_json)
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _save_runs_csv(runs, runs_csv)

    # --- Wykresy (poglądowe PNG) ---
    _plot_convergence_single(abc_runs, "ABC", args.out_figures / "conv_abc.png")
    _plot_convergence_single(bee_runs, "Bee", args.out_figures / "conv_bee.png")
    _plot_convergence_compare(abc_runs, bee_runs, args.out_figures / "conv_compare.png")
    _plot_final_box(abc_runs, bee_runs, args.out_figures / "final_values_box.png")

    # --- Dane .dat do wykresow pgfplots w dokumentacji ---
    dat_files = export_pgfplots_data(results_json, args.out_figures)

    # --- Podsumowanie na konsole ---
    print("\n=== STATYSTYKI (value_collected) ===")
    for algo in ("ABC", "Bee"):
        s = summary["per_algo"][algo]["value_collected"]
        print(
            f"{algo}: mean={s['mean']:.1f} std={s['std']:.1f} "
            f"min={s['min']:.0f} max={s['max']:.0f} median={s['median']:.1f}"
        )
    w = summary.get("wilcoxon_value_collected", {})
    if w.get("p_value") is not None and "p_value" in w:
        print(f"\nWilcoxon ABC vs Bee: statistic={w.get('statistic')}, p-value={w.get('p_value'):.4f}")
    else:
        print(f"\nWilcoxon: {w}")

    print("\nZapisano:")
    for p in (results_json, summary_json, runs_csv):
        print(f"  - {p}")
    for name in ("conv_abc.png", "conv_bee.png", "conv_compare.png", "final_values_box.png"):
        print(f"  - {args.out_figures / name}")
    for p in dat_files:
        print(f"  - {p}")


if __name__ == "__main__":
    main()

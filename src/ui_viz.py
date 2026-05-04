from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np


_PATH_COLORS = ["#2980b9", "#e74c3c", "#27ae60", "#8e44ad", "#e67e22"]

# Distinct colors for attraction types (colorblind-friendly enough for 2–5 types)
_TYPE_COLORS = ["#f1c40f", "#1abc9c", "#e74c3c", "#9b59b6", "#e67e22"]
_TYPE_MARKERS = ["*", "o", "^", "s", "D"]


def plot_map(map_data: dict, title: str = "Mapa", *, show_attraction_labels: bool = True) -> plt.Figure:
    weights = np.array(map_data["weights"], dtype=float)
    h, w = weights.shape
    # Large figures get expensive fast (especially when re-rendered each iteration).
    fig_w = min(10.0, max(5.0, w * 0.35))
    fig_h = min(8.0, max(4.0, h * 0.35))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    im = ax.imshow(weights, cmap="YlOrRd", origin="lower", aspect="equal",
                   vmin=weights.min(), vmax=weights.max())
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04, label="Waga (koszt)")

    _draw_attractions(ax, map_data, show_labels=show_attraction_labels)
    _draw_start_end(ax, map_data)

    ax.set_title(title, fontsize=11)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.tight_layout()
    return fig


def plot_path_on_map(
    map_data: dict,
    path: List[Tuple[int, int]],
    title: str = "Ścieżka",
    color: str = "#2980b9",
) -> plt.Figure:
    fig = plot_map(map_data, title=title)
    ax = fig.axes[0]
    _draw_path(ax, path, color=color, label="Ścieżka", zorder=4)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    return fig


def plot_paths_comparison(
    map_data: dict,
    paths: Dict[str, List[Tuple[int, int]]],
    title: str = "Porównanie ścieżek",
    *,
    show_attraction_labels: bool = True,
) -> plt.Figure:
    fig = plot_map(map_data, title=title, show_attraction_labels=show_attraction_labels)
    ax = fig.axes[0]
    for i, (name, path) in enumerate(paths.items()):
        color = _PATH_COLORS[i % len(_PATH_COLORS)]
        _draw_path(ax, path, color=color, label=name, zorder=4 + i)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    return fig


def plot_convergence(histories: Dict[str, List[float]], title: str = "Konwergencja") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, (name, hist) in enumerate(histories.items()):
        color = _PATH_COLORS[i % len(_PATH_COLORS)]
        ax.plot(hist, color=color, linewidth=2, label=name)
    ax.set_xlabel("Iteracja / pokolenie")
    ax.set_ylabel("Fitness (wartość)")
    ax.set_title(title)
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig


# ── Internal helpers ──────────────────────────────────────────────────────────

def _draw_attractions(ax: plt.Axes, map_data: dict, *, show_labels: bool = True) -> None:
    defined_types = map_data.get("attraction_types") or []
    type_index: dict[str, int] = {t: i for i, t in enumerate(defined_types)}
    legend_handles: dict[str, mpatches.Patch] = {}

    attractions = map_data.get("attractions", [])
    # Labels are the slowest part on dense maps.
    if len(attractions) > 60:
        show_labels = False

    for a in attractions:
        x, y = a["x"], a["y"]
        atype = a.get("type", "")
        idx = type_index.get(atype, len(defined_types))  # unknown types get last slot
        color = _TYPE_COLORS[idx % len(_TYPE_COLORS)]
        marker = _TYPE_MARKERS[idx % len(_TYPE_MARKERS)]
        size = 280 if marker == "*" else 130
        ax.scatter(x, y, marker=marker, s=size, c=color, edgecolors="black",
                   linewidths=0.7, zorder=3)

        if show_labels:
            label = f"{a['id']}\nV:{a.get('value', 0)}"
            if "cost" in a and a.get("cost") is not None:
                label += f"\nC:{a.get('cost', 0)}"

            ax.text(x + 0.35, y + 0.35, label, fontsize=6,
                    ha="left", va="bottom", color="black",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.6))
        label = atype if atype else "brak typu"
        if label not in legend_handles:
            legend_handles[label] = mpatches.Patch(
                facecolor=color, edgecolor="black", label=label, linewidth=0.7
            )

    if legend_handles:
        handles = list(legend_handles.values())
        ax.legend(handles=handles, title="Typy atrakcji", fontsize=7,
                  title_fontsize=7, loc="upper right")


def _draw_start_end(ax: plt.Axes, map_data: dict) -> None:
    s = map_data.get("start")
    e = map_data.get("end")
    if s:
        ax.scatter(s["x"], s["y"], marker="D", s=120, c="#27ae60", edgecolors="white",
                   linewidths=1.2, zorder=5, label="Start")
        ax.text(s["x"], s["y"] - 0.6, "S", ha="center", va="top", fontsize=7,
                color="#27ae60", fontweight="bold")
    if e:
        ax.scatter(e["x"], e["y"], marker="D", s=120, c="#e74c3c", edgecolors="white",
                   linewidths=1.2, zorder=5, label="End")
        ax.text(e["x"], e["y"] - 0.6, "E", ha="center", va="top", fontsize=7,
                color="#e74c3c", fontweight="bold")


def _draw_path(
    ax: plt.Axes,
    path: List[Tuple[int, int]],
    color: str,
    label: str,
    zorder: int = 4,
) -> None:
    if len(path) < 2:
        return
    xs = [p[0] for p in path]
    ys = [p[1] for p in path]
    ax.plot(xs, ys, color=color, linewidth=2.5, alpha=0.85, zorder=zorder, label=label)
    ax.plot(xs[0], ys[0], "o", color=color, markersize=6, zorder=zorder + 1)
    ax.plot(xs[-1], ys[-1], "s", color=color, markersize=6, zorder=zorder + 1)

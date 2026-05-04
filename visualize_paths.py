import json
import matplotlib.pyplot as plt


def load_map_json(filename="map.json"):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def load_population_json(filename="initial_population.json"):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def draw_paths(
    map_file="map.json",
    population_file="initial_population.json",
    selected_ids=None,
    start=None,
    end=None,
):
    map_data = load_map_json(map_file)
    population = load_population_json(population_file)

    move_time = map_data["move_time"]
    attractions = map_data["attractions"]

    rows = len(move_time)
    cols = len(move_time[0])

    if start is None:
        start = (5, 5)
    if end is None:
        end = (rows - 10, cols - 3)

    fig, ax = plt.subplots(figsize=(10, 10))

    # BIAŁE TŁO (bez wag)
    ax.set_facecolor("white")

    # siatka (opcjonalnie, wygląda bardzo dobrze)
    for x in range(cols + 1):
        ax.axvline(x - 0.5, color="lightgray", linewidth=0.5)
    for y in range(rows + 1):
        ax.axhline(y - 0.5, color="lightgray", linewidth=0.5)

    # atrakcje jako punkty
    if attractions:
        attr_x = [a[1] for a in attractions]
        attr_y = [a[0] for a in attractions]
        ax.scatter(attr_x, attr_y, c="black", s=10, label="Attractions")

    # wybór tras
    if selected_ids is None:
        paths_to_draw = population
    else:
        selected_set = set(selected_ids)
        paths_to_draw = [sol for sol in population if sol["id"] in selected_set]

    # kolory
    cmap = plt.cm.get_cmap("tab20", max(1, len(paths_to_draw)))

    for idx, sol in enumerate(paths_to_draw):
        path = sol["path"]
        x = [p[1] for p in path]
        y = [p[0] for p in path]

        ax.plot(
            x,
            y,
            linewidth=1.5,
            color=cmap(idx),
            alpha=0.8
        )

    # start i koniec
    ax.scatter([start[1]], [start[0]], marker="s", s=120, c="green", label="Start")
    ax.scatter([end[1]], [end[0]], marker="X", s=120, c="red", label="End")

    ax.set_title("Paths visualization")
    ax.set_xlim(-0.5, cols - 0.5)
    ax.set_ylim(rows - 0.5, -0.5)

    # legenda tylko dla małej liczby tras
    if selected_ids is not None and len(paths_to_draw) <= 10:
        ax.legend()

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Wszystkie trasy
    draw_paths()

    # Przykład wybranych tras:
    # draw_paths(selected_ids=[0, 1, 5, 10])
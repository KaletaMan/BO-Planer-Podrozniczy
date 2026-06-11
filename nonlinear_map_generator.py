
import json
import random
import heapq
import math


def in_bounds(r, c, rows, cols):
    return 0 <= r < rows and 0 <= c < cols


def set_rect(grid, r1, r2, c1, c2, value):
    rows = len(grid)
    cols = len(grid[0])

    for r in range(max(0, r1), min(rows, r2 + 1)):
        for c in range(max(0, c1), min(cols, c2 + 1)):
            grid[r][c] = value


def set_h_line(grid, r, c1, c2, value, thickness=1):
    rows = len(grid)
    cols = len(grid[0])
    half = thickness // 2

    for rr in range(r - half, r + half + 1):
        if 0 <= rr < rows:
            for c in range(max(0, c1), min(cols, c2 + 1)):
                grid[rr][c] = value


def set_v_line(grid, c, r1, r2, value, thickness=1):
    rows = len(grid)
    cols = len(grid[0])
    half = thickness // 2

    for cc in range(c - half, c + half + 1):
        if 0 <= cc < cols:
            for r in range(max(0, r1), min(rows, r2 + 1)):
                grid[r][cc] = value


def set_diag_line(grid, r1, c1, r2, c2, value, thickness=1):
    rows = len(grid)
    cols = len(grid[0])
    steps = max(abs(r2 - r1), abs(c2 - c1))

    if steps == 0:
        return

    for i in range(steps + 1):
        t = i / steps
        r = round(r1 + (r2 - r1) * t)
        c = round(c1 + (c2 - c1) * t)

        for dr in range(-thickness, thickness + 1):
            for dc in range(-thickness, thickness + 1):
                if abs(dr) + abs(dc) <= thickness:
                    rr = r + dr
                    cc = c + dc
                    if in_bounds(rr, cc, rows, cols):
                        grid[rr][cc] = value


def dijkstra(move_time, start, end):
    rows = len(move_time)
    cols = len(move_time[0])

    sr, sc = start
    er, ec = end

    dist = [[float("inf") for _ in range(cols)] for _ in range(rows)]
    parent = {}

    dist[sr][sc] = 0
    pq = [(0, sr, sc)]

    while pq:
        d, r, c = heapq.heappop(pq)

        if (r, c) == (er, ec):
            break

        if d != dist[r][c]:
            continue

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr = r + dr
            nc = c + dc

            if not in_bounds(nr, nc, rows, cols):
                continue

            nd = d + move_time[nr][nc]

            if nd < dist[nr][nc]:
                dist[nr][nc] = nd
                parent[(nr, nc)] = (r, c)
                heapq.heappush(pq, (nd, nr, nc))

    if dist[er][ec] == float("inf"):
        raise RuntimeError("Nie znaleziono ścieżki od startu do końca")

    path = []
    cur = (er, ec)

    while cur != (sr, sc):
        path.append(cur)
        cur = parent[cur]

    path.append((sr, sc))
    path.reverse()

    return dist[er][ec], path


def generate_city_structure(rows, cols, rng):
    """
    Generuje mapę w stylu miasta:
    - domyślnie zabudowa 10+,
    - główne ulice 2-4,
    - boczne ulice 3-5,
    - place/parki 3-5,
    - cięższe kwartały 14-18.
    """

    if rows < 15 or cols < 15:
        raise ValueError("Dla tego generatora mapa powinna mieć co najmniej 15x15")

    grid = [[rng.randint(11, 15) for _ in range(cols)] for _ in range(rows)]

    center_r = rows // 2
    center_c = cols // 2

    # Główna oś pionowa i pozioma
    set_v_line(grid, center_c, 0, rows - 1, rng.randint(2, 3), thickness=3)
    set_h_line(grid, center_r, 0, cols - 1, rng.randint(2, 3), thickness=3)

    # Start/end połączone logiczną drogą
    set_v_line(grid, center_c, 0, rows - 1, 3, thickness=2)
    set_diag_line(grid, rows - 3, center_c, rows // 2, center_c, 3, thickness=1)
    set_diag_line(grid, rows // 2, center_c, 2, cols - 4, 3, thickness=1)

    # Rynek / główny plac
    market_h = max(4, rows // 7)
    market_w = max(5, cols // 6)
    set_rect(
        grid,
        center_r - market_h // 2,
        center_r + market_h // 2,
        center_c - market_w // 2,
        center_c + market_w // 2,
        3,
    )

    # Park / obwodnica zielona wokół centrum
    for r in range(rows):
        for c in range(cols):
            dr = (r - center_r) / max(1, rows * 0.38)
            dc = (c - center_c) / max(1, cols * 0.42)
            ellipse = dr * dr + dc * dc

            if 0.75 <= ellipse <= 1.05:
                grid[r][c] = min(grid[r][c], rng.randint(4, 5))

    # Kilka bocznych ulic pionowych i poziomych
    vertical_streets = sorted(set([
        cols // 5,
        cols // 3,
        2 * cols // 3,
        4 * cols // 5,
        rng.randint(3, cols - 4),
        rng.randint(3, cols - 4),
    ]))

    horizontal_streets = sorted(set([
        rows // 5,
        rows // 3,
        2 * rows // 3,
        4 * rows // 5,
        rng.randint(3, rows - 4),
        rng.randint(3, rows - 4),
    ]))

    for c in vertical_streets:
        set_v_line(grid, c, 2, rows - 3, rng.randint(3, 5), thickness=1)

    for r in horizontal_streets:
        set_h_line(grid, r, 2, cols - 3, rng.randint(3, 5), thickness=1)

    # Kilka ukośnych ulic
    set_diag_line(grid, rows // 5, cols // 8, center_r, center_c, 4, thickness=1)
    set_diag_line(grid, center_r, center_c, rows - rows // 6, cols - cols // 8, 4, thickness=1)
    set_diag_line(grid, rows - rows // 5, cols // 8, center_r, center_c, 5, thickness=1)

    # Place lokalne / parki
    for _ in range(max(3, rows * cols // 500)):
        rh = rng.randint(3, 6)
        cw = rng.randint(3, 7)
        r = rng.randint(2, rows - rh - 2)
        c = rng.randint(2, cols - cw - 2)
        value = rng.randint(3, 5)
        set_rect(grid, r, r + rh, c, c + cw, value)

    # Cięższe bloki zabudowy
    for _ in range(max(5, rows * cols // 350)):
        rh = rng.randint(3, 7)
        cw = rng.randint(3, 8)
        r = rng.randint(1, rows - rh - 1)
        c = rng.randint(1, cols - cw - 1)

        # Nie nadpisujemy ulic/parków na całym obszarze, tylko wzmacniamy zabudowę
        for rr in range(r, r + rh):
            for cc in range(c, c + cw):
                if grid[rr][cc] >= 10:
                    grid[rr][cc] = rng.randint(14, 18)

    # Lekki szum, ale nie niszczy struktury
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] <= 5:
                grid[r][c] = min(5, max(2, grid[r][c] + rng.choice([0, 0, 0, 1])))
            else:
                grid[r][c] = min(20, grid[r][c] + rng.choice([0, 0, 1, 2]))

    return grid


def is_intersection(grid, r, c):
    rows = len(grid)
    cols = len(grid[0])

    if not (2 <= grid[r][c] <= 5):
        return False

    horizontal = 0
    vertical = 0

    for dc in [-1, 1]:
        nc = c + dc
        if 0 <= nc < cols and 2 <= grid[r][nc] <= 5:
            horizontal += 1

    for dr in [-1, 1]:
        nr = r + dr
        if 0 <= nr < rows and 2 <= grid[nr][c] <= 5:
            vertical += 1

    return horizontal > 0 and vertical > 0


def near_point(r, c, point, radius):
    pr, pc = point
    return abs(r - pr) + abs(c - pc) <= radius


def choose_spread_positions(candidates, count, rng, min_distance=3):
    """
    Wybiera pozycje dość równomiernie.
    Najpierw losuje kolejność, potem preferuje punkty oddalone od już wybranych.
    """
    candidates = list(dict.fromkeys(candidates))
    rng.shuffle(candidates)

    selected = []
    used = set()

    while candidates and len(selected) < count:
        if not selected:
            p = candidates.pop()
        else:
            sample_size = min(80, len(candidates))
            sample = rng.sample(candidates, sample_size)

            def score(pos):
                r, c = pos
                d = min(abs(r - sr) + abs(c - sc) for sr, sc in selected)
                return d + rng.random() * 0.25

            p = max(sample, key=score)
            candidates.remove(p)

        if p not in used:
            if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= min_distance for q in selected):
                selected.append(p)
                used.add(p)

    # awaryjne dobieranie, gdy min_distance było zbyt ostre
    if len(selected) < count:
        for p in candidates:
            if p not in used:
                selected.append(p)
                used.add(p)
            if len(selected) >= count:
                break

    return selected[:count]


def generate_attractions(grid, rng, number_on_map=120):
    rows = len(grid)
    cols = len(grid[0])
    center_r = rows // 2
    center_c = cols // 2

    market = (center_r, center_c)

    walkable = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if 2 <= grid[r][c] <= 5
    ]

    intersections = [(r, c) for r, c in walkable if is_intersection(grid, r, c)]
    near_market = [(r, c) for r, c in walkable if near_point(r, c, market, max(rows, cols) // 6)]
    parks = [(r, c) for r, c in walkable if grid[r][c] in [4, 5]]
    side_streets = [(r, c) for r, c in walkable if abs(c - center_c) >= cols // 5]

    attraction_types = ["zabytek", "muzeum", "sakralny", "park", "gastronomia", "kulturalne"]

    # Ile atrakcji każdego typu
    plan = {
        "zabytek": int(number_on_map * 0.22),
        "muzeum": int(number_on_map * 0.18),
        "sakralny": int(number_on_map * 0.16),
        "park": int(number_on_map * 0.16),
        "gastronomia": int(number_on_map * 0.18),
    }
    plan["kulturalne"] = number_on_map - sum(plan.values())

    candidates_by_type = {
        "zabytek": near_market + intersections,
        "muzeum": side_streets + intersections,
        "sakralny": near_market + intersections,
        "park": parks,
        "gastronomia": intersections + near_market,
        "kulturalne": side_streets + walkable,
    }

    type_time = {
        "zabytek": 6,
        "muzeum": 9,
        "sakralny": 5,
        "park": 4,
        "gastronomia": 8,
        "kulturalne": 7,
    }

    attractions = []
    occupied = set()
    next_id = 1

    for typ in attraction_types:
        candidates = [p for p in candidates_by_type[typ] if p not in occupied]

        if len(candidates) < plan[typ]:
            candidates += [p for p in walkable if p not in occupied]

        positions = choose_spread_positions(
            candidates=candidates,
            count=plan[typ],
            rng=rng,
            min_distance=3,
        )

        for r, c in positions:
            occupied.add((r, c))

            # Im bliżej pionowej osi środka, tym mniejsza wartość.
            # Dzięki temu algorytm ma powód zbaczać ze środka.
            dist_from_center = abs(c - center_c) / max(1, center_c)

            base_by_type = {
                "zabytek": 28,
                "muzeum": 24,
                "sakralny": 22,
                "park": 14,
                "gastronomia": 16,
                "kulturalne": 20,
            }

            value = int(base_by_type[typ] + dist_from_center * 70 + rng.randint(0, 12))

            if abs(c - center_c) <= 3:
                value = max(5, int(value * 0.45))
            elif abs(c - center_c) <= 6:
                value = max(8, int(value * 0.65))

            if typ == "park":
                cost = 0
            elif typ == "sakralny":
                cost = rng.randint(0, 8)
            elif typ == "muzeum":
                cost = rng.randint(12, 35)
            elif typ == "gastronomia":
                cost = rng.randint(10, 30)
            elif typ == "kulturalne":
                cost = rng.randint(5, 25)
            else:
                cost = rng.randint(0, 18)

            attractions.append({
                "id": f"a{next_id}",
                "x": c,
                "y": r,
                "value": value,
                "cost": cost,
                "time": type_time[typ],
                "type": typ,
            })
            next_id += 1

    return attractions, attraction_types


def calculate_budget(attractions, desired_attractions=25, reserve_factor=1.25):
    """
    Budżet ustawiany tak, żeby dało się odwiedzić sensowną liczbę tańszych atrakcji.
    Nie jest to optymalizacja, tylko rozsądna heurystyka.
    """
    positive_costs = sorted(a["cost"] for a in attractions if a["cost"] > 0)

    if not positive_costs:
        return 0

    selected = positive_costs[:min(desired_attractions, len(positive_costs))]
    return math.ceil(sum(selected) * reserve_factor)


def generate_map(
    rows=50,
    cols=50,
    seed=7,
    number_of_attractions=130,
    filename="city_map.json",
):
    rng = random.Random(seed)

    move_time = generate_city_structure(rows, cols, rng)

    start = {
        "x": cols // 2,
        "y": 0,
    }

    end = {
        "x": cols - 4,
        "y": rows - 3,
    }

    shortest_time, shortest_path = dijkstra(
        move_time,
        start=(start["y"], start["x"]),
        end=(end["y"], end["x"]),
    )

    # Najkrótsza ścieżka ma zużyć około 70% limitu,
    # więc zostaje co najmniej około 30% na atrakcje/objazdy.
    time_limit = math.ceil(shortest_time / 0.70)

    attractions, attraction_types = generate_attractions(
        move_time,
        rng=rng,
        number_on_map=number_of_attractions,
    )

    budget = calculate_budget(
        attractions,
        desired_attractions=max(10, number_of_attractions // 5),
        reserve_factor=1.25,
    )

    data = {
        "name": f"city_like_map_seed_{seed}",
        "notes": (
            "Mapa generowana strukturalnie: najpierw układ miasta, potem lekki szum. "
            "Atrakcje są losowane z kandydatów zależnych od typu, a nie z całej mapy. "
            "Atrakcje blisko pionowej osi środka mają mniejszą wartość."
        ),
        "width": cols,
        "height": rows,
        "weights": move_time,
        "move_time": move_time,
        "start": start,
        "end": end,
        "time_limit": time_limit,
        "budget": budget,
        "attractions": attractions,
        "attraction_types": attraction_types,
        "seed": seed,
        "metadata": {
            "shortest_path_time": shortest_time,
            "shortest_path_length": len(shortest_path),
            "time_left_after_shortest_path": time_limit - shortest_time,
            "shortest_path_time_ratio": round(shortest_time / time_limit, 3),
            "attractions_count": len(attractions),
        },
    }

    # Walidacja
    if len(move_time) != rows:
        raise ValueError("Niepoprawna liczba wierszy")

    if any(len(row) != cols for row in move_time):
        raise ValueError("Niepoprawna liczba kolumn")

    if any(move_time[a["y"]][a["x"]] > 5 for a in attractions):
        raise ValueError("Atrakcja została umieszczona na trudnym polu")

    if filename is not None:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Zapisano mapę do: {filename}")
    print(f"Seed: {seed}")
    print(f"Rozmiar: {rows}x{cols}")
    print(f"Liczba atrakcji: {len(attractions)}")
    print(f"Najkrótsza ścieżka: {shortest_time}")
    print(f"Limit czasu: {time_limit}")
    print(f"Zapas czasu po najkrótszej ścieżce: {time_limit - shortest_time}")
    print(f"Budżet: {budget}")

    return data


if __name__ == "__main__":
    generate_map(
        rows=50,
        cols=50,
        seed=7,
        number_of_attractions=130,
        filename="city_map_seed_7.json",
    )

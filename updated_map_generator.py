import json
import random
import heapq
import math


def dijkstra(move_time, start, end):
    rows = len(move_time)
    cols = len(move_time[0])

    sr, sc = start
    er, ec = end

    dist = [[float("inf") for _ in range(cols)] for _ in range(rows)]
    dist[sr][sc] = 0

    pq = [(0, sr, sc)]
    parent = {}

    while pq:
        d, r, c = heapq.heappop(pq)

        if (r, c) == (er, ec):
            break

        if d != dist[r][c]:
            continue

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr = r + dr
            nc = c + dc

            if 0 <= nr < rows and 0 <= nc < cols:
                nd = d + move_time[nr][nc]

                if nd < dist[nr][nc]:
                    dist[nr][nc] = nd
                    parent[(nr, nc)] = (r, c)
                    heapq.heappush(pq, (nd, nr, nc))

    path = []
    current = end

    while current != start:
        path.append(current)
        current = parent[current]

    path.append(start)
    path.reverse()

    return dist[er][ec], path


def generate_city_like_move_time(rows, cols, seed=None):
    if seed is not None:
        random.seed(seed)

    move_time = [
        [random.randint(10, 15) for _ in range(cols)]
        for _ in range(rows)
    ]

    center_col = cols // 2
    center_row = rows // 2

    # główna pionowa droga
    for r in range(rows):
        for dc in [-1, 0, 1]:
            c = center_col + dc
            if 0 <= c < cols:
                move_time[r][c] = random.randint(2, 4)

    # główna pozioma droga
    for c in range(cols):
        for dr in [-1, 0, 1]:
            r = center_row + dr
            if 0 <= r < rows:
                move_time[r][c] = random.randint(2, 4)

    # dodatkowe uliczki
    for _ in range(rows // 2):
        r = random.randint(2, rows - 3)
        for c in range(cols):
            if random.random() < 0.75:
                move_time[r][c] = random.randint(3, 5)

    for _ in range(cols // 2):
        c = random.randint(2, cols - 3)
        for r in range(rows):
            if random.random() < 0.75:
                move_time[r][c] = random.randint(3, 5)

    # place / większe przechodnie obszary
    for _ in range(4):
        rr = random.randint(4, rows - 8)
        cc = random.randint(4, cols - 8)

        for r in range(rr, rr + random.randint(3, 6)):
            for c in range(cc, cc + random.randint(3, 6)):
                if 0 <= r < rows and 0 <= c < cols:
                    move_time[r][c] = random.randint(2, 5)

    return move_time


def generate_attractions(
    move_time,
    number_on_map=120,
    seed=None
):
    if seed is not None:
        random.seed(seed)

    rows = len(move_time)
    cols = len(move_time[0])
    center_col = cols // 2

    attraction_types = [
        "zabytek",
        "muzeum",
        "sakralny",
        "park",
        "gastronomia",
        "kulturalne"
    ]

    type_time = {
        "zabytek": 6,
        "muzeum": 10,
        "sakralny": 5,
        "park": 4,
        "gastronomia": 8,
        "kulturalne": 7
    }

    walkable = [
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if 2 <= move_time[r][c] <= 5
    ]

    random.shuffle(walkable)

    selected = []
    used = set()

    # próba równomiernego rozłożenia — wybieramy pola oddalone od już wybranych
    while walkable and len(selected) < number_on_map:
        best = max(
            walkable,
            key=lambda p: min(
                [abs(p[0] - q[0]) + abs(p[1] - q[1]) for q in selected] or [999]
            )
        )

        selected.append(best)
        used.add(best)
        walkable.remove(best)

    attractions = []

    for i, (r, c) in enumerate(selected):
        t = attraction_types[i % len(attraction_types)]

        distance_from_center = abs(c - center_col) / max(1, center_col)

        # atrakcje blisko środka są mniej opłacalne
        value = int(15 + distance_from_center * 80 + random.randint(0, 15))

        if abs(c - center_col) <= 3:
            value = max(5, int(value * 0.45))
        elif abs(c - center_col) <= 6:
            value = max(8, int(value * 0.65))

        if t == "park":
            cost = 0
        elif t == "sakralny":
            cost = random.randint(0, 8)
        elif t == "muzeum":
            cost = random.randint(12, 35)
        elif t == "gastronomia":
            cost = random.randint(10, 30)
        else:
            cost = random.randint(0, 20)

        attractions.append({
            "id": f"a{i + 1}",
            "x": c,
            "y": r,
            "value": value,
            "cost": cost,
            "time": type_time[t],
            "type": t
        })

    return attractions, attraction_types


def generate_map(
    rows=50,
    cols=50,
    seed=7,
    number_of_attractions=130,
    filename="generated_map.json"
):
    random.seed(seed)

    move_time = generate_city_like_move_time(rows, cols, seed=seed)

    start = {
        "x": cols // 2,
        "y": 0
    }

    end = {
        "x": cols - 4,
        "y": rows - 3
    }

    shortest_time, shortest_path = dijkstra(
        move_time,
        start=(start["y"], start["x"]),
        end=(end["y"], end["x"])
    )

    time_limit = math.ceil(shortest_time / 0.7)

    attractions, attraction_types = generate_attractions(
        move_time,
        number_on_map=number_of_attractions,
        seed=seed + 1000
    )

    # budżet ustawiony tak, żeby dało się odwiedzić sensowną liczbę atrakcji
    sorted_costs = sorted(a["cost"] for a in attractions if a["cost"] > 0)
    budget = sum(sorted_costs[:25])

    data = {
        "name": f"generated_city_map_seed_{seed}",
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
            "time_left_after_shortest_path": time_limit - shortest_time,
            "shortest_path_time_ratio": round(shortest_time / time_limit, 3)
        }
    }

    if filename is not None:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Zapisano mapę do {filename}")
    print(f"Najkrótsza droga: {shortest_time}")
    print(f"Limit czasu: {time_limit}")
    print(f"Zapas czasu: {time_limit - shortest_time}")
    print(f"Budżet: {budget}")
    print(f"Liczba atrakcji: {len(attractions)}")

    return data


if __name__ == "__main__":
    generate_map(
        rows=50,
        cols=50,
        seed=7,
        filename="map_seed_7.json"
    )
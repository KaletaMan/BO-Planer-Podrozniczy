import json


def load_map_from_json(filename="map.json"):
    """
    Wczytuje dane mapy z pliku JSON.

    Zwraca:
    - weight
    - time_limit
    - budget
    - attractions
    - attraction_types
    """

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    required_keys = ["weight", "time", "budget", "attractions", "attraction_types"]

    for key in required_keys:
        if key not in data:
            raise ValueError(f"Brakuje klucza w JSON: {key}")

    weight = data["weight"]
    time_limit = data["time"]
    budget = data["budget"]
    attractions = data["attractions"]
    attraction_types = data["attraction_types"]

    if not isinstance(weight, list) or not isinstance(weight[0], list):
        raise ValueError("weight musi być listą list")

    if not isinstance(time_limit, int):
        raise ValueError("time musi być int")

    if not isinstance(budget, int):
        raise ValueError("budget musi być int")

    if not isinstance(attractions, list):
        raise ValueError("attractions musi być listą")

    if not isinstance(attraction_types, list):
        raise ValueError("attraction_types musi być listą")

    return weight, time_limit, budget, attractions, attraction_types


if __name__ == "__main__":
    weight, time_limit, budget, attractions, attraction_types = load_map_from_json("map.json")

    print("Rozmiar mapy:", len(weight), "x", len(weight[0]))
    print("Time limit:", time_limit)
    print("Budget:", budget)
    print("Liczba atrakcji:", len(attractions))
    print("Typy atrakcji:", attraction_types)
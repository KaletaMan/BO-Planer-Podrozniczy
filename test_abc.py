import json

from src.abc_ui_adapter import solve_abc_ui


with open("scenarios/15x15_20atr.json", "r", encoding="utf-8") as f:
    map_data = json.load(f)

result = solve_abc_ui(
    map_data,
    population_size=30,
    iterations=100,
    limit=30,
    seed=42,
)

best = result["best"]

print("=== ABC TEST ===")
print("Wartość:", best["total_value"])
print("Koszt atrakcji:", best["attraction_cost"])
print("Budżet:", map_data["budget"])
print("Czy mieści się w budżecie:", best["attraction_cost"] <= map_data["budget"])
print("Liczba atrakcji:", len(best["visited_attractions"]))
print("Ścieżka:")
print(result["path"])
# BO-Planer-Podrozniczy

## Uruchomienie

Dodatkowe przykłady komend i walidacji: `examples/README.md`.

### 1) Generowanie mapy

```bash
python3 map_generator.py
```

Generator zapisuje `map.json` w formacie CLI:
- `move_time` – siatka czasu przejścia (minuty)
- `time_limit` – limit czasu (minuty)
- `budget` – budżet pieniężny
- `attractions[][3]` – cena atrakcji (wliczana do `budget`)

### 2) Generowanie populacji tras (ABC – algorytm pszczeli)

Wariant ABC (Artificial Bee Colony) generuje wyłącznie rozwiązania dopuszczalne (czas/budżet/typy) i dodatkowo pilnuje twardo, aby żadne przejście (krawędź między sąsiadującymi polami) nie zostało użyte więcej niż raz.

```bash
python3 initial_population.py --population-size 50 --iters 200 --limit 60 --out initial_population.json
```

Parametry:

- `--iters` – liczba iteracji ABC
- `--limit` – limit stagnacji (po tylu nieudanych próbach rozwiązanie jest zastępowane przez „scout”)
- `--onlookers` – (opcjonalnie) liczba prób fazy onlooker na iterację
- `--seed` – (opcjonalnie) ziarno losowości

### 3) Wizualizacj

```bash
python3 visualize_paths.py
```

Jeśli zapiszesz populację do innego pliku niż `initial_population.json`, możesz uruchomić wizualizację tak:

```bash
python3 -c "from visualize_paths import draw_paths; draw_paths(population_file='initial_population_abc.json')"
```

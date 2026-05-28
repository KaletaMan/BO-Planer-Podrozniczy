from __future__ import annotations

from typing import Dict, Tuple

ATTRACTION_TYPES = ["zabytek", "muzeum", "sakralny"]


def generate_krakow_old_town(variant: str = "normal", seed: int = 7) -> dict:
    """Generuje themed mapę Starego Miasta Krakowa (20x20).

    Layout (pionowa oś N-S): Barbakan → Brama Floriańska → Floriańska →
    Rynek Główny (z Sukiennicami, Mariackim) → Grodzka → Wawel.

    Wagi: 1 = ulice główne, 2 = uliczki/dziedzińce, 3 = Rynek/Planty,
    5 = Wawel/bramy, 8 = kamienice, 10 = mury/Wisła.
    """
    if variant not in ("easy", "normal", "hard"):
        raise ValueError(f"Unknown variant: {variant!r} (expected: easy/normal/hard)")

    W, H = 20, 20

    weights = [[8] * W for _ in range(H)]

    for x in range(W):
        weights[0][x] = 3
        weights[H - 1][x] = 3
    for y in range(H):
        weights[y][0] = 3
        weights[y][W - 1] = 3

    for y in range(7, 12):
        for x in range(7, 14):
            weights[y][x] = 3

    for y in range(2, 7):
        weights[y][10] = 1
    for y in range(12, 15):
        weights[y][10] = 1

    for x in range(2, 18):
        if weights[10][x] == 8:
            weights[10][x] = 2

    for x in range(3, 18):
        if weights[5][x] == 8:
            weights[5][x] = 2
    for x in range(3, 18):
        if weights[14][x] == 8:
            weights[14][x] = 2

    for y in range(15, 18):
        for x in range(8, 13):
            weights[y][x] = 5

    for y in range(15, 18):
        weights[y][7] = 10
        weights[y][13] = 10
    for x in range(8, 13):
        weights[18][x] = 10

    weights[1][10] = 5

    attractions = [
        {"id": "a1",  "x": 10, "y": 1,  "value": 45,  "type": "zabytek"},
        {"id": "a2",  "x": 10, "y": 2,  "value": 50,  "type": "zabytek"},
        {"id": "a3",  "x": 13, "y": 5,  "value": 60,  "type": "muzeum"},
        {"id": "a4",  "x": 10, "y": 9,  "value": 70,  "type": "zabytek"},
        {"id": "a5",  "x": 13, "y": 8,  "value": 80,  "type": "sakralny"},
        {"id": "a6",  "x": 7,  "y": 11, "value": 40,  "type": "zabytek"},
        {"id": "a7",  "x": 9,  "y": 10, "value": 55,  "type": "muzeum"},
        {"id": "a8",  "x": 10, "y": 12, "value": 30,  "type": "sakralny"},
        {"id": "a9",  "x": 11, "y": 14, "value": 55,  "type": "sakralny"},
        {"id": "a10", "x": 10, "y": 17, "value": 100, "type": "zabytek"},
        {"id": "a11", "x": 12, "y": 17, "value": 85,  "type": "sakralny"},
        {"id": "a12", "x": 5,  "y": 5,  "value": 65,  "type": "muzeum"},
    ]

    variants: Dict[str, Dict] = {
        "easy": {
            "start": (10, 0),
            "end": (10, 11),
            "budget": 20,
            "name": "Krakow Stare Miasto - latwy",
            "notes": "Z Plant pn. przez Brame Florianska na Rynek. Ciasny budzet.",
        },
        "normal": {
            "start": (10, 0),
            "end": (10, 16),
            "budget": 40,
            "name": "Krakow Stare Miasto",
            "notes": "Planty pn. -> dziedziniec Wawelu pionowa osia. Hero scenariusz.",
        },
        "hard": {
            "start": (1, 10),
            "end": (18, 10),
            "budget": 70,
            "name": "Krakow Stare Miasto - trudny",
            "notes": "Planty zach. -> Planty wsch. Wymusza objazd centrum.",
        },
    }
    v = variants[variant]

    return {
        "name": v["name"],
        "notes": v["notes"],
        "width": W,
        "height": H,
        "weights": weights,
        "attractions": attractions,
        "attraction_types": ATTRACTION_TYPES,
        "start": {"x": v["start"][0], "y": v["start"][1]},
        "end": {"x": v["end"][0], "y": v["end"][1]},
        "budget": v["budget"],
        "seed": seed,
    }

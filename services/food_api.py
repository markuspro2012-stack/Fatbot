import httpx
import os
from typing import Optional

from services.local_food_db import search_local_food

USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")

_ENERGY_NAMES = {"Energy"}
_PROTEIN_NAMES = {"Protein"}
_FAT_NAMES = {"Total lipid (fat)"}
_CARB_NAMES = {"Carbohydrate, by difference"}


async def search_food(query: str, page_size: int = 8) -> list[dict]:
    # 1. Local DB first — instant, no network
    local = search_local_food(query, top_k=page_size)

    # If we have 4+ local results, return immediately without calling USDA
    if len(local) >= 4:
        return local[:page_size]

    # 2. USDA API as fallback / supplement
    usda = await _search_usda(query, page_size)

    # Merge: local results first, then USDA unique items
    local_names = {r["name"].lower() for r in local}
    merged = local[:]
    for r in usda:
        if r["name"].lower() not in local_names:
            merged.append(r)

    return merged[:page_size]


async def _search_usda(query: str, page_size: int = 8) -> list[dict]:
    params = {
        "query": query,
        "api_key": USDA_KEY,
        "pageSize": page_size,
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(USDA_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception:
        return []

    results = []
    for food in data.get("foods", []):
        name = food.get("description", "").strip()
        if not name:
            continue

        raw = food.get("foodNutrients", [])
        kcal = _get_kcal(raw)
        if kcal is None or kcal <= 0 or kcal > 1200:
            continue

        results.append({
            "name": name[:100],
            "kcal_100g": round(kcal, 1),
            "protein_100g": round(_get_nutrient(raw, _PROTEIN_NAMES) or 0, 1),
            "fat_100g": round(_get_nutrient(raw, _FAT_NAMES) or 0, 1),
            "carbs_100g": round(_get_nutrient(raw, _CARB_NAMES) or 0, 1),
        })

    return results[:page_size]


def _get_kcal(nutrients: list) -> Optional[float]:
    kcal_val = None
    kj_val = None
    for n in nutrients:
        name = n.get("nutrientName", "")
        unit = n.get("unitName", "")
        val = n.get("value")
        if val is None:
            continue
        if name in _ENERGY_NAMES:
            if unit in ("KCAL", "kcal"):
                try:
                    kcal_val = float(val)
                except (TypeError, ValueError):
                    pass
            elif unit in ("kJ", "KJ"):
                try:
                    kj_val = float(val)
                except (TypeError, ValueError):
                    pass
    if kcal_val is not None:
        return kcal_val
    if kj_val is not None:
        return kj_val / 4.184
    for n in nutrients:
        if n.get("nutrientName", "") in _ENERGY_NAMES:
            try:
                return float(n["value"])
            except (TypeError, ValueError, KeyError):
                pass
    return None


def _get_nutrient(nutrients: list, names: set) -> Optional[float]:
    for n in nutrients:
        if n.get("nutrientName", "") in names:
            try:
                return float(n["value"])
            except (TypeError, ValueError, KeyError):
                pass
    return None


def calculate_portion(product: dict, grams: float) -> dict:
    ratio = grams / 100
    return {
        "calories": round(product["kcal_100g"] * ratio, 1),
        "protein": round(product["protein_100g"] * ratio, 1),
        "fat": round(product["fat_100g"] * ratio, 1),
        "carbs": round(product["carbs_100g"] * ratio, 1),
    }

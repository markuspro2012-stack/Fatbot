import httpx
import os
from typing import Optional

USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")

# Nutrient IDs / names in USDA database
_ENERGY_NAMES = {"Energy"}
_PROTEIN_NAMES = {"Protein"}
_FAT_NAMES = {"Total lipid (fat)"}
_CARB_NAMES = {"Carbohydrate, by difference"}


async def search_food(query: str, page_size: int = 8) -> list[dict]:
    params = {
        "query": query,
        "api_key": USDA_KEY,
        "pageSize": page_size,
        "dataType": "Survey (FNDDS),SR Legacy,Foundation",
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

        nutrients = {n.get("nutrientName", ""): n.get("value") for n in food.get("foodNutrients", [])}

        kcal = _pick(nutrients, _ENERGY_NAMES)
        if kcal is None or kcal <= 0 or kcal > 1200:
            continue

        results.append({
            "name": name[:100],
            "kcal_100g": round(kcal, 1),
            "protein_100g": round(_pick(nutrients, _PROTEIN_NAMES) or 0, 1),
            "fat_100g": round(_pick(nutrients, _FAT_NAMES) or 0, 1),
            "carbs_100g": round(_pick(nutrients, _CARB_NAMES) or 0, 1),
        })

    return results[:page_size]


def _pick(nutrients: dict, names: set) -> Optional[float]:
    for k, v in nutrients.items():
        if k in names and v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
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

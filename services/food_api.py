import httpx
from typing import Optional

OPENFOODFACTS_URL = "https://world.openfoodfacts.org/cgi/search.pl"


async def search_food(query: str, page_size: int = 6) -> list[dict]:
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": page_size,
        "fields": "product_name,brands,nutriments",
        "sort_by": "unique_scans_n",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(OPENFOODFACTS_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

    results = []
    for product in data.get("products", []):
        name = product.get("product_name", "").strip()
        if not name:
            continue

        nutriments = product.get("nutriments", {})
        kcal = _get_float(nutriments, "energy-kcal_100g", "energy_100g")
        if kcal is None:
            continue
        if kcal > 900 or kcal < 0:
            continue

        brand = product.get("brands", "").split(",")[0].strip()
        display_name = f"{name} ({brand})" if brand else name

        results.append({
            "name": display_name[:100],
            "kcal_100g": round(kcal, 1),
            "protein_100g": round(_get_float(nutriments, "proteins_100g") or 0, 1),
            "fat_100g": round(_get_float(nutriments, "fat_100g") or 0, 1),
            "carbs_100g": round(_get_float(nutriments, "carbohydrates_100g") or 0, 1),
        })

        if len(results) >= page_size:
            break

    return results


def _get_float(nutriments: dict, *keys) -> Optional[float]:
    for key in keys:
        val = nutriments.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def calculate_portion(product: dict, grams: float) -> dict:
    ratio = grams / 100
    return {
        "calories": round(product["kcal_100g"] * ratio, 1),
        "protein": round(product["protein_100g"] * ratio, 1),
        "fat": round(product["fat_100g"] * ratio, 1),
        "carbs": round(product["carbs_100g"] * ratio, 1),
    }

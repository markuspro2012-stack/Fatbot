import httpx
from typing import Optional

OPENFOODFACTS_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OPENFOODFACTS_V2 = "https://world.openfoodfacts.org/api/v2/search"

HEADERS = {
    "User-Agent": "FatBot/1.0 (calorie tracker; markuspro2012@gmail.com)",
    "Accept": "application/json",
}


async def search_food(query: str, page_size: int = 8) -> list[dict]:
    results = await _search_v2(query, page_size)
    if not results:
        results = await _search_v1(query, page_size)
    return results


async def _search_v2(query: str, page_size: int) -> list[dict]:
    params = {
        "q": query,
        "fields": "product_name,brands,nutriments",
        "sort_by": "unique_scans_n",
        "page_size": page_size,
    }
    try:
        async with httpx.AsyncClient(timeout=12.0, headers=HEADERS) as client:
            response = await client.get(OPENFOODFACTS_V2, params=params)
            response.raise_for_status()
            data = response.json()
        return _parse_products(data.get("products", []), page_size)
    except Exception:
        return []


async def _search_v1(query: str, page_size: int) -> list[dict]:
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": page_size,
        "fields": "product_name,brands,nutriments",
        "sort_by": "unique_scans_n",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0, headers=HEADERS) as client:
            response = await client.get(OPENFOODFACTS_URL, params=params)
            response.raise_for_status()
            data = response.json()
        return _parse_products(data.get("products", []), page_size)
    except Exception:
        return []


def _parse_products(products: list, page_size: int) -> list[dict]:
    results = []
    for product in products:
        name = product.get("product_name", "").strip()
        if not name:
            continue

        nutriments = product.get("nutriments", {})

        # Try kcal field first; fall back to kJ and convert (÷4.184)
        kcal = _get_float(nutriments, "energy-kcal_100g", "energy-kcal")
        if kcal is None:
            kj = _get_float(nutriments, "energy_100g", "energy")
            if kj is not None:
                kcal = kj / 4.184

        if kcal is None or kcal < 0 or kcal > 1200:
            continue

        brand = product.get("brands", "").split(",")[0].strip()
        display_name = f"{name} ({brand})" if brand else name

        results.append({
            "name": display_name[:100],
            "kcal_100g": round(kcal, 1),
            "protein_100g": round(_get_float(nutriments, "proteins_100g", "proteins") or 0, 1),
            "fat_100g": round(_get_float(nutriments, "fat_100g", "fat") or 0, 1),
            "carbs_100g": round(_get_float(nutriments, "carbohydrates_100g", "carbohydrates") or 0, 1),
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

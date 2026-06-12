import base64
import json
import httpx
from config import GROQ_API_KEY

_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

_PROMPT = (
    "Look at this food photo and identify what you see.\n\n"
    "Respond ONLY with valid JSON, no extra text:\n"
    "{\n"
    '  "food_name": "название блюда на русском",\n'
    '  "amount_g": <estimated weight of the portion in grams as number>,\n'
    '  "calories": <total kcal for this portion as number>,\n'
    '  "protein": <total protein grams as number>,\n'
    '  "fat": <total fat grams as number>,\n'
    '  "carbs": <total carbs grams as number>,\n'
    '  "confidence": "high" or "medium" or "low"\n'
    "}\n\n"
    "If you cannot identify food in the image respond with:\n"
    '{"error": "not_food"}\n\n'
    "Rules:\n"
    "- food_name must be in Russian\n"
    "- calories/protein/fat/carbs: for the FULL estimated portion, not per 100g\n"
    "- Be accurate and realistic"
)


_LABEL_PROMPT = (
    "This is a photo of a food product package with its nutrition label "
    "(пищевая ценность / состав).\n\n"
    "Extract the product name and nutrition values PER 100 g (or 100 ml).\n\n"
    "Respond ONLY with valid JSON, no extra text:\n"
    "{\n"
    '  "name": "название продукта на русском (с брендом, если виден)",\n'
    '  "kcal_100g": <kcal per 100 g as number>,\n'
    '  "protein_100g": <protein grams per 100 g as number>,\n'
    '  "fat_100g": <fat grams per 100 g as number>,\n'
    '  "carbs_100g": <carbs grams per 100 g as number>\n'
    "}\n\n"
    "If the image has no readable nutrition information respond with:\n"
    '{"error": "not_label"}\n\n'
    "Rules:\n"
    "- Read the printed numbers carefully and exactly as written\n"
    "- If values are given per serving/portion, recalculate to per 100 g\n"
    "- If energy is only in kJ, convert to kcal (divide by 4.184)\n"
    "- If product name is not visible, use empty string for name"
)


async def analyze_nutrition_label(image_bytes: bytes) -> dict | None:
    if not GROQ_API_KEY:
        return {"error": "no_key"}

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": _MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": _LABEL_PROMPT},
        ]}],
        "max_tokens": 300,
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        return {"error": f"api_error: {e}"}

    try:
        raw = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        return {"error": "parse_error"}

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "parse_error"}

    if "error" in result:
        return result

    required = {"kcal_100g", "protein_100g", "fat_100g", "carbs_100g"}
    if not required.issubset(result.keys()):
        return {"error": "incomplete_data"}

    try:
        return {
            "name": str(result.get("name", ""))[:100],
            "kcal_100g": round(float(result["kcal_100g"]), 1),
            "protein_100g": round(float(result["protein_100g"]), 1),
            "fat_100g": round(float(result["fat_100g"]), 1),
            "carbs_100g": round(float(result["carbs_100g"]), 1),
        }
    except (TypeError, ValueError):
        return {"error": "parse_error"}


async def analyze_food_photo(image_bytes: bytes) -> dict | None:
    if not GROQ_API_KEY:
        return {"error": "no_key"}

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": _MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            {"type": "text", "text": _PROMPT},
        ]}],
        "max_tokens": 400,
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        return {"error": f"api_error: {e}"}

    try:
        raw = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        return {"error": "parse_error"}

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "parse_error"}

    if "error" in result:
        return result

    required = {"food_name", "amount_g", "calories", "protein", "fat", "carbs"}
    if not required.issubset(result.keys()):
        return {"error": "incomplete_data"}

    return {
        "food_name": str(result["food_name"])[:100],
        "amount_g": round(float(result["amount_g"]), 0),
        "calories": round(float(result["calories"]), 1),
        "protein": round(float(result["protein"]), 1),
        "fat": round(float(result["fat"]), 1),
        "carbs": round(float(result["carbs"]), 1),
        "confidence": result.get("confidence", "medium"),
    }

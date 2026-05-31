import base64
import json
import httpx
from config import GEMINI_API_KEY

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


async def analyze_food_photo(image_bytes: bytes) -> dict | None:
    if not GEMINI_API_KEY:
        return {"error": "no_key"}

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            {"text": _PROMPT}
        ]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400}
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        return {"error": f"api_error: {e}"}

    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
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

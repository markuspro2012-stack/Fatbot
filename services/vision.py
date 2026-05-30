import base64
import json
from openai import AsyncOpenAI
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are a professional nutritionist and food recognition AI. "
    "Analyze food photos and return accurate nutritional estimates."
)

USER_PROMPT = (
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
    "If you cannot identify food in the image, respond with:\n"
    '{"error": "not_food"}\n\n'
    "Rules:\n"
    "- food_name in Russian\n"
    "- amount_g: realistic portion size (e.g. bowl of soup ~350g, sandwich ~200g)\n"
    "- calories/protein/fat/carbs: for the FULL estimated portion, not per 100g\n"
    "- Be accurate but realistic — do not guess wildly"
)


async def analyze_food_photo(image_bytes: bytes) -> dict | None:
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": USER_PROMPT},
                    ],
                },
            ],
            max_tokens=300,
            temperature=0.2,
        )
    except Exception as e:
        return {"error": f"api_error: {e}"}

    raw = response.choices[0].message.content.strip()

    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "parse_error"}

    if "error" in data:
        return data

    required = {"food_name", "amount_g", "calories", "protein", "fat", "carbs"}
    if not required.issubset(data.keys()):
        return {"error": "incomplete_data"}

    return {
        "food_name": str(data["food_name"])[:100],
        "amount_g": round(float(data["amount_g"]), 0),
        "calories": round(float(data["calories"]), 1),
        "protein": round(float(data["protein"]), 1),
        "fat": round(float(data["fat"]), 1),
        "carbs": round(float(data["carbs"]), 1),
        "confidence": data.get("confidence", "medium"),
    }

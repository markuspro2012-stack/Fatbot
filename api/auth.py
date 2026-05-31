import hashlib
import hmac
import json
from urllib.parse import parse_qs, unquote

from fastapi import Header, HTTPException
from config import BOT_TOKEN


def validate_init_data(init_data: str) -> dict | None:
    try:
        params = dict(parse_qs(init_data, keep_blank_values=True))
        hash_val = params.pop("hash", [None])[0]
        if not hash_val:
            return None

        data_check = "\n".join(f"{k}={v[0]}" for k, v in sorted(params.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected, hash_val):
            return None

        user_str = params.get("user", [None])[0]
        return json.loads(unquote(user_str)) if user_str else {}
    except Exception:
        return None


async def get_current_user_id(x_init_data: str = Header(..., alias="X-Init-Data")) -> int:
    user = validate_init_data(x_init_data)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    uid = user.get("id")
    if not uid:
        raise HTTPException(status_code=401, detail="No user id in init data")
    return int(uid)

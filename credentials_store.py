import json
import os
from datetime import datetime
from typing import Optional, Tuple

from redis_store import load_credentials as load_credentials_redis
from redis_store import save_credentials as save_credentials_redis

CREDENTIALS_FILE = os.getenv("DHAN_CREDENTIALS_FILE", "dhan_credentials.json")


def load_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load saved Dhan credentials from Redis (preferred) or disk."""
    client_id, access_token = load_credentials_redis()
    if client_id and access_token:
        return client_id, access_token

    if not os.path.exists(CREDENTIALS_FILE):
        return None, None

    try:
        with open(CREDENTIALS_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        return None, None

    client_id = data.get("client_id") or None
    access_token = data.get("access_token") or None
    return client_id, access_token


def save_credentials(client_id: str, access_token: str) -> None:
    """Persist Dhan credentials to Redis and disk."""
    if not client_id or not access_token:
        return

    save_credentials_redis(client_id, access_token)

    payload = {
        "client_id": client_id,
        "access_token": access_token,
        "saved_at": datetime.now().isoformat(),
    }

    tmp_path = f"{CREDENTIALS_FILE}.tmp"
    with open(tmp_path, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, CREDENTIALS_FILE)

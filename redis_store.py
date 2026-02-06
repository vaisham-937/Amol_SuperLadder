import json
import logging
import os
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _get_redis_client():
    try:
        import redis
    except Exception as e:
        logger.warning(f"Redis client not available: {e}")
        return None

    try:
        return redis.Redis.from_url(DEFAULT_REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis at {DEFAULT_REDIS_URL}: {e}")
        return None


def _seconds_until_end_of_day_ist() -> int:
    now = datetime.now(IST)
    end = datetime.combine(now.date(), dt_time(23, 59, 59), IST)
    if now >= end:
        end = end + timedelta(days=1)
    return int((end - now).total_seconds())


def save_credentials(client_id: str, access_token: str) -> bool:
    r = _get_redis_client()
    if not r:
        return False
    try:
        r.hset("dhan:credentials", mapping={
            "client_id": client_id,
            "access_token": access_token,
            "saved_at": datetime.now(IST).isoformat(),
        })
        return True
    except Exception as e:
        logger.warning(f"Failed to save credentials to Redis: {e}")
        return False


def load_credentials() -> Tuple[Optional[str], Optional[str]]:
    r = _get_redis_client()
    if not r:
        return None, None
    try:
        data = r.hgetall("dhan:credentials")
        if not data:
            return None, None
        return data.get("client_id") or None, data.get("access_token") or None
    except Exception:
        return None, None


def save_candidates(candidates: Dict[str, float], metadata: Dict) -> bool:
    r = _get_redis_client()
    if not r:
        return False
    try:
        today_key = f"dhan:premarket:candidates:{datetime.now(IST).strftime('%Y%m%d')}"
        payload = {
            "timestamp": metadata.get("timestamp"),
            "criteria": metadata.get("criteria"),
            "total_stocks_screened": metadata.get("total_stocks_screened"),
            "stocks_accepted": metadata.get("stocks_accepted"),
            "candidates": candidates,
        }
        r.set(today_key, json.dumps(payload))
        r.set("dhan:premarket:candidates:latest", today_key)
        r.expire(today_key, _seconds_until_end_of_day_ist())
        return True
    except Exception as e:
        logger.warning(f"Failed to save candidates to Redis: {e}")
        return False


def load_candidates() -> Optional[Dict]:
    r = _get_redis_client()
    if not r:
        return None
    try:
        latest_key = r.get("dhan:premarket:candidates:latest")
        if not latest_key:
            return None
        raw = r.get(latest_key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None

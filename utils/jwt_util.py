from datetime import datetime, timedelta
from typing import Any, Optional

import jwt

from utils.setting import settings


def create_access_token(
    user_id: int,
    *,
    role: str = "staff",
    username: str = "",
) -> str:
    """生成 JWT：sub=用户 id，附带 role / username。"""
    expire = datetime.utcnow() + timedelta(seconds=settings.JWT_ACCESS_TOKEN_EXPIRES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "username": username,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_token(token: str) -> Optional[dict[str, Any]]:
    """
    验签 + 过期校验。
    成功返回 {"id", "role", "username"}；失败返回 None。
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        user_id = int(payload.get("sub"))
        return {
            "id": user_id,
            "role": payload.get("role") or "staff",
            "username": payload.get("username") or "",
        }
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None
    except (TypeError, ValueError):
        return None

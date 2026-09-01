from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from utils.jwt_util import verify_token
from utils.rbac import assert_perm

security = HTTPBearer(auto_error=False)


def _user_from_credentials(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[dict[str, Any]]:
    if not credentials or credentials.scheme.lower() != "bearer":
        return None
    return verify_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict[str, Any]]:
    return _user_from_credentials(credentials)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Any]:
    user = _user_from_credentials(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或 token 无效/过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_perm(perm: str) -> Callable:
    async def _dep(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        deny = assert_perm(user, perm)
        if deny:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=deny)
        return user

    return _dep

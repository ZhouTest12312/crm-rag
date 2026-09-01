
from fastapi import APIRouter
from fastapi import HTTPException
from schemas.auth import LoginResponse, LoginRequest
from utils.jwt_util import create_access_token
from utils.rbac import DEMO_USERS

router = APIRouter(prefix="/api/auth", tags=["auth"])
@router.post('/login',response_model=LoginResponse)
async def get_login(body: LoginRequest):
    row = DEMO_USERS.get(body.username.strip())
    if not row or row['password']!=body.password:
        raise HTTPException(status_code=401,detail='密码不对')
    username = body.username.strip()
    role = row["role"]
    token = create_access_token(
        row['id'],
        role=role,
        username=username
    )
    return LoginResponse(
        access_token=token,
        user={
            "id": row["id"],
            "username": username,
            "role": role,
        },
    )

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status, Depends
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from config import setting
import models
from typing import Annotated
from database import DbSession

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")

BearerToken = Annotated[str, Depends(oauth2_scheme)]


def hash_password(plaint_password:str) -> str:
    return password_hash.hash(plaint_password)

def verify_password(plaint_password: str, hashed_password:str) -> bool:
    return password_hash.verify(plaint_password, hashed_password)

def create_access_token(data:dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    # data = {'sub': 1}

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=setting.access_token_expired_minutes)

    to_encode.update({"exp":expire})
    # to_encode = {'sub': 1, 'exp':expire}

    access_token = jwt.encode(
        to_encode,
        setting.secret_key.get_secret_value(),
        algorithm=setting.algorithm
    )

    return access_token

def verify_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            setting.secret_key.get_secret_value(),
            algorithms=[setting.algorithm],
            options={"require": ["sub", "exp"]}
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")


async def get_current_user(token: BearerToken, db: DbSession):
    user_id = verify_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    result = await db.execute(select(models.User).where(models.User.id == user_id_int))
    current_user = result.scalars().first()

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return current_user


CurrentUser = Annotated[models.User, Depends(get_current_user)]
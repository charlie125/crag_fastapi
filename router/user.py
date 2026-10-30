from fastapi import HTTPException, status, Depends, APIRouter
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from typing import Annotated
import models
from schemas import UserResponse, UserCreate, Token
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from auth import hash_password, verify_password, verify_access_token, create_access_token, oauth2_scheme

from config import setting

router = APIRouter()
Dbsession = Annotated[AsyncSession, Depends(get_db)]
token = Annotated[str, Depends(oauth2_scheme)]
form = Annotated[OAuth2PasswordRequestForm, Depends()]

@router.post("", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def create_user(user: UserCreate, db: Dbsession):
    result = await db.execute(select(models.User).where(models.User.username == user.username))
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    result = await db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = result.scalars().first()

    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    new_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password)
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
async def login(db: Dbsession, form_data: form):
    result = await db.execute(select(models.User).where(models.User.email == form_data.username))
    existing_user = result.scalars().first()

    if not existing_user or not verify_password(form_data.password, existing_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token_expires = timedelta(minutes=setting.access_token_expired_minutes)
    access_token = create_access_token(
        data={"sub":str(existing_user.id)},
        expires_delta = access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user(db:Dbsession, token:token):
    user_id = verify_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate":"bearer"}
        )

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate":"bearer"}
        )

    result = await db.execute(select(models.User).where(models.User.id == user_id_int))
    current_user = result.scalars().first()

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "bearer"}
        )

    return current_user



@router.get("", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def get_all_user(db:Dbsession):
    result = await db.execute(select(models.User))
    users = result.scalars().all()

    return users
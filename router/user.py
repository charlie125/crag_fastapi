from fastapi import HTTPException, status, Depends, APIRouter
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Annotated
import models
from schemas import UserResponse, UserCreate, Token, QueryResponse
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from auth import hash_password, verify_password, create_access_token, CurrentUser
from database import DbSession

from config import setting

router = APIRouter()
Form = Annotated[OAuth2PasswordRequestForm, Depends()]

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: DbSession):
    result = await db.execute(select(models.User).where(func.lower(models.User.username) == user.username.lower()))
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    result = await db.execute(select(models.User).where(func.lower(models.User.email) == user.email.lower()))
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
async def login(db: DbSession, form_data: Form):
    result = await db.execute(select(models.User).where(func.lower(models.User.email) == form_data.username.lower()))
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

@router.get("", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def get_all_user(db:DbSession):
    result = await db.execute(select(models.User))
    users = result.scalars().all()

    return users


@router.get("/{username}/histories", response_model=list[QueryResponse])
async def get_user_histories(db: DbSession, user: CurrentUser, username: str):

    if user.username.lower() != username.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own histories"
        )

    result = await db.execute(select(models.Response).options(selectinload(models.Response.user)).where(models.Response.user_id == user.id))
    target_responses = result.scalars().all()
    return target_responses
from fastapi import HTTPException, status, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from typing import Annotated
import models
from schemas import UserResponse, UserCreate

router = APIRouter()
Dbsession = Annotated[AsyncSession, Depends(get_db)]

@router.post("", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def create_user(user: UserCreate, db: Dbsession):
    pass

@router.get("", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def get_all_user(db:Dbsession):
    result = await db.execute(select(models.User))
    users = result.scalars().all()

    return users
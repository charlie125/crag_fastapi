from fastapi import status, Depends, APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from typing import Annotated
import models
from schemas import QueryResponse, QueryCreate
from capped_crag import capped_main
import datetime

router = APIRouter()
Dbsession = Annotated[AsyncSession, Depends(get_db)]

@router.post("", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def create_query(query: QueryCreate, db:Dbsession):
    result = capped_main(query.query)
    new_chat = models.Response(query=query.query, response=result, date_created=datetime.datetime.now(), user_id=1)

    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)

    return new_chat

@router.get("", response_model=list[QueryResponse], status_code=status.HTTP_200_OK)
async def get_all_chat(db:Dbsession):
    target = await db.execute(select(models.Response).options(models.Response.user))
    results = target.scalars().all()
    return results
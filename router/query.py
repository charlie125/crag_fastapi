from fastapi import status, APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import models
from schemas import QueryResponse, QueryCreate
from capped_crag import capped_main
import datetime
import asyncio
from auth import CurrentUser
from database import DbSession

router = APIRouter()

@router.post("", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def create_query(query: QueryCreate, db:DbSession, current_user: CurrentUser):

    result = await asyncio.to_thread(capped_main, query.query)
    new_chat = models.Response(query=query.query, response=result, date_created=datetime.datetime.now(), user_id=current_user.id, user=current_user)

    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)

    return new_chat

@router.get("", response_model=list[QueryResponse], status_code=status.HTTP_200_OK)
async def get_all_chat(db:DbSession):
    result = await db.execute(select(models.Response).options(selectinload(models.Response.user)))
    responses = result.scalars().all()
    return responses

@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(db: DbSession, query_id: int, current_user: CurrentUser):

    result = await db.execute(select(models.Response).where(models.Response.id == query_id, models.Response.user_id == current_user.id))
    target_query = result.scalars().first()

    if not target_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )

    await db.delete(target_query)
    await db.commit()
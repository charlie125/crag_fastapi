from fastapi import status, APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import models
from schemas import QueryResponse, QueryCreate
from capped_crag import capped_main
import asyncio
from auth import CurrentUser
from database import DbSession

router = APIRouter()

@router.post("", response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
async def create_query(query: QueryCreate, db:DbSession, current_user: CurrentUser):

    response = await asyncio.to_thread(capped_main, query.query)
    new_query = models.Query(query=query.query, response=response, user=current_user)

    db.add(new_query)
    await db.commit()

    return new_query


@router.get("", response_model=list[QueryResponse], status_code=status.HTTP_200_OK)
async def get_all_queries(db:DbSession):
    result = await db.execute(select(models.Query).options(selectinload(models.Query.user)))
    queries = result.scalars().all()
    return queries


@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(db: DbSession, query_id: int, current_user: CurrentUser):

    result = await db.execute(select(models.Query).where(models.Query.id == query_id, models.Query.user_id == current_user.id))
    target_query = result.scalars().first()

    if not target_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )

    await db.delete(target_query)
    await db.commit()
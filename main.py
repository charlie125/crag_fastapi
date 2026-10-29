from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import Base, engine
from router import user, query

@asynccontextmanager
async def lifespan(_app:FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

    await engine.dispose()
app = FastAPI(lifespan=lifespan)
app.include_router(user.router, prefix="/api/users", tags=["users"])
app.include_router(query.router, prefix="/api/query", tags=["query"])
from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import engine
from router import user, query

@asynccontextmanager
async def lifespan(_app:FastAPI):
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
app.include_router(user.router, prefix="/api/users", tags=["users"])
app.include_router(query.router, prefix="/api/queries", tags=["queries"])
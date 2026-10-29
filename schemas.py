from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(min_length=0, max_length=100)
    email: EmailStr = Field(min_length=0, max_length=100)

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date_created: datetime



class QueryBase(BaseModel):
    query: str = Field(min_length=1, max_length=500)

class QueryCreate(QueryBase):
    pass

class QueryResponse(QueryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    response: str
    date_created: datetime
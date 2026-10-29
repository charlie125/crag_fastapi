from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String())
    email: Mapped[str] = mapped_column(String())
    password: Mapped[str] = mapped_column(String())
    date_created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    queries: Mapped[list[Response]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Response(Base):
    __tablename__ = "response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text())
    response: Mapped[str] = mapped_column(Text())
    date_created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    user: Mapped[User] = relationship(back_populates="queries")
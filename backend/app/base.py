import uuid
from typing import Type, TypeVar

from fastapi import HTTPException
from sqlalchemy import select

from backend.app.database import Base, DbSession

T = TypeVar("T", bound=Base)


class BaseRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, instance: Base) -> None:
        await self.session.refresh(instance)

    async def get_or_404(self, model: Type[T], id: uuid.UUID, *options) -> T:
        result = await self.session.execute(
            select(model).where(model.id == id).options(*options)
        )
        obj = result.scalars().first()
        if not obj:
            raise HTTPException(status_code=404)
        return obj

    async def assert_owner(self, obj, user, field="user_id"):
        if getattr(obj, field) != user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

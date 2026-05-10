from backend.app.database import Base, DbSession


class BaseRepository:
    def __init__(self, session: DbSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, instance: Base) -> None:
        await self.session.refresh(instance)

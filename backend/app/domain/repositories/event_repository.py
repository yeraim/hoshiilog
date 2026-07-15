from abc import ABC, abstractmethod
from uuid import UUID

from backend.app.domain.entities.event import Event, EventMember


class AbstractEventRepository(ABC):
    @abstractmethod
    async def get_by_id(self, event_id: UUID) -> Event | None: ...

    @abstractmethod
    async def get_list(self, user_id: UUID) -> list[Event]: ...

    @abstractmethod
    async def create(self, event: Event) -> Event: ...

    @abstractmethod
    async def update(self, event: Event) -> Event: ...

    @abstractmethod
    async def delete(self, event_id: UUID) -> None: ...


class AbstractEventMemberRepository(ABC):
    @abstractmethod
    async def get_member(self, user_id: UUID, event_id: UUID) -> EventMember | None: ...

    @abstractmethod
    async def add_member(self, user_id: UUID, event_id: UUID) -> EventMember: ...

    @abstractmethod
    async def remove_member(self, user_id: UUID, event_id: UUID) -> None: ...

from abc import ABC, abstractmethod
from uuid import UUID

from backend.app.domain.entities.wish import Wish


class AbstractWishRepository(ABC):
    @abstractmethod
    async def create(self, wish: Wish) -> Wish: ...

    @abstractmethod
    async def get_by_id(self, wish_id: UUID) -> Wish | None: ...

    @abstractmethod
    async def get_list_by_user(self, user_id: UUID) -> list[Wish]: ...

    @abstractmethod
    async def get_list_by_user_public(self, user_id: UUID) -> list[Wish]: ...

    @abstractmethod
    async def get_list_by_user_friends(self, user_id: UUID) -> list[Wish]: ...

    @abstractmethod
    async def update(self, wish: Wish) -> Wish: ...

    @abstractmethod
    async def delete(self, wish_id: UUID) -> None: ...

    @abstractmethod
    async def reserve(self, wish_id: UUID, reserver_id: UUID) -> Wish: ...

    @abstractmethod
    async def cancel_reservation(self, wish_id: UUID) -> Wish: ...

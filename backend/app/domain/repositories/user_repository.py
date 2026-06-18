from abc import ABC, abstractmethod
from uuid import UUID

from backend.app.domain.entities.user import Follow, User


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_list(self) -> list[User]: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool: ...

    @abstractmethod
    async def change_password(self, user_id: UUID, new_password: bytes) -> User: ...

    @abstractmethod
    async def are_friends(self, user1_id: UUID, user2_id: UUID) -> bool: ...


class AbstractFollowRepository(ABC):
    @abstractmethod
    async def follow_user(
        self, following_user_id: UUID, followed_user_id: UUID
    ) -> Follow: ...

    @abstractmethod
    async def unfollow_user(
        self, following_user_id: UUID, followed_user_id: UUID
    ) -> None: ...

    @abstractmethod
    async def check_followers(
        self, following_user_id: UUID, followed_user_id: UUID
    ) -> bool | None: ...

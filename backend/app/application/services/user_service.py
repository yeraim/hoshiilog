import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt

from backend.app.config import settings
from backend.app.domain.entities.user import User
from backend.app.domain.repositories.user_repository import (
    AbstractFollowRepository,
    AbstractUserRepository,
)
from backend.app.exceptions import AuthenticationError, ConflictError, NotFoundError


class UserService:
    def __init__(self, repository: AbstractUserRepository) -> None:
        self._repository = repository

    def _generate_jwt_token(self, username: str) -> dict[str, str]:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        to_encode: dict[str, Any] = {"sub": username, "exp": expire}
        encoded_jwt = jwt.encode(
            to_encode, str(settings.SECRET_KEY), algorithm=settings.ALGORITHM
        )
        return {"access_token": encoded_jwt, "token_type": "bearer"}

    async def _hash_password(self, password: str) -> bytes:
        loop = asyncio.get_running_loop()
        pw = password.encode()
        salt = await loop.run_in_executor(None, bcrypt.gensalt)
        return await loop.run_in_executor(None, bcrypt.hashpw, pw, salt)

    async def _check_password(self, raw: str, hashed: bytes) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, bcrypt.checkpw, raw.encode(), hashed)

    async def register(self, email: str, name: str, raw_password: str) -> User:
        existing_user = await self._repository.get_by_email(email)
        if existing_user:
            raise ConflictError("Email already registered")

        hashed_password = await self._hash_password(raw_password)
        user = User(email=email, name=name, password=hashed_password)
        return await self._repository.create(user)

    async def login(self, email: str, raw_password: str) -> dict[str, str]:
        user = await self._repository.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        if not await self._check_password(raw_password, user.password):
            raise AuthenticationError("Invalid email or password")

        return self._generate_jwt_token(user.email)

    async def list_users(self) -> list[User]:
        return await self._repository.get_list()

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self._repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def change_password(
        self, user: User, old_password: str, new_password: str
    ) -> User:
        if not await self._check_password(old_password, user.password):
            raise AuthenticationError("Invalid email or password")

        hashed_password = await self._hash_password(new_password)
        return await self._repository.change_password(user.id, hashed_password)


class FollowService:
    def __init__(
        self,
        follow_repo: AbstractFollowRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self._follow_repo = follow_repo
        self._user_repo = user_repo

    async def follow_user(self, following_user: User, followed_user_id: uuid.UUID):
        followed_user = await self._user_repo.get_by_id(followed_user_id)
        if not followed_user:
            raise NotFoundError("User not found")

        if following_user.id == followed_user.id:
            raise ConflictError("You can't follow yourself.")

        is_followed = await self._follow_repo.check_followers(
            following_user.id, followed_user.id
        )
        if is_followed:
            raise ConflictError("You are already followed to this user.")

        await self._follow_repo.follow_user(following_user.id, followed_user.id)

    async def unfollow_user(self, following_user: User, followed_user_id: uuid.UUID):
        followed_user = await self._user_repo.get_by_id(followed_user_id)
        if not followed_user:
            raise NotFoundError("User not found")

        is_followed = await self._follow_repo.check_followers(
            following_user.id, followed_user.id
        )
        if not is_followed:
            raise ConflictError("You are not following this user.")

        await self._follow_repo.unfollow_user(following_user.id, followed_user.id)

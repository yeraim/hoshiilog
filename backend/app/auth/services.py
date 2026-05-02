import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from jose import jwt

from backend.app.auth.models import User
from backend.app.auth.repositories import FollowRepository, UserRepository
from backend.app.config import settings

user_repo = Annotated[UserRepository, Depends(UserRepository)]
follow_repo = Annotated[FollowRepository, Depends(FollowRepository)]


class UserService:
    """Service for user-related business logic."""

    def __init__(self, repo: user_repo):
        self.repo = repo

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

    async def register_new_user(self, email: str, raw_password: str):
        existing_user = await self.repo.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = await self._hash_password(raw_password)
        user = await self.repo.create_user(email, hashed_password)
        await self.repo.commit()
        await self.repo.refresh(user)
        return user

    async def authenticate_user(self, email: str, raw_password: str):
        user = await self.repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not bool(user.is_active):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        if not await self._check_password(raw_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._generate_jwt_token(user.email)

    async def get_users(self):
        return await self.repo.get_users()

    async def get_user(self, user_id: uuid.UUID):
        return await self.repo.get_user(user_id)

    async def change_password(self, user: User, old_password: str, new_password: str):
        if not await self._check_password(old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        hashed_password = await self._hash_password(new_password)
        user = await self.repo.change_password(user, hashed_password)
        await self.repo.commit()
        await self.repo.refresh(user)
        return user


class FollowService:
    def __init__(self, follow_repo: follow_repo, user_repo: user_repo) -> None:
        self.follow_repo = follow_repo
        self.user_repo = user_repo

    async def follow_user(self, following_user: User, followed_user_id: uuid.UUID):
        followed_user = await self.user_repo.get_user(followed_user_id)
        if not followed_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of followed_user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if following_user.id == followed_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You can't follow yourself.",
            )
        is_followed = await self.follow_repo.check_followers(
            following_user, followed_user
        )
        if is_followed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are already followed to this user.",
            )
        await self.follow_repo.follow_user(following_user, followed_user)
        await self.follow_repo.commit()

    async def unfollow_user(self, following_user: User, followed_user_id: uuid.UUID):
        followed_user = await self.user_repo.get_user(followed_user_id)
        if not followed_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of followed_user.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        is_followed = await self.follow_repo.check_followers(
            following_user, followed_user
        )
        if not is_followed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You are not following this user.",
            )
        await self.follow_repo.unfollow_user(following_user, followed_user)
        await self.follow_repo.commit()

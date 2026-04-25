import asyncio
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, cast

import bcrypt
from fastapi import Depends, HTTPException, status
from jose import jwt

from backend.app.auth.repositories import UserRepository
from backend.app.config import settings

UserRepo = Annotated[UserRepository, Depends(UserRepository)]


class UserService:
    """Service for user-related business logic."""

    def __init__(self, repo: UserRepo):
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

        if not await self._check_password(raw_password, cast(bytes, user.password)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._generate_jwt_token(str(user.email))

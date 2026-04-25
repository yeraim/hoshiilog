from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status

from backend.app.auth.repositories import UserRepository

UserRepo = Annotated[UserRepository, Depends(UserRepository)]


class UserService:
    """Service for user-related business logic."""

    def __init__(self, repo: UserRepo):
        self.repo = repo

    def _hash_password(self, password: str):
        """Hash a plaintext password."""

        pw = bytes(password, "utf-8")
        salt = bcrypt.gensalt()

        return bcrypt.hashpw(pw, salt)

    async def register_new_user(self, email: str, raw_password: str):
        """Register a new user with the given email and password."""
        existing_user = await self.repo.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = self._hash_password(raw_password)

        return await self.repo.create_user(email, hashed_password)

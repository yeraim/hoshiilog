from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.app.config import settings
from backend.app.domain.entities.user import User
from backend.app.domain.repositories.user_repository import AbstractUserRepository
from backend.app.infrastructure.database.session import DbSession
from backend.app.infrastructure.repositories.user_repository import (
    SQLAlchemyUserRepository,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_user_repo(session: DbSession) -> AbstractUserRepository:
    return SQLAlchemyUserRepository(session)


UserRepoDep = Annotated[AbstractUserRepository, Depends(get_user_repo)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    repo: UserRepoDep,
) -> User:
    try:
        payload = jwt.decode(
            token, str(settings.SECRET_KEY), algorithms=[settings.ALGORITHM]
        )
        email: str | None = payload.get("sub")
        if email is None:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await repo.get_by_email(email)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user

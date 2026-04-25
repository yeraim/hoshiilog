from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from backend.app.auth.repositories import UserRepository
from backend.app.config import settings

oauth2_cheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
user_repo = Annotated[UserRepository, Depends(UserRepository)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_cheme)], repo: user_repo
):
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

    user = await repo.get_user_by_email(email)
    if user is None or not bool(user.is_active):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user

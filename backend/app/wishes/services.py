import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.app.auth.models import User
from backend.app.auth.repositories import UserRepository
from backend.app.wishes.models import WishType
from backend.app.wishes.repositories import WishRepository
from backend.app.wishes.schemas import WishCreate, WishUpdate

wish_repo = Annotated[WishRepository, Depends(WishRepository)]
user_repo = Annotated[UserRepository, Depends(UserRepository)]


class WishService:
    def __init__(self, wish_repo: wish_repo, user_repo: user_repo):
        self.wish_repo = wish_repo
        self.user_repo = user_repo

    async def create(self, current_user: User, data: WishCreate):
        wish = await self.wish_repo.create(current_user, data)
        # add title duplicates validation

        await self.wish_repo.commit()
        await self.wish_repo.refresh(wish)
        return wish

    async def get_by_id(self, wish_id: uuid.UUID):
        wish = await self.wish_repo.get_by_id(wish_id)
        if not wish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of wish",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return wish

    async def get_by_user(self, current_user: User, user_id: uuid.UUID | None = None):
        target_id = user_id or current_user.id
        if user_id and user_id != current_user.id:
            target_user: User = await self.user_repo.get_user(user_id)

            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invalid id of user",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if (
                current_user in target_user.followers
                and current_user in target_user.subscriptions
            ):
                return await self.wish_repo.get_by_user_friends(target_id)

            return await self.wish_repo.get_by_user_public(target_id)

        return await self.wish_repo.get_by_user(target_id)

    async def update(self, wish_id: uuid.UUID, current_user: User, data: WishUpdate):
        wish = await self.wish_repo.get_by_id(wish_id)

        if not wish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of wish",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if wish.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
            )

        wish = await self.wish_repo.update(wish, data)
        await self.wish_repo.commit()
        await self.wish_repo.refresh(wish)
        return wish

    async def delete(self, wish_id: uuid.UUID, current_user: User):
        wish = await self.wish_repo.get_by_id(wish_id)

        if not wish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of wish",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if wish.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied"
            )

        await self.wish_repo.delete(wish)
        await self.wish_repo.commit()

    async def reserve(self, wish_id: uuid.UUID, reserver: User):
        wish = await self.wish_repo.get_by_id(wish_id)

        if not wish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of wish",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if wish.user_id == reserver.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can't reserve your own wish",
            )

        if wish.type == WishType.PERSONAL:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't reserve other person's private wish",
            )

        if wish.reserver:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wish is already reserved",
            )

        wish = await self.wish_repo.reserve(wish, reserver)
        await self.wish_repo.commit()
        await self.wish_repo.refresh(wish)
        return wish

    async def cancel_reservation(self, wish_id: uuid.UUID, reserver: User):
        wish = await self.wish_repo.get_by_id(wish_id)

        if not wish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of wish",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not wish.reserver:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wish is not reserved",
            )
        if wish.reserver != reserver:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't unreserve someone's reservation",
            )

        wish = await self.wish_repo.cancel_reservation(wish)
        await self.wish_repo.commit()
        await self.wish_repo.refresh(wish)
        return wish

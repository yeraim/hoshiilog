import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.app.auth.models import User
from backend.app.wishes.models import WishType
from backend.app.wishes.repositories import WishRepository
from backend.app.wishes.schemas import WishCreate, WishUpdate

wish_repo = Annotated[WishRepository, Depends(WishRepository)]


class WishService:
    def __init__(self, repo: wish_repo):
        self.repo = repo

    async def create(self, current_user: User, data: WishCreate):
        wish = await self.repo.create(current_user, data)
        # add title duplicates validation

        await self.repo.commit()
        await self.repo.refresh(wish)
        return wish

    async def get_by_id(self, wish_id: uuid.UUID):
        wish = await self.repo.get_by_id(wish_id)
        if not wish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid id of wish",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return wish

    async def get_all(self):
        return await self.repo.get_all()

    async def update(self, wish_id: uuid.UUID, current_user: User, data: WishUpdate):
        wish = await self.repo.get_by_id(wish_id)

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

        wish = await self.repo.update(wish, data)
        await self.repo.commit()
        await self.repo.refresh(wish)
        return wish

    async def delete(self, wish_id: uuid.UUID, current_user: User):
        wish = await self.repo.get_by_id(wish_id)

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

        await self.repo.delete(wish)
        await self.repo.commit()

    async def reserve(self, wish_id: uuid.UUID, reserver: User):
        wish = await self.repo.get_by_id(wish_id)

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

        wish = await self.repo.reserve(wish, reserver)
        await self.repo.commit()
        await self.repo.refresh(wish)
        return wish

    async def cancel_reservation(self, wish_id: uuid.UUID, reserver: User):
        wish = await self.repo.get_by_id(wish_id)

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

        wish = await self.repo.cancel_reservation(wish)
        await self.repo.commit()
        await self.repo.refresh(wish)
        return wish

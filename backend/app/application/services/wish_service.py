import uuid

from backend.app.domain.entities.user import User
from backend.app.domain.entities.wish import Wish, WishCreate, WishType, WishUpdate
from backend.app.domain.repositories.user_repository import AbstractUserRepository
from backend.app.domain.repositories.wish_repository import AbstractWishRepository
from backend.app.exceptions import ConflictError, NotFoundError, PermissionDeniedError


class WishService:
    def __init__(
        self,
        wish_repo: AbstractWishRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self._wish_repo = wish_repo
        self._user_repo = user_repo

    async def create(self, current_user: User, data: WishCreate) -> Wish:
        wish = Wish(
            user_id=current_user.id,
            title=data.title,
            price=data.price,
            body=data.body,
            link=data.link,
            image_url=data.image_url,
            status=data.status,
            type=data.type,
            category=data.category,
        )
        return await self._wish_repo.create(wish)

    async def get_by_id(self, wish_id: uuid.UUID, current_user: User) -> Wish:
        wish = await self._wish_repo.get_by_id(wish_id)
        if not wish:
            raise NotFoundError("Wish not found")

        if wish.user_id != current_user.id:
            if wish.type == WishType.PERSONAL:
                raise PermissionDeniedError("Can't access data")

            if wish.type == WishType.FRIENDS_ONLY:
                are_friends = await self._user_repo.are_friends(
                    current_user.id, wish.user_id
                )
                if not are_friends:
                    raise PermissionDeniedError("Can't access data")

        return wish

    async def get_list_by_user(
        self, current_user: User, user_id: uuid.UUID | None = None
    ) -> list[Wish]:
        target_id = user_id or current_user.id

        if user_id and user_id != current_user.id:
            are_friends = await self._user_repo.are_friends(current_user.id, user_id)
            if are_friends:
                return await self._wish_repo.get_list_by_user_friends(target_id)
            return await self._wish_repo.get_list_by_user_public(target_id)

        return await self._wish_repo.get_list_by_user(target_id)

    async def update(
        self, wish_id: uuid.UUID, current_user: User, data: WishUpdate
    ) -> Wish:
        wish = await self._wish_repo.get_by_id(wish_id)
        if not wish:
            raise NotFoundError("Wish not found")
        if wish.user_id != current_user.id:
            raise PermissionDeniedError("Can't access data")

        if data.title is not None:
            wish.title = data.title
        if data.price is not None:
            wish.price = data.price
        if data.body is not None:
            wish.body = data.body
        if data.link is not None:
            wish.link = data.link
        if data.image_url is not None:
            wish.image_url = data.image_url
        if data.status is not None:
            wish.status = data.status
        if data.type is not None:
            wish.type = data.type
        if data.category is not None:
            wish.category = data.category

        return await self._wish_repo.update(wish)

    async def delete(self, wish_id: uuid.UUID, current_user: User) -> None:
        wish = await self._wish_repo.get_by_id(wish_id)
        if not wish:
            raise NotFoundError("Wish not found")
        if wish.user_id != current_user.id:
            raise PermissionDeniedError("Can't access data")

        await self._wish_repo.delete(wish_id)

    async def reserve(self, wish_id: uuid.UUID, reserver: User) -> Wish:
        wish = await self._wish_repo.get_by_id(wish_id)
        if not wish:
            raise NotFoundError("Wish not found")

        if wish.user_id == reserver.id:
            raise ConflictError("You can't reserve your own wish")

        if wish.type == WishType.PERSONAL:
            raise PermissionDeniedError("You can't reserve other person's private wish")

        if wish.reserved_by_id is not None:
            raise ConflictError("Wish is already reserved")

        return await self._wish_repo.reserve(wish_id, reserver.id)

    async def cancel_reservation(self, wish_id: uuid.UUID, reserver: User) -> Wish:
        wish = await self._wish_repo.get_by_id(wish_id)
        if not wish:
            raise NotFoundError("Wish not found")

        if wish.reserved_by_id is None:
            raise ConflictError("Wish is not reserved")

        if wish.reserved_by_id != reserver.id:
            raise PermissionDeniedError("You can't unreserve someone's reservation")

        return await self._wish_repo.cancel_reservation(wish_id)

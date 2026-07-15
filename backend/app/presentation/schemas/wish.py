import uuid
from decimal import Decimal

from pydantic import AnyUrl, BaseModel, ConfigDict

from backend.app.domain.entities.wish import WishCategory, WishStatus, WishType
from backend.app.presentation.schemas.user import UserRead


class WishBase(BaseModel):
    body: str | None = None
    link: AnyUrl | None = None
    image_url: AnyUrl | None = None


class WishCreate(WishBase):
    title: str
    status: WishStatus
    type: WishType
    category: WishCategory
    price: Decimal


class WishUpdate(WishBase):
    title: str | None = None
    status: WishStatus | None = None
    type: WishType | None = None
    category: WishCategory | None = None
    price: Decimal | None = None


class WishRead(WishBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: WishStatus
    type: WishType
    category: WishCategory
    price: Decimal


class WishReserveRead(WishRead):
    reserver: UserRead | None = None

import uuid
from decimal import Decimal

from pydantic import AnyUrl, BaseModel

from backend.app.wishes.models import WishCategory, WishStatus, WishType


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
    id: uuid.UUID
    title: str
    status: WishStatus
    type: WishType
    category: WishCategory
    price: Decimal

    # model_config = ConfigDict(from_attributes=True)

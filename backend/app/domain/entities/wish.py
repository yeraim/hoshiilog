import datetime
import decimal
import enum
from dataclasses import dataclass, field
from uuid import UUID, uuid4


class WishStatus(enum.Enum):
    ARCHIVED = 0
    ACTIVE = 1
    DONE = 3


class WishType(enum.Enum):
    PERSONAL = 0
    FRIENDS_ONLY = 1
    PUBLIC = 2


class WishCategory(enum.Enum):
    LOW = 0
    MODERATE = 1
    HIGH = 2


@dataclass
class Wish:
    user_id: UUID
    title: str
    price: decimal.Decimal
    id: UUID = field(default_factory=uuid4)
    body: str | None = None
    link: str | None = None
    image_url: str | None = None
    status: WishStatus = WishStatus.ACTIVE
    type: WishType = WishType.PERSONAL
    category: WishCategory = WishCategory.LOW
    reserved_by_id: UUID | None = None
    reserved_at: datetime.datetime | None = None


@dataclass
class WishCreate:
    title: str
    price: decimal.Decimal
    status: WishStatus
    type: WishType
    category: WishCategory
    body: str | None = None
    link: str | None = None
    image_url: str | None = None


@dataclass
class WishUpdate:
    title: str | None = None
    price: decimal.Decimal | None = None
    status: WishStatus | None = None
    type: WishType | None = None
    category: WishCategory | None = None
    body: str | None = None
    link: str | None = None
    image_url: str | None = None

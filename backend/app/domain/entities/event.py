import enum
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4


class EventStatus(enum.Enum):
    PLANNING = 0
    ACTIVE = 1
    COMPLETED = 2
    CANCELLED = 3


@dataclass
class Event:
    user_id: UUID
    title: str
    price_limit: Decimal
    id: UUID = field(default_factory=uuid4)
    description: str | None = None
    image_url: str | None = None
    status: EventStatus = EventStatus.PLANNING


@dataclass
class EventMember:
    event_id: UUID
    user_id: UUID
    id: UUID = field(default_factory=uuid4)
    target_user_id: UUID | None = None


@dataclass
class EventCreate:
    title: str
    price_limit: Decimal
    status: EventStatus
    description: str | None = None
    image_url: str | None = None


@dataclass
class EventUpdate:
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    status: EventStatus | None = None
    price_limit: Decimal | None = None

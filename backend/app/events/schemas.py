import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import AnyUrl, BaseModel, Field

from backend.app.auth.schemas import UserRead
from backend.app.events.models import EventStatus

PriceDecimal = Annotated[Decimal, Field(max_digits=10, decimal_places=2, ge=0)]


class EventBase(BaseModel):
    title: str
    description: str | None = None
    image_url: AnyUrl | None = None
    status: EventStatus
    price_limit: PriceDecimal


class EventRead(EventBase):
    id: uuid.UUID
    owner: UserRead


class EventCreate(EventBase): ...


class EventUpdate(EventBase):
    title: str | None = None
    description: str | None = None
    image_url: AnyUrl | None = None
    status: EventStatus | None = None
    price_limit: PriceDecimal | None = None

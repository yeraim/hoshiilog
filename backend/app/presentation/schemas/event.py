import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import AnyUrl, BaseModel, ConfigDict, Field

from backend.app.domain.entities.event import EventStatus

PriceDecimal = Annotated[Decimal, Field(max_digits=10, decimal_places=2, ge=0)]


class EventBase(BaseModel):
    title: str
    description: str | None = None
    image_url: AnyUrl | None = None
    status: EventStatus
    price_limit: PriceDecimal


class EventRead(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID


class EventCreate(EventBase): ...


class EventUpdate(EventBase):
    title: str | None = None
    description: str | None = None
    image_url: AnyUrl | None = None
    status: EventStatus | None = None
    price_limit: PriceDecimal | None = None

import enum
import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.auth.models import User
from backend.app.database import Base
from backend.app.mixins import TimeStampMixin


class EventStatus(enum.Enum):
    PLANNING = 0
    ACTIVE = 1
    COMPLETED = 2
    CANCELLED = 3


class Event(Base, TimeStampMixin):
    __repr_attrs__ = ["id"]
    __table_args__ = (UniqueConstraint("title", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id")
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), default=EventStatus.PLANNING
    )
    price_limit: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))

    owner: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="owned_events"
    )


class EventMember(Base, TimeStampMixin):
    __repr_attrs__ = ["id"]
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id"),
        comment="The person to give a gift to",
    )

    event: Mapped["Event"] = relationship("Event", foreign_keys=[event_id])
    member: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    target_member: Mapped["User | None"] = relationship(
        "User", foreign_keys=[target_user_id]
    )

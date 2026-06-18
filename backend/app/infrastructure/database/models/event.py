import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.entities.event import Event, EventMember, EventStatus
from backend.app.infrastructure.database.mixins import TimeStampMixin
from backend.app.infrastructure.database.session import Base


class EventModel(Base, TimeStampMixin):
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

    owner = relationship(
        "UserModel", foreign_keys=[user_id], back_populates="owned_events"
    )

    def to_entity(self) -> Event:
        return Event(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            description=self.description,
            image_url=self.image_url,
            status=self.status,
            price_limit=self.price_limit,
        )

    @classmethod
    def from_entity(cls, event: Event) -> "EventModel":
        return cls(
            id=event.id,
            user_id=event.user_id,
            title=event.title,
            description=event.description,
            image_url=event.image_url,
            status=event.status,
            price_limit=event.price_limit,
        )


class EventMemberModel(Base, TimeStampMixin):
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

    event = relationship("EventModel", foreign_keys=[event_id])
    member = relationship("UserModel", foreign_keys=[user_id])
    target_member = relationship("UserModel", foreign_keys=[target_user_id])

    def to_entity(self) -> EventMember:
        return EventMember(
            id=self.id,
            event_id=self.event_id,
            user_id=self.user_id,
            target_user_id=self.target_user_id,
        )

    @classmethod
    def from_entity(cls, member: EventMember) -> "EventMemberModel":
        return cls(
            id=member.id,
            event_id=member.event_id,
            user_id=member.user_id,
            target_user_id=member.target_user_id,
        )

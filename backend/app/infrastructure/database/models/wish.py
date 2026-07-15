import datetime
import decimal
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.entities.wish import Wish, WishCategory, WishStatus, WishType
from backend.app.infrastructure.database.mixins import TimeStampMixin
from backend.app.infrastructure.database.session import Base


class WishModel(Base, TimeStampMixin):
    __repr_attrs__ = ["id"]
    __table_args__ = (UniqueConstraint("title", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id")
    )
    reserved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id")
    )

    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(String(255))
    link: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[WishStatus] = mapped_column(
        Enum(WishStatus), default=WishStatus.ACTIVE
    )
    type: Mapped[WishType] = mapped_column(Enum(WishType), default=WishType.PERSONAL)
    category: Mapped[WishCategory] = mapped_column(
        Enum(WishCategory), default=WishCategory.LOW
    )
    price: Mapped[decimal.Decimal] = mapped_column(Numeric)
    reserved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    owner = relationship("UserModel", foreign_keys=[user_id], back_populates="wishes")
    reserver = relationship(
        "UserModel", foreign_keys=[reserved_by_id], back_populates="reserved_wishes"
    )

    def to_entity(self) -> Wish:
        return Wish(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            price=self.price,
            body=self.body,
            link=self.link,
            image_url=self.image_url,
            status=self.status,
            type=self.type,
            category=self.category,
            reserved_by_id=self.reserved_by_id,
            reserved_at=self.reserved_at,
        )

    @classmethod
    def from_entity(cls, wish: Wish) -> "WishModel":
        return cls(
            id=wish.id,
            user_id=wish.user_id,
            title=wish.title,
            price=wish.price,
            body=wish.body,
            link=wish.link,
            image_url=wish.image_url,
            status=wish.status,
            type=wish.type,
            category=wish.category,
            reserved_by_id=wish.reserved_by_id,
            reserved_at=wish.reserved_at,
        )

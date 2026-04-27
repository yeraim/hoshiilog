import datetime
import decimal
import enum
import uuid

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.auth.models import User
from backend.app.database import Base
from backend.app.mixins import TimeStampMixin


class WishStatus(enum.Enum):
    ARCHIVED = 0
    ACTIVE = 1
    RESERVED = 2
    DONE = 3


class WishType(enum.Enum):
    PERSONAL = 0
    FRIENDS_ONLY = 1
    PUBLIC = 2


class WishCategory(enum.Enum):
    LOW = 0
    MODERATE = 1
    HIGH = 2


class Wish(Base, TimeStampMixin):
    __repr_attrs__ = ["id"]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    reserved_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    body: Mapped[str] = mapped_column(String(255), nullable=False)
    link: Mapped[str] = mapped_column(String(255), nullable=False)
    image_url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[WishStatus] = mapped_column(
        Enum(WishStatus), default=WishStatus.ACTIVE
    )
    type: Mapped[WishType] = mapped_column(
        Enum(WishType), default=WishType.PERSONAL
    )
    category: Mapped[WishCategory] = mapped_column(
        Enum(WishCategory), default=WishCategory.LOW
    )
    price: Mapped[decimal.Decimal] = mapped_column(Numeric, nullable=False)
    reserved_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    reserved_by: Mapped["User"] = relationship("User", foreign_keys=[reserved_by_id])

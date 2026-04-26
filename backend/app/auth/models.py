import uuid

from sqlalchemy import Boolean, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.mixins import TimeStampMixin


class User(Base, TimeStampMixin):
    __repr_attrs__ = ["id", "email"]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    friends: Mapped[list["User"]] = relationship(
        "User",
        secondary="friends",
        primaryjoin="User.id==Friends.person_id",
        secondaryjoin="User.id==Friends.friend_id",
    )


class Friends(Base, TimeStampMixin):
    __repr_attrs__ = ["id"]
    __table_args__ = (UniqueConstraint("person_id", "friend_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    friend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )

    person: Mapped["User"] = relationship("User", foreign_keys=[person_id])
    friend: Mapped["User"] = relationship("User", foreign_keys=[friend_id])

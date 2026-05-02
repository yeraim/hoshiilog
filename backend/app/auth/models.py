import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base
from backend.app.mixins import TimeStampMixin

if TYPE_CHECKING:
    from backend.app.wishes.models import Wish


class User(Base, TimeStampMixin):
    __repr_attrs__ = ["id", "email"]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    wishes: Mapped[list["Wish"]] = relationship(
        "Wish", back_populates="owner", foreign_keys="[Wish.user_id]"
    )
    reserved_wishes: Mapped[list["Wish"]] = relationship(
        "Wish", back_populates="reserver", foreign_keys="[Wish.reserved_by_id]"
    )

    following_relationships = relationship(
        "Follow",
        back_populates="following_user",
        foreign_keys="[Follow.following_user_id]",
    )
    follower_relationships = relationship(
        "Follow",
        back_populates="followed_user",
        foreign_keys="[Follow.followed_user_id]",
    )

    subscriptions: AssociationProxy[list["User"]] = association_proxy(
        target_collection="following_relationships",
        attr="followed_user",
        creator=lambda user_obj: Follow(followed_user=user_obj),  # type: ignore
    )

    followers: AssociationProxy[list["User"]] = association_proxy(
        target_collection="follower_relationships", attr="following_user"
    )


class Follow(Base, TimeStampMixin):
    __repr_attrs__ = ["id"]
    __table_args__ = (UniqueConstraint("following_user_id", "followed_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    following_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    followed_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )

    following_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[following_user_id],
        back_populates="following_relationships",
    )
    followed_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[followed_user_id],
        back_populates="follower_relationships",
    )

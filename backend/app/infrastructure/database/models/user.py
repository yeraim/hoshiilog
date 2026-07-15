import uuid

from sqlalchemy import (
    Boolean,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain.entities.user import Follow, User
from backend.app.infrastructure.database.mixins import TimeStampMixin
from backend.app.infrastructure.database.session import Base


class UserModel(Base, TimeStampMixin):
    __repr_attrs__ = ["id", "email"]

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password: Mapped[bytes] = mapped_column(LargeBinary)
    name: Mapped[str] = mapped_column(String(100))
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    pfp: Mapped[str | None] = mapped_column(String(255))

    owned_events = relationship(
        "EventModel", back_populates="owner", foreign_keys="[EventModel.user_id]"
    )

    wishes = relationship(
        "WishModel", back_populates="owner", foreign_keys="[WishModel.user_id]"
    )
    reserved_wishes = relationship(
        "WishModel",
        back_populates="reserver",
        foreign_keys="[WishModel.reserved_by_id]",
    )

    following_relationships = relationship(
        "FollowModel",
        back_populates="following_user",
        foreign_keys="[FollowModel.following_user_id]",
    )
    follower_relationships = relationship(
        "FollowModel",
        back_populates="followed_user",
        foreign_keys="[FollowModel.followed_user_id]",
    )

    subscriptions = association_proxy(
        target_collection="following_relationships",
        attr="followed_user",
        creator=lambda user_obj: FollowModel(followed_user=user_obj),  # type: ignore  # noqa: F821
    )

    followers = association_proxy(
        target_collection="follower_relationships", attr="following_user"
    )

    def to_entity(self) -> User:
        unloaded = sa_inspect(self).unloaded
        return User(
            id=self.id,
            name=self.name,
            email=self.email,
            password=self.password,
            is_staff=self.is_staff,
            is_active=self.is_active,
            pfp=self.pfp,
            subscriptions=[
                r.followed_user.to_entity() for r in self.following_relationships
            ]
            if "following_relationships" not in unloaded
            else [],
            followers=[
                r.following_user.to_entity() for r in self.follower_relationships
            ]
            if "follower_relationships" not in unloaded
            else [],
        )

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            password=user.password,
            is_staff=user.is_staff,
            is_active=user.is_active,
            pfp=user.pfp,
        )


class FollowModel(Base, TimeStampMixin):
    __repr_attrs__ = ["id"]
    __table_args__ = (UniqueConstraint("following_user_id", "followed_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    following_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id")
    )
    followed_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id")
    )

    following_user = relationship(
        "UserModel",
        foreign_keys=[following_user_id],
        back_populates="following_relationships",
    )
    followed_user = relationship(
        "UserModel",
        foreign_keys=[followed_user_id],
        back_populates="follower_relationships",
    )

    def to_entity(self) -> Follow:
        return Follow(
            id=self.id,
            following_user_id=self.following_user_id,
            followed_user_id=self.followed_user_id,
        )

    @classmethod
    def from_entity(cls, follow: Follow) -> "FollowModel":
        return cls(
            id=follow.id,
            following_user_id=follow.following_user_id,
            followed_user_id=follow.followed_user_id,
        )

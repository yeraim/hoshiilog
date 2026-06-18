from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class User:
    name: str
    email: str
    id: UUID = field(default_factory=uuid4)
    password: bytes = field(default=b"")
    is_staff: bool = False
    is_active: bool = True
    pfp: str | None = None
    subscriptions: list["User"] = field(default_factory=list)
    followers: list["User"] = field(default_factory=list)


@dataclass
class Follow:
    following_user_id: UUID
    followed_user_id: UUID
    id: UUID = field(default_factory=uuid4)

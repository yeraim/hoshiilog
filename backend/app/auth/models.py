import uuid

from sqlalchemy import Boolean, Column, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.database import Base
from backend.app.mixins import TimeStampMixin


class User(Base, TimeStampMixin):
    __repr_attrs__ = ["id", "email"]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(LargeBinary, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

import uuid

from sqlalchemy import Column, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID

from backend.app.database import Base
from backend.app.mixins import TimeStampMixin


class User(Base, TimeStampMixin):
    __repr_attrs__ = ["id", "username"]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True)
    password = Column(LargeBinary(255), nullable=False)

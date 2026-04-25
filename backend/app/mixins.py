from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, event, func
from sqlalchemy.orm import Mapper


class TimeStampMixin(object):
    """Timestamping mixin for created_at and updated_at fields."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @staticmethod
    def _updated_at(mapper: Mapper[Any], connection: Any, target: Any):
        """Updates the updated_at field to the current UTC time."""
        target.updated_at = datetime.now(timezone.utc)

    @classmethod
    def __declare_last__(cls):
        """Registers the before_update event to update the updated_at field."""
        event.listen(cls, "before_update", cls._updated_at)

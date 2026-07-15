"""Pydantic models for the cross-marketplace crawler.

These models double as the wire format for two hops:
  arq worker --(JSON)--> Redis pub/sub --(JSON)--> WebSocket client

`JobEvent` is the envelope that actually travels over both hops. `ProductInfo`
and `MatchResult` are the payloads it carries.
"""

from typing import Literal

from pydantic import BaseModel, HttpUrl

SourceMarketplace = Literal["wb", "kaspi", "ozon"]

JobEventType = Literal["source_parsed", "match_found", "job_done", "job_error"]

MatchStatus = Literal["ok", "not_found", "error"]


class SearchRequest(BaseModel):
    url: HttpUrl


class ProductInfo(BaseModel):
    marketplace: SourceMarketplace
    url: HttpUrl
    title: str
    price: float | None = None
    currency: str | None = None
    image_url: str | None = None
    external_id: str | None = None
    brand: str | None = None
    # Unmapped fields kept for debugging. Excluded from client-facing payloads
    # by default (see `to_client()` / the `exclude` used when publishing).
    raw: dict | None = None

    def to_client(self) -> "ProductInfo":
        """Return a copy safe to send to the client (drops `raw`)."""
        return self.model_copy(update={"raw": None})


class MatchResult(BaseModel):
    """One result per *target* marketplace searched for a given source product.

    A job over a WB source link produces two of these (kaspi + ozon); the
    source marketplace never searches itself.
    """

    source: ProductInfo
    matches: list[ProductInfo]
    marketplace: SourceMarketplace
    status: MatchStatus
    error: str | None = None

    def to_client(self) -> "MatchResult":
        """Return a copy safe to send to the client (drops all `raw` fields)."""
        return self.model_copy(
            update={
                "source": self.source.to_client(),
                "matches": [m.to_client() for m in self.matches],
            }
        )


class JobEvent(BaseModel):
    """Envelope published to Redis channel `job:{job_id}` and forwarded over WS."""

    job_id: str
    event: JobEventType
    data: ProductInfo | MatchResult | None = None
    error: str | None = None

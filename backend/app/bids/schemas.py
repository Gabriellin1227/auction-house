from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BidCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_cents: int = Field(gt=0, le=10**12, strict=True)


class BidRead(BaseModel):
    id: UUID
    bidder_public_id: UUID
    sequence: int
    amount_cents: int
    accepted_at: datetime


class BidAccepted(BidRead):
    lot_id: UUID
    version: int
    ends_at: datetime
    extended: bool

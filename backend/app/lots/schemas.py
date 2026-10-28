from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class LotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    external_item_id: int = Field(gt=0)
    category: str = "fine-art"
    opening_bid_cents: int = Field(gt=0, strict=True, le=10**12)
    min_increment_cents: int = Field(gt=0, strict=True, le=10**12)
    starts_at: AwareDatetime
    ends_at: AwareDatetime


class LotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str | None = None
    opening_bid_cents: int | None = Field(default=None, gt=0, strict=True, le=10**12)
    min_increment_cents: int | None = Field(default=None, gt=0, strict=True, le=10**12)
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None


class LotRead(BaseModel):
    id: str
    number: str
    title: str
    category: str
    categoryName: str
    image: str
    currentBid: int
    bids: int
    endsAt: int
    startsAt: int
    status: str
    increment: int
    sourceUrl: str
    attributes: dict
    leaderPublicId: str | None = None
    version: int = 0

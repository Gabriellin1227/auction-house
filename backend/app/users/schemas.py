from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class Role(StrEnum):
    AUCTIONEER = "auctioneer"
    BIDDER = "bidder"


class ProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class UserCreate(ProfileFields):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr = Field(max_length=320)
    password: SecretStr = Field(min_length=8, max_length=128)
    role: Role = Role.BIDDER


class UserUpdate(ProfileFields):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = Field(default=None, max_length=320)

    @field_validator("name", "email", mode="before")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    public_id: UUID
    name: str
    email: str
    role: Role
    active: bool
    created_at: datetime

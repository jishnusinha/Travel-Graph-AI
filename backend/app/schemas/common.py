from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, Generic, Optional, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

T = TypeVar("T")

_EMAIL_RE = re.compile(r"^[^@\s]+@[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$")


def _validate_email(value: str) -> str:
    """Syntax-only check, lower-cased.

    Deliberately not `EmailStr`: email-validator rejects reserved TLDs such as `.local`, which
    would make the seeded `demo@travelgraph.local` accounts impossible to sign in with.
    """
    value = (value or "").strip().lower()
    if len(value) > 320 or not _EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address")
    return value


LocalEmail = Annotated[str, AfterValidator(_validate_email)]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageOut(APIModel):
    message: str


class ErrorOut(APIModel):
    detail: str
    code: Optional[str] = None


class Paginated(APIModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20


class HealthOut(APIModel):
    status: str
    ai_mode: str
    openai_configured: bool
    database: str
    version: str
    timestamp: datetime

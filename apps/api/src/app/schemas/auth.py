from pydantic import BaseModel
from typing import Optional


class TelegramInitRequest(BaseModel):
    init_data: str


class TelegramWidgetRequest(BaseModel):
    """Data from Telegram Login Widget callback."""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

    model_config = {"extra": "allow"}


class TelegramUserPayload(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    photo_url: str | None = None


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TelegramUserPayload

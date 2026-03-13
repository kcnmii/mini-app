from pydantic import BaseModel


class TelegramInitRequest(BaseModel):
    init_data: str


class TelegramUserPayload(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TelegramUserPayload

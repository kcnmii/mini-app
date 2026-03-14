from fastapi import APIRouter

from app.modules.auth.service import TelegramAuthService
from app.schemas.auth import TelegramAuthResponse, TelegramInitRequest, TelegramWidgetRequest

router = APIRouter(prefix="/auth/telegram", tags=["auth"])
service = TelegramAuthService()


@router.post("/init", response_model=TelegramAuthResponse)
async def auth_telegram_init(payload: TelegramInitRequest) -> TelegramAuthResponse:
    """Authenticate via Telegram Mini App initData."""
    return service.build_auth_response(payload.init_data)


@router.post("/widget", response_model=TelegramAuthResponse)
async def auth_telegram_widget(payload: TelegramWidgetRequest) -> TelegramAuthResponse:
    """Authenticate via Telegram Login Widget data."""
    return service.build_widget_auth_response(payload.model_dump(exclude_unset=True, exclude_none=True))


@router.get("/bot-name")
async def get_bot_name():
    """Return the configured Telegram bot username for the login widget."""
    from app.core.config import settings
    return {"bot_name": settings.telegram_bot_username}

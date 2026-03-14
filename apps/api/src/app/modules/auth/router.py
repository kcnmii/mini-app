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
    return service.build_widget_auth_response(payload.model_dump())

from fastapi import APIRouter

from app.modules.auth.service import TelegramAuthService
from app.schemas.auth import TelegramAuthResponse, TelegramInitRequest

router = APIRouter(prefix="/auth/telegram", tags=["auth"])
service = TelegramAuthService()


@router.post("/init", response_model=TelegramAuthResponse)
async def auth_telegram_init(payload: TelegramInitRequest) -> TelegramAuthResponse:
    return service.build_auth_response(payload.init_data)

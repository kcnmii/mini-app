from __future__ import annotations

import hashlib
import hmac
import json
from time import time
from urllib.parse import parse_qsl

import jwt
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.auth import TelegramAuthResponse, TelegramUserPayload


class TelegramAuthService:
    max_age_seconds = 24 * 60 * 60

    # ── Mini App initData validation ──
    def validate_init_data(self, init_data: str) -> dict[str, str]:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)

        if not received_hash:
            raise HTTPException(status_code=400, detail="missing_hash")

        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(pairs.items(), key=lambda item: item[0])
        )
        secret_key = hmac.new(
            b"WebAppData",
            settings.telegram_bot_token.encode(),
            hashlib.sha256,
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            raise HTTPException(status_code=401, detail="invalid_init_data")

        auth_date = int(pairs.get("auth_date", "0"))
        if auth_date and abs(int(time()) - auth_date) > self.max_age_seconds:
            raise HTTPException(status_code=401, detail="expired_init_data")

        return pairs

    # ── Login Widget validation (different HMAC scheme!) ──
    def validate_widget_data(self, data: dict) -> dict:
        """
        Telegram Login Widget uses a different validation scheme:
        secret_key = SHA256(bot_token)   ← NOT HMAC!
        check_string = sorted key=value joined by \\n (excluding 'hash')
        expected = HMAC-SHA256(check_string, secret_key)
        """
        received_hash = data.get("hash")
        if not received_hash:
            raise HTTPException(status_code=400, detail="missing_hash")

        check_data = {k: v for k, v in data.items() if k != "hash"}
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(check_data.items())
        )

        secret_key = hashlib.sha256(settings.telegram_bot_token.encode()).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, str(received_hash)):
            raise HTTPException(status_code=401, detail="invalid_widget_data")

        auth_date = int(data.get("auth_date", "0"))
        if auth_date and abs(int(time()) - auth_date) > self.max_age_seconds:
            raise HTTPException(status_code=401, detail="expired_widget_data")

        return check_data

    # ── Build response for Mini App ──
    def build_auth_response(self, init_data: str) -> TelegramAuthResponse:
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=500, detail="telegram_bot_token_missing")

        payload = self.validate_init_data(init_data)
        user_raw = payload.get("user")
        if not user_raw:
            raise HTTPException(status_code=400, detail="missing_user")

        try:
            user_data = json.loads(user_raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid_user_payload") from exc

        user = TelegramUserPayload.model_validate(user_data)
        token = jwt.encode(
            {"sub": str(user.id), "username": user.username},
            settings.jwt_secret,
            algorithm="HS256",
        )
        return TelegramAuthResponse(access_token=token, user=user)

    # ── Build response for Login Widget ──
    def build_widget_auth_response(self, data: dict) -> TelegramAuthResponse:
        if not settings.telegram_bot_token:
            raise HTTPException(status_code=500, detail="telegram_bot_token_missing")

        self.validate_widget_data(data)

        user = TelegramUserPayload(
            id=int(data["id"]),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            username=data.get("username"),
        )

        token = jwt.encode(
            {"sub": str(user.id), "username": user.username},
            settings.jwt_secret,
            algorithm="HS256",
        )
        return TelegramAuthResponse(access_token=token, user=user)

"""Dependency that extracts the current Telegram user_id from the JWT token."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request

from app.core.config import settings


def get_current_user_id(request: Request) -> int:
    """Extract and validate user_id from the Authorization: Bearer <token> header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_token")

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = int(payload["sub"])
        return user_id
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid_token") from exc

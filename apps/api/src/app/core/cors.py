from __future__ import annotations

from fastapi import Response

from app.core.config import settings


def cors_preflight_response() -> Response:
    response = Response(status_code=204)
    response.headers["Access-Control-Allow-Origin"] = settings.frontend_origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Vary"] = "Origin"
    return response

"""
SIGEX API Client — QR/Deeplink signing via eGov Mobile.

Docs: https://sigex.kz/support/developers/
Library reference: sigex-qr-signing-client (JS)

Flow:
  1. register_signing() → get qrCode + eGovMobileLaunchLink
  2. send_data_to_sign(dataURL, document_b64) → push data
  3. poll_signatures(signURL) → wait for CMS signature from eGov Mobile
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SIGEX_BASE_URL = "https://sigex.kz"


class SigexSigningError(Exception):
    """Raised when SIGEX API returns an error."""
    pass


class SigexClient:
    """Async client for SIGEX QR/deeplink signing API."""

    def __init__(self, base_url: str = SIGEX_BASE_URL):
        self.base_url = base_url.rstrip("/")

    # ──────────────────────────────────────────────
    # Step 1: Register signing procedure
    # ──────────────────────────────────────────────
    async def register_signing(self, description: str) -> dict[str, Any]:
        """
        POST /api/egovQr — register a new QR signing procedure.

        Returns dict with keys:
          - qrCode (base64 GIF)
          - dataURL (where to POST data)
          - signURL (where to GET signatures)
          - eGovMobileLaunchLink
          - eGovBusinessLaunchLink
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/egovQr",
                json={"description": description},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("message"):
            raise SigexSigningError(f"SIGEX register error: {data['message']}")

        logger.info("SIGEX signing registered, dataURL=%s", data.get("dataURL"))
        return data

    # ──────────────────────────────────────────────
    # Step 2: Send data to be signed
    # ──────────────────────────────────────────────
    async def send_data_to_sign(
        self,
        data_url: str,
        document_b64: str,
        names: list[str],
        meta: list[dict[str, str]] | None = None,
        sign_method: str = "CMS_SIGN_ONLY",
    ) -> dict[str, Any]:
        """
        POST {dataURL} — send document data for signing.

        Args:
            data_url: URL from register_signing response
            document_b64: Base64-encoded document content
            names: [nameRu, nameKz, nameEn] — at least one required
            meta: optional list of {name, value} metadata dicts
            sign_method: CMS_SIGN_ONLY | CMS_WITH_DATA | XML
        """
        payload = {
            "signMethod": sign_method,
            "documentsToSign": [
                {
                    "id": 1,
                    "nameRu": names[0],
                    "nameKz": names[1] if len(names) > 1 else names[0],
                    "nameEn": names[2] if len(names) > 2 else names[0],
                    "meta": meta or [],
                    "document": {
                        "file": {
                            "mime": "",
                            "data": document_b64,
                        }
                    },
                }
            ],
        }

        last_error = None
        for attempt in range(5):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(data_url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()

                if data.get("message"):
                    raise SigexSigningError(
                        f"SIGEX send_data error: {data['message']}"
                    )

                logger.info("SIGEX data sent successfully")
                return data
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                logger.warning("SIGEX send_data attempt %d failed: %s", attempt + 1, exc)
                await asyncio.sleep(1.0)

        raise SigexSigningError(f"Failed to send data after 5 attempts: {last_error}")

    # ──────────────────────────────────────────────
    # Step 3: Poll for signatures (long-polling)
    # ──────────────────────────────────────────────
    async def poll_signatures(
        self,
        sign_url: str,
        max_wait_seconds: int = 180,
        poll_interval: float = 3.0,
    ) -> list[str]:
        """
        GET {signURL} — poll until signatures arrive from eGov Mobile.

        Returns list of Base64-encoded CMS signatures.
        Raises TimeoutError if user doesn't sign within max_wait_seconds.
        """
        max_attempts = int(max_wait_seconds / poll_interval)

        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(sign_url)
                    if resp.status_code == 200:
                        data = resp.json()
                        if not data.get("message"):
                            # Signatures received!
                            signatures = [
                                doc["document"]["file"]["data"]
                                for doc in data.get("documentsToSign", [])
                            ]
                            if signatures:
                                logger.info(
                                    "SIGEX signatures received: %d signature(s)",
                                    len(signatures),
                                )
                                return signatures
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.debug("SIGEX poll attempt %d error: %s", attempt + 1, exc)

            await asyncio.sleep(poll_interval)

        raise TimeoutError(
            f"Подпись не получена в течение {max_wait_seconds} секунд. "
            "Пользователь не завершил подписание в eGov Mobile."
        )

    # ──────────────────────────────────────────────
    # High-level: Full signing flow
    # ──────────────────────────────────────────────
    async def initiate_signing(
        self,
        document_bytes: bytes,
        description: str,
        names: list[str],
        meta: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        High-level: Register + send data in one call.

        Returns dict with:
          - signing_id: internal tracking reference
          - eGovMobileLaunchLink: deeplink for mobile
          - eGovBusinessLaunchLink: deeplink for eGov Business
          - qr_code_b64: QR code as base64 GIF
          - sign_url: URL to poll for signatures
        """
        document_b64 = base64.b64encode(document_bytes).decode("ascii")

        # 1. Register
        reg = await self.register_signing(description)

        # 2. Send data
        await self.send_data_to_sign(
            data_url=reg["dataURL"],
            document_b64=document_b64,
            names=names,
            meta=meta,
        )

        return {
            "eGovMobileLaunchLink": reg.get("eGovMobileLaunchLink", ""),
            "eGovBusinessLaunchLink": reg.get("eGovBusinessLaunchLink", ""),
            "qr_code_b64": reg.get("qrCode", ""),
            "sign_url": reg.get("signURL", ""),
            "data_url": reg.get("dataURL", ""),
        }

from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core.config import settings


def build_launch_keyboard() -> InlineKeyboardMarkup | None:
    if not settings.telegram_app_url.startswith("https://"):
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть приложение",
                    web_app=WebAppInfo(url=settings.telegram_app_url),
                )
            ]
        ]
    )


class TelegramBotClient:
    def __init__(self) -> None:
        if not settings.telegram_bot_token:
            raise RuntimeError("telegram_bot_token_missing")
        self.bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    async def send_invoice_pdf(
        self,
        *,
        chat_id: int,
        filename: str,
        pdf_bytes: bytes,
        caption: str | None,
    ) -> int:
        document = BufferedInputFile(pdf_bytes, filename=filename)
        message = await self.bot.send_document(
            chat_id=chat_id,
            document=document,
            caption=caption,
            reply_markup=build_launch_keyboard(),
        )
        return message.message_id

    async def close(self) -> None:
        await self.bot.session.close()

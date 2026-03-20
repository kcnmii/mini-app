from __future__ import annotations

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.core.config import settings


def build_launch_keyboard(docx_filename: str | None = None) -> InlineKeyboardMarkup | None:
    buttons = []
    
    if docx_filename:
        # We store the callback data as docx:<filename> to fetch it later
        buttons.append([InlineKeyboardButton(text="Скачать в Word", callback_data=f"docx:{docx_filename}")])

    if settings.telegram_app_url.startswith("https://"):
        buttons.append([
            InlineKeyboardButton(
                text="Открыть приложение",
                web_app=WebAppInfo(url=settings.telegram_app_url),
            )
        ])
        
    if not buttons:
        return None
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)


class TelegramBotClient:
    def __init__(self) -> None:
        token = settings.telegram_bot_token
        self.enabled = bool(token) and token != "fake"
        if not self.enabled:
            # Skip initialization if no token or fake token
            self.bot = None
            return

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
        if not self.enabled: return 0
        document = BufferedInputFile(pdf_bytes, filename=filename)
        message = await self.bot.send_document(
            chat_id=chat_id,
            document=document,
            caption=caption,
            reply_markup=build_launch_keyboard(),
        )
        return message.message_id

    async def send_invoice_documents(
        self,
        *,
        chat_id: int,
        filename_prefix: str,
        pdf_bytes: bytes,
        docx_bytes: bytes,
        caption: str | None,
    ) -> int:
        if not self.enabled: return 0
        # Send ONLY PDF, keep docx behind an inline button
        pdf_doc = BufferedInputFile(pdf_bytes, filename=f"{filename_prefix}.pdf")
        msg = await self.bot.send_document(
            chat_id=chat_id,
            document=pdf_doc,
            caption=caption,
            reply_markup=build_launch_keyboard(f"{filename_prefix}.docx"),
        )
        return msg.message_id

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
    ) -> int:
        if not self.enabled: return 0
        message = await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=build_launch_keyboard(),
        )
        return message.message_id

    async def close(self) -> None:
        if not self.enabled: return
        await self.bot.session.close()

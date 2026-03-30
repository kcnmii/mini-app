import asyncio
import logging
import os

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from app.modules.telegram_bot.service import TelegramBotClient, build_launch_keyboard


async def on_start(message: Message) -> None:
    await message.answer(
        f"Открой Mini App и создай счет или КП.\nchat_id: <code>{message.chat.id}</code>",
        reply_markup=build_launch_keyboard(),
    )


async def on_web_app_data(message: Message) -> None:
    await message.answer("Данные из Mini App получены.")


async def on_docx_callback(callback: CallbackQuery) -> None:
    if not callback.data or not callback.data.startswith("docx:"):
        await callback.answer()
        return

    parts = callback.data.split(":")
    if len(parts) == 3:
        _, user_id_str, filename = parts
    else:
        # Fallback for old buttons
        _, filename = parts
        user_id_str = "0"
        
    s3_key = f"invoices/{user_id_str}/{filename}"
    
    from app.core import s3
    content = await s3.download_file(s3_key)

    if not content:
        await callback.answer("Файл не найден. Попробуйте отправить документ заново из приложения.", show_alert=True)
        return

    await callback.answer("Отправляем Word файл...")

    try:
        await callback.message.answer_document(
            document=BufferedInputFile(content, filename=filename),
            caption=f"Word вариант: {filename}"
        )
    except Exception as e:
        logging.error(f"Error sending docx: {e}")
        await callback.answer("Произошла ошибка при отправке файла.", show_alert=True)


async def on_zip_src_callback(callback: CallbackQuery) -> None:
    if not callback.data or not callback.data.startswith("zip_src:"):
        await callback.answer()
        return

    _, doc_id_str = callback.data.split(":")
    doc_id = int(doc_id_str)

    await callback.answer("⏳ Собираем архив с подписями...")

    from app.core.db import SessionLocal
    from app.services.signature_exporter import SignatureExporter

    db = SessionLocal()
    try:
        exporter = SignatureExporter(db)
        zip_bytes, filename = await exporter.generate_zip_package(doc_id)

        await callback.message.answer_document(
            document=BufferedInputFile(zip_bytes, filename=filename),
            caption=f"📦 Исходники и ЭЦП подписи для документа №{doc_id}.\n\n"
                    f"Файл .cms можно проверить на ezsigner.kz"
        )
    except Exception as e:
        logging.error(f"Error sending zip source: {e}")
        await callback.answer(f"Ошибка при сборке архива: {e}", show_alert=True)
    finally:
        db.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = TelegramBotClient()
    dp = Dispatcher()
    dp.message.register(on_start, CommandStart())
    dp.message.register(on_web_app_data, F.web_app_data)
    dp.callback_query.register(on_docx_callback, F.data.startswith("docx:"))
    dp.callback_query.register(on_zip_src_callback, F.data.startswith("zip_src:"))

    try:
        await dp.start_polling(client.bot)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

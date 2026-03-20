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

    filename = callback.data.split(":", 1)[1]
    # Re-use the same logic as in persist_debug_output
    file_path = os.path.join("data/storage", filename)

    if not os.path.exists(file_path):
        await callback.answer("Файл не найден. Попробуйте отправить документ заново из приложения.", show_alert=True)
        return

    await callback.answer("Отправляем Word файл...")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        await callback.message.answer_document(
            document=BufferedInputFile(content, filename=filename),
            caption=f"Word вариант: {filename}"
        )
    except Exception as e:
        logging.error(f"Error sending docx: {e}")
        await callback.answer("Произошла ошибка при отправке файла.", show_alert=True)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = TelegramBotClient()
    dp = Dispatcher()
    dp.message.register(on_start, CommandStart())
    dp.message.register(on_web_app_data, F.web_app_data)
    dp.callback_query.register(on_docx_callback, F.data.startswith("docx:"))

    try:
        await dp.start_polling(client.bot)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

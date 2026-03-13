import asyncio
import logging

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.modules.telegram_bot.service import TelegramBotClient, build_launch_keyboard


async def on_start(message: Message) -> None:
    await message.answer(
        f"Открой Mini App и создай счет или КП.\nchat_id: <code>{message.chat.id}</code>",
        reply_markup=build_launch_keyboard(),
    )


async def on_web_app_data(message: Message) -> None:
    await message.answer("Данные из Mini App получены.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = TelegramBotClient()
    dp = Dispatcher()
    dp.message.register(on_start, CommandStart())
    dp.message.register(on_web_app_data, F.web_app_data)

    try:
        await dp.start_polling(client.bot)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

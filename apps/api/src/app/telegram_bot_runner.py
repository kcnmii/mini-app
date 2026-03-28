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


async def on_sign_edo_callback(callback: CallbackQuery) -> None:
    if not callback.data or not callback.data.startswith("sign_edo:"):
        await callback.answer()
        return

    from app.core.db import SessionLocal
    from app.schemas.edo import SignDocumentRequest
    from app.modules.edo.router import initiate_signing
    from fastapi import BackgroundTasks, Request
    import urllib.parse
    
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Неверный формат данных", show_alert=True)
        return
        
    document_id = int(parts[1])
    # The callback user id usually maps to the one who pressed it
    user_id = callback.from_user.id
    
    await callback.answer("⌛ Генерируем ссылку для подписания в eGov Mobile...", show_alert=False)

    try:
        # Spin up a DB session manually because we are outside FastAPI request context
        db = SessionLocal()
        
        # We must mock a Request object or construct the base URL manually
        # since we don't have a FastAPI request here.
        # We can use the app URL from settings.
        from app.core.config import settings
        backend_url = str(settings.telegram_app_url).split("/#")[0]
        # remove "/mini-app" or whatever frontend path if it's the exact domain, usually API is /api
        parsed = urllib.parse.urlparse(settings.telegram_app_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}/api" if parsed.netloc else "https://api.doc.onlink.kz"
        
        # Create a mock request obj or just manually call the logic
        from app.core.models.document import Document
        from app.core.models.client import SupplierProfile
        from app.services.sigex_client import SigexClient
        from app.core.models.edo import SigningSession
        import hashlib
        from app.core import s3
        
        doc = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()
        
        if not doc:
            await callback.message.answer("❌ Документ не найден или у вас нет доступа.")
            return

        sigex = SigexClient()
        pdf_bytes = await s3.download_file(doc.pdf_path) if doc.pdf_path else None
        if not pdf_bytes:
            # Fallback to signing just title if no PDF yet
            pdf_bytes = doc.title.encode("utf-8")

        profile = db.query(SupplierProfile).filter(SupplierProfile.user_id == user_id).first()
        signer_role = "supplier"
        signer_name = (profile.executor_name if profile else "") or "Подписант"
        company_name = (profile.company_name if profile else "") or ""
        
        meta = [
            {"name": "Документ", "value": str(doc.title or "")},
            {"name": "Сумма", "value": str(doc.total_sum or "0")},
            {"name": "Компания", "value": str(company_name or "")},
        ]
        
        result = await sigex.initiate_signing(
            document_bytes=pdf_bytes,
            description=f"Подписание: {doc.title}",
            names=[str(doc.title), str(doc.title), str(doc.title)],
            meta=meta,
        )
        
        session = SigningSession(
            document_id=doc.id,
            user_id=user_id,
            sign_url=result["sign_url"],
            egov_mobile_link=result["eGovMobileLaunchLink"],
            egov_business_link=result["eGovBusinessLaunchLink"],
            qr_code_b64=result["qr_code_b64"],
            status="pending",
            signer_role=signer_role,
        )
        db.add(session)
        doc.edo_status = "awaiting_sign"
        db.commit()
        db.refresh(session)
        
        # We don't have FastAPI BackgroundTasks, so we schedule manually
        from app.modules.edo.router import _poll_and_save_signature
        asyncio.create_task(_poll_and_save_signature(
            signing_session_id=session.id,
            sign_url=result["sign_url"],
            document_id=doc.id,
            user_id=user_id,
            signer_iin=(profile.company_iin if profile else ""),
            signer_name=signer_name,
            signer_role=signer_role,
        ))
        
        if result.get("eGovMobileLaunchLink"):
            safe_url = urllib.parse.quote(result["eGovMobileLaunchLink"])
            redirect_url = f"{base_url}/edo/mobile-redirect?url={safe_url}"
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Открыть eGov Mobile для подписи", url=redirect_url)]])
            await callback.message.reply(
                text=f"Документ отправлен в eGov Mobile. Нажмите кнопку ниже для перехода:",
                reply_markup=kb
            )
        else:
            await callback.message.answer("Не удалось сгенерировать ссылку для подписи.")
            
    except Exception as e:
        import traceback
        logging.error(f"Error handling sign_edo callback: {e}\n{traceback.format_exc()}")
        await callback.message.answer(f"❌ Ошибка отправки в SIGEX: {e}")
    finally:
        db.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    client = TelegramBotClient()
    dp = Dispatcher()
    dp.message.register(on_start, CommandStart())
    dp.message.register(on_web_app_data, F.web_app_data)
    dp.callback_query.register(on_docx_callback, F.data.startswith("docx:"))
    dp.callback_query.register(on_sign_edo_callback, F.data.startswith("sign_edo:"))

    try:
        await dp.start_polling(client.bot)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

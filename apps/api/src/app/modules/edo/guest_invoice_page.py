"""Public guest page for sending incoming invoices to registered users."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db, SupplierProfile, Invoice, NewInvoiceItem
from app.core.config import settings

router = APIRouter(prefix="/edo", tags=["edo-guest-invoice"])

class GuestInvoiceItem(BaseModel):
    name: str
    quantity: float
    price: float
    unit: str = "шт."

class GuestInvoicePayload(BaseModel):
    sender_name: str
    sender_bin: str
    sender_email: str = ""
    sender_phone: str = ""
    items: list[GuestInvoiceItem]
    total: float


# ──────────────────────────────────────────────
# GET /edo/guest-invoice/{profile_uuid} — HTML form
# ──────────────────────────────────────────────
@router.get("/guest-invoice/{profile_uuid}", response_class=HTMLResponse)
async def guest_invoice_form(profile_uuid: str, db: Session = Depends(get_db)):
    """Render the public form so guests can send an invoice to this user."""
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.profile_uuid == profile_uuid
    ).first()

    if not profile:
        return HTMLResponse(
            content="""
            <html>
            <head><meta charset="utf-8"><title>Ошибка</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>body{font-family:-apple-system,sans-serif;background:#f2f2f7;display:flex;justify-content:center;align-items:center;min-height:100vh;}
            .card{background:#fff;padding:32px;border-radius:16px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.05);}</style>
            </head>
            <body><div class="card"><h2>❌ Пользователь не найден</h2><p>Ссылка недействительна.</p></div></body>
            </html>
            """,
            status_code=404
        )

    company_name = profile.company_name or "Неизвестная компания"
    company_bin = profile.company_iin or ""

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Выставить счёт для {company_name}</title>
    <style>
        :root {{
            --primary: #007AFF;
            --bg: #f2f2f7;
            --card: #ffffff;
            --text: #1c1c1e;
            --text-secondary: #8e8e93;
            --border: #e5e5ea;
            --success: #34C759;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0; padding: 0; background: var(--bg); color: var(--text); padding-bottom: 40px;
        }}
        .header {{
            background: var(--card); padding: 24px 20px; border-bottom: 1px solid var(--border);
            position: sticky; top: 0; z-index: 10;
        }}
        .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
        .card {{ background: var(--card); border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }}
        .section-title {{ font-size: 14px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 12px; letter-spacing: 0.5px; }}
        .form-group {{ margin-bottom: 16px; }}
        label {{ display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: #3a3a3c; }}
        input {{ width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 10px; font-size: 16px; box-sizing: border-box; transition: 0.2s; outline: none; }}
        input:focus {{ border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0,122,255,0.1); }}
        
        .item-row {{ display: grid; grid-template-columns: 2fr 1fr 1.5fr; gap: 8px; margin-bottom: 8px; }}
        .btn {{
            width: 100%; padding: 14px; background: var(--primary); color: #fff; border: none;
            border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; transition: 0.2s;
        }}
        .btn:active {{ transform: scale(0.98); opacity: 0.9; }}
        .btn:disabled {{ opacity: 0.5; pointer-events: none; }}
        .btn-outline {{ background: transparent; color: var(--primary); border: 2px dashed var(--primary); }}
        
        .totals {{ margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: 700; }}
        
        .promo-block {{
            background: linear-gradient(135deg, #f0f9ff, #f5f3ff); border: 1px solid #e0e7ff; 
            border-radius: 16px; padding: 20px; text-align: center; margin-top: 32px;
        }}
        
        .hidden {{ display: none !important; }}
        
        /* KYC Result Card */
        .kyc-result {{
            margin-top: 16px;
            padding: 16px;
            background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
            border: 1px solid #86efac;
            border-radius: 12px;
            animation: slideDown 0.4s ease;
        }}
        .kyc-result .kyc-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 14px;
        }}
        .kyc-result .kyc-label {{
            color: var(--text-secondary);
            font-size: 12px;
        }}
        .kyc-result .kyc-value {{
            font-weight: 600;
            text-align: right;
            max-width: 65%;
        }}
        .kyc-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .kyc-badge.success {{
            background: #dcfce7;
            color: #166534;
        }}
        .kyc-badge.loading {{
            background: #dbeafe;
            color: #1e40af;
        }}
        .kyc-badge.error {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        @keyframes slideDown {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .bin-input-wrapper {{
            position: relative;
        }}
        .bin-input-wrapper .status-icon {{
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 20px;
        }}
        
        @keyframes spin {{
            to {{ transform: translateY(-50%) rotate(360deg); }}
        }}
        .bin-input-wrapper .spinner-icon {{
            animation: spin 1s linear infinite;
        }}
    </style>
</head>
<body>

<div class="header">
    <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 4px;">Выставляется счёт для:</div>
    <div style="font-size: 18px; font-weight: 700;">{company_name}</div>
    <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">БИН/ИИН: {company_bin}</div>
</div>

<div class="container" id="form-container">
    <form id="invoice-form">
        <div class="card">
            <div class="section-title">Ваши данные</div>
            <div class="form-group">
                <label>БИН / ИИН вашей компании</label>
                <div class="bin-input-wrapper">
                    <input type="text" id="senderBin" required placeholder="Введите 12 цифр" pattern="\\d{{12}}" maxlength="12" inputmode="numeric" autocomplete="off">
                    <span class="status-icon" id="binStatusIcon"></span>
                </div>
            </div>
            
            <!-- КYC Result — hidden until BIN is resolved -->
            <div id="kyc-result-container" class="hidden"></div>
            
            <!-- Hidden fields populated by KYC -->
            <input type="hidden" id="senderName" value="">
            <input type="hidden" id="senderAddress" value="">
            <input type="hidden" id="senderDirector" value="">
        </div>

        <div class="card" id="items-card">
            <div class="section-title">Позиции счёта</div>
            <div id="items-container">
                <div class="item-row">
                    <input type="text" placeholder="Наименование" class="i-name" required>
                    <input type="number" placeholder="Кол-во" class="i-qty" value="1" min="1" required step="any">
                    <input type="number" placeholder="Цена (₸)" class="i-price" required step="any">
                </div>
            </div>
            <button type="button" class="btn btn-outline" style="margin-top: 12px;" onclick="addItem()">+ Добавить позицию</button>
            
            <div class="totals">
                <span>Итого к оплате:</span>
                <span id="grand-total">0 ₸</span>
            </div>
        </div>

        <button type="submit" class="btn" id="submit-btn" disabled style="box-shadow: 0 4px 12px rgba(0,122,255,0.3);">📤 Отправить счёт</button>
    </form>
    
    <!-- CTA Block -->
    <div class="promo-block">
        <div style="font-size: 24px; margin-bottom: 8px;">📱</div>
        <h4 style="margin: 0 0 6px 0; font-size: 15px;">Автоматические уведомления</h4>
        <p style="margin: 0 0 12px 0; font-size: 13px; color: var(--text-secondary); line-height: 1.4;">
            Узнайте мгновенно, когда {company_name} оплатит этот счёт или подпишет документы.
        </p>
        <a href="https://t.me/DocOnlinkBot" target="_blank" style="color: var(--primary); font-weight: 600; text-decoration: none; font-size: 14px;">Попробовать Doc App →</a>
    </div>
</div>

<div class="container hidden" id="success-container">
    <div class="card" style="text-align: center; padding: 40px 20px;">
        <div style="font-size: 48px; margin-bottom: 16px;">✅</div>
        <h2 style="margin: 0 0 12px 0;">Счёт успешно отправлен!</h2>
        <p style="color: var(--text-secondary); margin: 0 0 24px 0; font-size: 15px;">Он появится во входящих документах пользователя {company_name}.</p>
        
        <div style="background: linear-gradient(135deg, #007AFF11, #5856D611); border: 1px solid #007AFF22; border-radius: 16px; padding: 20px; text-align: left;">
            <div style="display: flex; gap: 12px; align-items: flex-start;">
                <div style="font-size: 24px;">🚀</div>
                <div>
                    <h4 style="margin: 0 0 4px 0; font-size: 14px;">Переходите на электронный ЭДО</h4>
                    <p style="margin: 0 0 12px 0; font-size: 12px; color: var(--text-secondary); line-height: 1.4;">Создавайте счета и акты, подписывайте ЭЦП прямо со смартфона за 30 секунд. Без компьютеров и NCALayer.</p>
                    <a href="https://t.me/DocOnlinkBot" target="_blank" class="btn" style="display: inline-block; text-align: center; padding: 10px; text-decoration: none; box-sizing: border-box;">Запустить Telegram-бота</a>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
    // Determine API base: if we're on /edo/..., we might need /api or just /
    // If the current path doesn't have /api but mini-app uses it, 
    // it usually means Nginx handles /api by stripping it.
    const API_BASE = window.location.pathname.startsWith('/api') ? '/api' : '';
    console.log('Using API_BASE:', API_BASE);
    const PROFILE_UUID = '{profile_uuid}';
    
    let kycData = null;
    let kycLookupTimer = null;
    
    // BIN/IIN input handler — auto-lookup via KYC API
    const binInput = document.getElementById('senderBin');
    const statusIcon = document.getElementById('binStatusIcon');
    const kycContainer = document.getElementById('kyc-result-container');
    const submitBtn = document.getElementById('submit-btn');
    
    binInput.addEventListener('input', function() {{
        const val = this.value.replace(/\\D/g, '');
        this.value = val;
        
        // Reset state
        kycData = null;
        kycContainer.classList.add('hidden');
        kycContainer.innerHTML = '';
        statusIcon.innerHTML = '';
        submitBtn.disabled = true;
        document.getElementById('senderName').value = '';
        
        if (val.length === 12) {{
            // Show loading
            statusIcon.innerHTML = '<span class="spinner-icon">⏳</span>';
            
            clearTimeout(kycLookupTimer);
            kycLookupTimer = setTimeout(() => lookupBin(val), 300);
        }}
    }});
    
    async function lookupBin(bin) {{
        try {{
            const resp = await fetch(`${{API_BASE}}/clients/search-bin/${{bin}}`);
            if (!resp.ok) {{
                statusIcon.innerHTML = '❌';
                kycContainer.classList.remove('hidden');
                kycContainer.innerHTML = `
                    <div class="kyc-badge error">❌ Организация не найдена</div>
                    <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">Проверьте правильность ИИН/БИН и попробуйте снова.</p>
                `;
                return;
            }}
            
            const data = await resp.json();
            kycData = data;
            
            // Fill hidden fields
            document.getElementById('senderName').value = data.name || '';
            document.getElementById('senderAddress').value = data.address || '';
            document.getElementById('senderDirector').value = data.director || '';
            
            statusIcon.innerHTML = '✅';
            
            // Show beautiful result card
            const typeLabel = data.type === 'IP' ? 'ИП' : 'ТОО / Юр. лицо';
            kycContainer.classList.remove('hidden');
            kycContainer.innerHTML = `
                <div class="kyc-result">
                    <div class="kyc-badge success">✓ Данные найдены</div>
                    <div class="kyc-row">
                        <span class="kyc-label">Название</span>
                        <span class="kyc-value">${{data.name || '—'}}</span>
                    </div>
                    <div class="kyc-row">
                        <span class="kyc-label">Тип</span>
                        <span class="kyc-value">${{typeLabel}}</span>
                    </div>
                    ${{data.director ? `<div class="kyc-row"><span class="kyc-label">Руководитель</span><span class="kyc-value">${{data.director}}</span></div>` : ''}}
                    ${{data.address ? `<div class="kyc-row"><span class="kyc-label">Адрес</span><span class="kyc-value" style="font-size:12px;">${{data.address}}</span></div>` : ''}}
                </div>
            `;
            
            // Enable submit
            submitBtn.disabled = false;
            
        }} catch (err) {{
            statusIcon.innerHTML = '⚠️';
            kycContainer.classList.remove('hidden');
            kycContainer.innerHTML = `
                <div class="kyc-badge error">⚠️ Ошибка сети</div>
                <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">Попробуйте ещё раз позже.</p>
            `;
        }}
    }}
    
    function calculateTotal() {{
        let total = 0;
        document.querySelectorAll('.item-row').forEach(row => {{
            const qty = parseFloat(row.querySelector('.i-qty').value) || 0;
            const price = parseFloat(row.querySelector('.i-price').value) || 0;
            total += (qty * price);
        }});
        document.getElementById('grand-total').textContent = new Intl.NumberFormat('ru-RU').format(total) + ' ₸';
        return total;
    }}

    function addItem() {{
        const container = document.getElementById('items-container');
        const row = document.createElement('div');
        row.className = 'item-row';
        row.innerHTML = `
            <input type="text" placeholder="Наименование" class="i-name" required>
            <input type="number" placeholder="Кол-во" class="i-qty" value="1" min="1" required step="any">
            <input type="number" placeholder="Цена (₸)" class="i-price" required step="any">
        `;
        container.appendChild(row);
        
        row.querySelectorAll('input').forEach(input => {{
            input.addEventListener('input', calculateTotal);
        }});
    }}

    document.getElementById('items-container').addEventListener('input', calculateTotal);

    document.getElementById('invoice-form').addEventListener('submit', async (e) => {{
        e.preventDefault();
        
        if (!kycData) {{
            alert('Сначала введите корректный ИИН/БИН');
            return;
        }}
        
        const btn = document.getElementById('submit-btn');
        btn.disabled = true;
        btn.textContent = 'Отправка...';
        
        const items = [];
        document.querySelectorAll('.item-row').forEach(row => {{
            items.push({{
                name: row.querySelector('.i-name').value,
                quantity: parseFloat(row.querySelector('.i-qty').value) || 1,
                price: parseFloat(row.querySelector('.i-price').value) || 0,
                unit: "шт."
            }});
        }});
        
        const payload = {{
            sender_name: document.getElementById('senderName').value.trim(),
            sender_bin: document.getElementById('senderBin').value.trim(),
            sender_email: '',
            sender_phone: '',
            items: items,
            total: calculateTotal()
        }};
        
        try {{
            const resp = await fetch(`${{API_BASE}}/edo/guest-invoice/${{PROFILE_UUID}}`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload)
            }});
            const data = await resp.json();
            
            if (data.success) {{
                document.getElementById('form-container').classList.add('hidden');
                document.getElementById('success-container').classList.remove('hidden');
                window.scrollTo(0, 0);
            }} else {{
                alert('Ошибка: ' + (data.error || 'Не удалось отправить'));
                btn.disabled = false;
                btn.textContent = '📤 Отправить счёт';
            }}
        }} catch(err) {{
            alert('Ошибка сети: ' + err.message);
            btn.disabled = false;
            btn.textContent = '📤 Отправить счёт';
        }}
    }});
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ──────────────────────────────────────────────
# POST /edo/guest-invoice/{profile_uuid} — Submit
# ──────────────────────────────────────────────
@router.post("/guest-invoice/{profile_uuid}")
async def submit_guest_invoice(
    profile_uuid: str,
    payload: GuestInvoicePayload,
    db: Session = Depends(get_db)
):
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.profile_uuid == profile_uuid
    ).first()

    from app.modules.render.service import RenderService
    import json
    from app.core.config import settings
    from app.core.db import Document

    target_user_id = profile.user_id
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    invoice_number = str(uuid.uuid4()).replace("-", "")[:6].upper()
    title = f"Счет на оплату № {invoice_number} (От гостя)"

    # Build basic data for the template renderer
    items_data = []
    total_num = 0.0
    for i, it in enumerate(payload.items):
        t = it.quantity * it.price
        total_num += t
        items_data.append({
            "number": i + 1,
            "name": it.name,
            "quantity": str(it.quantity),
            "unit": it.unit,
            "price": str(it.price),
            "total": str(t),
            "code": ""
        })

    words = str(total_num)

    template_data = {
        "INVOICE_NUMBER": invoice_number,
        "INVOICE_DATE": now.strftime("%d.%m.%Y"),
        "CONTRACT": "Без договора",
        "SUPPLIER_NAME": payload.sender_name,
        "SUPPLIER_IIN": payload.sender_bin,
        "SUPPLIER_ADDRESS": "",
        "COMPANY_NAME": profile.company_name or "",
        "COMPANY_IIN": profile.company_iin or "",
        "COMPANY_IIC": profile.bank_account or "",
        "COMPANY_BIC": profile.bank_bic or "",
        "COMPANY_KBE": profile.kbe or "",
        "BENEFICIARY_BANK": profile.bank_name or "",
        "PAYMENT_CODE": "",
        "CLIENT_NAME": profile.company_name or "",
        "CLIENT_IIN": profile.company_iin or "",
        "CLIENT_ADDRESS": profile.address or "",
        "EXECUTOR_NAME": payload.sender_name,
        "POSITION": "",
        "VAT": "Без НДС",
        "ITEMS_TOTAL_LINE": str(total_num),
        "TOTAL_SUM": str(total_num),
        "TOTAL_SUM_IN_WORDS": words,
        "items": items_data,
        "LOGO": "",
        "SIG": "",
        "STAMP": "",
    }

    render_service = RenderService()
    try:
        docx_bytes = await render_service.render_document_docx("invoice-kz", template_data)
        pdf_bytes = await render_service.convert_docx_to_pdf(f"invoice-{invoice_number}.docx", docx_bytes)
        
        s3_pdf_key = await render_service.save_file(f"invoice-{invoice_number}.pdf", pdf_bytes, user_id=0)
        pdf_url = f"{settings.s3_endpoint}/{settings.s3_bucket}/{s3_pdf_key}"
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to generate guest invoice PDF: {e}")
        return JSONResponse({"success": False, "error": "Ошибка генерации документа"}, status_code=500)

    # Note: For guest invoices, the sender is unauthenticated (user_id=0).
    # The receiver is target_user_id.
    share_uuid = str(uuid.uuid4())
    
    doc = Document(
        user_id=0, # 0 means created by guest sender.
        receiver_user_id=target_user_id,
        receiver_bin=payload.sender_bin, # Keep sender bin so it doesn't conflict
        title=title,
        client_name=payload.sender_name,
        total_sum=str(total_num),
        total_amount=total_num,
        total_sum_in_words=words,
        pdf_path=s3_pdf_key,
        docx_path="",
        doc_type="invoice",
        payload_json=json.dumps(template_data, ensure_ascii=False),
        edo_status="sent",
        share_uuid=share_uuid,
        created_at=now
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Notify target user
    try:
        bot_msg = (
            f"📥 <b>Новый гостевой счет!</b>\n\n"
            f"От: <b>{payload.sender_name}</b>\n"
            f"Документ: <code>{title}</code>\n"
            f"Сумма: <b>{total_num} ₸</b>\n\n"
            f"🔗 Откройте приложение для просмотра."
        )
        from app.modules.telegram_bot.service import TelegramBotClient
        bot = TelegramBotClient()
        await bot.send_message(chat_id=target_user_id, text=bot_msg)
        await bot.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to notify guest invoice: %s", e)

    return {"success": True, "invoice_number": invoice_number}

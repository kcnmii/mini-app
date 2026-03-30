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
        .btn-outline {{ background: transparent; color: var(--primary); border: 2px dashed var(--primary); }}
        
        .totals {{ margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: 700; }}
        
        .promo-block {{
            background: linear-gradient(135deg, #f0f9ff, #f5f3ff); border: 1px solid #e0e7ff; 
            border-radius: 16px; padding: 20px; text-align: center; margin-top: 32px;
        }}
        
        .hidden {{ display: none !important; }}
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
                <label>Название Вашей компании / ИП</label>
                <input type="text" id="senderName" required placeholder="Например: ТОО Ромашка">
            </div>
            <div class="form-group">
                <label>БИН / ИИН</label>
                <input type="text" id="senderBin" required placeholder="Для подстановки в акт" pattern="\\d{{12}}" maxlength="12" inputmode="numeric">
            </div>
            <div style="display: flex; gap: 12px;">
                <div class="form-group" style="flex: 1;">
                    <label>Email (опц.)</label>
                    <input type="email" id="senderEmail" placeholder="Для уведомлений">
                </div>
                <div class="form-group" style="flex: 1;">
                    <label>Телефон (опц.)</label>
                    <input type="tel" id="senderPhone" placeholder="+7 777...">
                </div>
            </div>
        </div>

        <div class="card">
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

        <button type="submit" class="btn" id="submit-btn" style="box-shadow: 0 4px 12px rgba(0,122,255,0.3);">📤 Отправить счёт</button>
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
    const API_BASE = '/api';
    const PROFILE_UUID = '{profile_uuid}';
    
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
            sender_email: document.getElementById('senderEmail').value.trim(),
            sender_phone: document.getElementById('senderPhone').value.trim(),
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

    if not profile:
        return JSONResponse({"success": False, "error": "Пользователь не найден"}, status_code=404)

    target_user_id = profile.user_id
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    invoice_number = f"ВХОД-{str(uuid.uuid4()).replace('-', '')[:6].upper()}"

    # Create Invoice with incoming flag (client_bin represents the SENDER here)
    inv = Invoice(
        user_id=target_user_id,
        number=invoice_number,
        date=now,
        client_name=payload.sender_name,
        client_bin=payload.sender_bin,
        status="incoming",  # Incoming magic status
        total_amount=payload.total,
        created_at=now,
        updated_at=now
    )
    db.add(inv)
    db.flush()

    for it in payload.items:
        line = NewInvoiceItem(
            invoice_id=inv.id,
            name=it.name,
            quantity=it.quantity,
            price=it.price,
            total=it.quantity * it.price,
            unit=it.unit
        )
        db.add(line)

    db.commit()

    # Notify target user
    try:
        from app.services.edo_notifications import notify_incoming_invoice
        await notify_incoming_invoice(db, target_user_id, inv, payload.sender_name)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to notify incoming invoice: %s", e)

    return {"success": True, "invoice_number": invoice_number}

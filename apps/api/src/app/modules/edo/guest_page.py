"""
EDO Guest Page — Public document view and signing for counterparties.

Serves an HTML page at /edo/doc/{share_uuid} that:
  - Shows document info, PDF preview, and existing signatures
  - Detects device type (mobile vs desktop)
  - Mobile: signs via eGov Mobile (SIGEX deeplink)
  - Desktop: signs via NCALayer (WebSocket wss://127.0.0.1:13579/)
  - Allows rejection with a comment
"""

from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timezone



from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db, Document, Signature, DocumentShare, SupplierProfile, SigningSession
from app.services.sigex_client import SigexClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/edo", tags=["edo-guest"])

sigex = SigexClient()


# ── Pydantic models ──

class GuestSignRequest(BaseModel):
    cms_signature_b64: str
    signer_iin: str = ""
    signer_name: str = ""
    signer_org: str = ""
    certificate_serial: str = ""


class GuestRejectRequest(BaseModel):
    comment: str = ""


# ──────────────────────────────────────────────
# GET /edo/doc/{share_uuid} — Guest HTML page
# ──────────────────────────────────────────────
@router.get("/doc/{share_uuid}", response_class=HTMLResponse)
async def guest_document_page(share_uuid: str, db: Session = Depends(get_db)):
    """Render a full HTML guest page for the counterparty."""

    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()
    if not share:
        return HTMLResponse(
            content=_error_html("Документ не найден", "Ссылка недействительна или документ был удалён."),
            status_code=404,
        )

    # Mark as accessed
    if not share.accessed_at:
        share.accessed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()

    doc = db.query(Document).filter(Document.id == share.document_id).first()
    if not doc:
        return HTMLResponse(
            content=_error_html("Документ удалён", "Этот документ больше не существует."),
            status_code=404,
        )

    # Get sender profile
    profile = db.query(SupplierProfile).filter(
        SupplierProfile.user_id == doc.user_id
    ).first()
    sender_name = (profile.company_name if profile else "") or "Неизвестный отправитель"
    sender_bin = (profile.company_iin if profile else "") or ""

    # Get signatures
    sigs = db.query(Signature).filter(Signature.document_id == doc.id).all()

    sigs_html = ""
    for s in sigs:
        role_label = "Отправитель" if s.signer_role == "sender" else "Получатель"
        role_color = "#007AFF" if s.signer_role == "sender" else "#34C759"
        signed_at = s.signed_at.strftime("%d.%m.%Y %H:%M") if s.signed_at else "—"
        cert_serial = (s.certificate_serial or "")[:20] + "..." if s.certificate_serial else "—"
        sigs_html += f"""
        <div class="sig-card">
            <div class="sig-icon" style="background: {role_color}20; color: {role_color};">✓</div>
            <div class="sig-info">
                <div class="sig-name">{s.signer_name or s.signer_iin or '—'}</div>
                <div class="sig-meta">{role_label} • {signed_at}</div>
                <div class="sig-cert">Серт: {cert_serial}</div>
            </div>
        </div>"""

    has_sender_sig = any(s.signer_role == "sender" for s in sigs)
    has_receiver_sig = any(s.signer_role == "receiver" for s in sigs)
    is_fully_signed = has_sender_sig and has_receiver_sig

    # Doc type badge
    doc_type_map = {
        "act": ("АВР", "#34C759"),
        "waybill": ("НКЛ", "#FF9500"),
        "invoice": ("СФ", "#007AFF"),
    }
    doc_type_info = doc_type_map.get(doc.doc_type or "", ("ДОК", "#8E8E93"))

    # Status
    if is_fully_signed:
        status_text = "Подписан обеими сторонами ✅✅"
        status_color = "#34C759"
    elif has_sender_sig:
        status_text = "Ожидает вашей подписи"
        status_color = "#FF9500"
    else:
        status_text = "Черновик"
        status_color = "#8E8E93"

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.title or 'Документ'} — ЭДО</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: #f2f2f7; color: #1c1c1e;
            min-height: 100vh;
        }}
        .header {{
            background: #fff; border-bottom: 1px solid #e5e5ea;
            padding: 16px 20px; text-align: center;
        }}
        .header-brand {{
            font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
            color: #8e8e93; font-weight: 600; margin-bottom: 4px;
        }}
        .header-title {{ font-size: 20px; font-weight: 700; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 16px; }}

        .card {{
            background: #fff; border-radius: 16px; padding: 20px;
            margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }}
        .card-title {{
            font-size: 13px; font-weight: 600; color: #8e8e93;
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px;
        }}

        .info-row {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px 0; border-bottom: 1px solid #f2f2f7; font-size: 15px;
        }}
        .info-row:last-child {{ border-bottom: none; }}
        .info-label {{ color: #8e8e93; font-weight: 500; }}
        .info-value {{ color: #1c1c1e; font-weight: 600; text-align: right; max-width: 60%; }}

        .amount {{ font-size: 32px; font-weight: 800; letter-spacing: -0.5px; margin: 8px 0; }}
        .badge {{
            display: inline-flex; align-items: center; gap: 4px;
            padding: 4px 10px; border-radius: 8px;
            font-size: 12px; font-weight: 700;
        }}
        .status-badge {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 6px 12px; border-radius: 20px;
            font-size: 13px; font-weight: 600;
        }}

        .sig-card {{
            display: flex; align-items: center; gap: 12px;
            padding: 12px; border-radius: 12px;
            background: #f2f2f7; margin-bottom: 8px;
        }}
        .sig-icon {{
            width: 40px; height: 40px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px; font-weight: 700; flex-shrink: 0;
        }}
        .sig-info {{ flex: 1; }}
        .sig-name {{ font-size: 14px; font-weight: 600; }}
        .sig-meta {{ font-size: 12px; color: #8e8e93; margin-top: 2px; }}
        .sig-cert {{ font-size: 10px; color: #aeaeb2; font-family: monospace; margin-top: 2px; }}

        .btn {{
            display: flex; align-items: center; justify-content: center; gap: 8px;
            width: 100%; height: 52px; border: none; border-radius: 14px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.2s; font-family: 'Inter', sans-serif;
        }}
        .btn-sign {{
            background: linear-gradient(135deg, #007AFF, #5856D6);
            color: #fff; box-shadow: 0 4px 16px rgba(0,122,255,0.25);
        }}
        .btn-sign:hover {{ transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,122,255,0.35); }}
        .btn-reject {{
            background: none; border: 1px solid #FF3B30; color: #FF3B30;
            height: 44px; font-size: 14px; margin-top: 8px;
        }}
        .btn-download {{
            background: #f2f2f7; color: #007AFF; height: 44px; font-size: 14px;
        }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}

        .spinner {{
            width: 20px; height: 20px; border: 2px solid currentColor;
            border-top-color: transparent; border-radius: 50%;
            animation: spin 0.8s linear infinite; display: inline-block;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        .ncalayer-status {{
            text-align: center; padding: 8px; font-size: 12px;
            color: #8e8e93; border-radius: 8px; margin-top: 8px;
        }}
        .ncalayer-status.connected {{ color: #34C759; }}
        .ncalayer-status.error {{ color: #FF3B30; }}

        .success-card {{
            background: #f0fdf4; border: 1px solid #bbf7d0;
            border-radius: 16px; padding: 24px; text-align: center; margin-bottom: 12px;
        }}
        .success-icon {{ font-size: 48px; margin-bottom: 8px; }}

        .pdf-preview {{ text-align: center; }}
        .pdf-preview img {{
            width: 100%; border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 12px;
        }}

        .footer {{
            text-align: center; padding: 32px 16px; color: #aeaeb2;
            font-size: 12px; line-height: 1.6;
        }}
        .footer a {{ color: #007AFF; text-decoration: none; }}

        .hidden {{ display: none; }}
        .material-icons-round {{ font-size: 20px; vertical-align: middle; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-brand">Электронный документооборот</div>
        <div class="header-title">{doc.title or 'Документ'}</div>
    </div>

    <div class="container">
        <!-- Sender Info -->
        <div class="card">
            <div class="card-title">📤 Отправитель</div>
            <div class="info-row">
                <span class="info-label">Организация</span>
                <span class="info-value">{sender_name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">БИН/ИИН</span>
                <span class="info-value" style="font-family: monospace;">{sender_bin}</span>
            </div>
        </div>

        <!-- Document Info -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span class="badge" style="background: {doc_type_info[1]}15; color: {doc_type_info[1]};">{doc_type_info[0]}</span>
                <span class="status-badge" style="background: {status_color}15; color: {status_color};">{status_text}</span>
            </div>
            <div class="amount">{doc.total_sum or '0'} ₸</div>
            <div class="info-row">
                <span class="info-label">Получатель</span>
                <span class="info-value">{doc.client_name or '—'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Дата</span>
                <span class="info-value">{doc.created_at.strftime('%d.%m.%Y') if doc.created_at else '—'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">MD5</span>
                <span class="info-value" style="font-family: monospace; font-size: 11px;">{doc.md5_hash or '—'}</span>
            </div>
        </div>

        <!-- PDF Preview -->
        <div class="card">
            <div class="card-title">📄 Превью документа</div>
            <div class="pdf-preview" id="pdf-preview">
                <div style="padding: 40px; color: #8e8e93;">
                    <span class="material-icons-round" style="font-size: 48px; display: block; margin-bottom: 8px;">picture_as_pdf</span>
                    PDF документ доступен для скачивания
                </div>
            </div>
            <button class="btn btn-download" onclick="downloadPdf()" style="margin-top: 12px;">
                <span class="material-icons-round">download</span>
                Скачать PDF
            </button>
        </div>

        <!-- Signatures -->
        <div class="card">
            <div class="card-title">🔐 Подписи ЭЦП</div>
            {sigs_html if sigs_html else '<div style="color: #8e8e93; font-size: 14px; text-align: center; padding: 16px;">Документ ещё не подписан</div>'}
        </div>

        <!-- Sign / Reject Actions (only if not fully signed and sender has signed) -->
        <div id="sign-section" class="{'hidden' if is_fully_signed or not has_sender_sig else ''}">
            <div class="card">
                <div class="card-title">✍️ Подписать документ</div>
                <p style="font-size: 13px; color: #8e8e93; margin-bottom: 16px; line-height: 1.5;">
                    Для подписания документа вам потребуется ЭЦП.
                    На телефоне — через <strong>eGov Mobile</strong>,
                    на компьютере — через <strong>NCALayer</strong>.
                </p>

                <!-- Mobile: eGov Mobile button -->
                <div id="mobile-sign" class="hidden">
                    <button class="btn btn-sign" id="sign-egov-btn" onclick="signViaEgovMobile()">
                        <span class="material-icons-round">phone_iphone</span>
                        Подписать через eGov Mobile
                    </button>
                </div>

                <!-- Desktop: NCALayer button -->
                <div id="desktop-sign" class="hidden">
                    <button class="btn btn-sign" id="sign-nca-btn" onclick="signViaNCALayer()">
                        <span class="material-icons-round">security</span>
                        Подписать через NCALayer
                    </button>
                    <div class="ncalayer-status" id="nca-status">Подключение к NCALayer...</div>
                </div>

                <button class="btn btn-reject" onclick="rejectDocument()">
                    Отклонить документ
                </button>
            </div>
        </div>

        <!-- Already fully signed -->
        <div id="success-section" class="{'hidden' if not is_fully_signed else ''}">
            <div class="success-card">
                <div class="success-icon">✅</div>
                <h3 style="font-weight: 700; margin-bottom: 4px;">Документ подписан</h3>
                <p style="color: #6b7280; font-size: 14px;">Обе стороны поставили электронные подписи</p>
            </div>
        </div>

        <!-- Waiting section (hidden initially) -->
        <div id="waiting-section" class="hidden">
            <div class="card" style="text-align: center; padding: 32px;">
                <div class="spinner" style="width: 32px; height: 32px; border-width: 3px; border-color: #007AFF; border-top-color: transparent; margin: 0 auto 16px;"></div>
                <h3 style="font-weight: 700; margin-bottom: 4px;">Ожидание подписи</h3>
                <p style="color: #8e8e93; font-size: 14px;" id="waiting-text">Подтвердите подпись в приложении eGov Mobile</p>
                <button class="btn btn-download" onclick="openEgovAgain()" id="reopen-egov-btn" style="margin-top: 16px;">
                    Открыть eGov Mobile ещё раз
                </button>
            </div>
        </div>

        <div class="footer">
            Электронный документооборот<br>
            Создано с помощью <a href="https://doc.onlink.kz">Doc App</a><br>
            Управляйте документами за 30 секунд →
        </div>
    </div>

<script>
    const API_BASE = window.location.origin;
    const SHARE_UUID = "{share_uuid}";
    const DOC_ID = {doc.id};
    const IS_MOBILE = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

    let ncaSocket = null;
    let egovMobileLink = null;

    // Detect device and show appropriate button
    if (IS_MOBILE) {{
        document.getElementById('mobile-sign').classList.remove('hidden');
    }} else {{
        document.getElementById('desktop-sign').classList.remove('hidden');
        connectNCALayer();
    }}

    // ── NCALayer WebSocket ──
    function connectNCALayer() {{
        try {{
            ncaSocket = new WebSocket('wss://127.0.0.1:13579/');
            ncaSocket.onopen = () => {{
                document.getElementById('nca-status').textContent = '✅ NCALayer подключен';
                document.getElementById('nca-status').className = 'ncalayer-status connected';
            }};
            ncaSocket.onclose = () => {{
                document.getElementById('nca-status').textContent = '❌ NCALayer не запущен. Запустите NCALayer.';
                document.getElementById('nca-status').className = 'ncalayer-status error';
                setTimeout(connectNCALayer, 5000);
            }};
            ncaSocket.onerror = () => {{}};
        }} catch(e) {{
            document.getElementById('nca-status').textContent = '❌ Не удалось подключиться к NCALayer';
            document.getElementById('nca-status').className = 'ncalayer-status error';
        }}
    }}

    // ── Sign via NCALayer (Desktop) ──
    async function signViaNCALayer() {{
        const btn = document.getElementById('sign-nca-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Подготовка...';

        try {{
            // 1. Get document bytes as base64 from server
            const docResp = await fetch(`${{API_BASE}}/edo/public/${{SHARE_UUID}}/pdf-b64`);
            const docData = await docResp.json();
            if (!docData.success) throw new Error(docData.error || 'Ошибка получения документа');

            btn.innerHTML = '<span class="spinner"></span> Выберите сертификат в NCALayer...';

            // 2. Send to NCALayer for CMS signing
            const signResult = await new Promise((resolve, reject) => {{
                const handler = (event) => {{
                    const result = JSON.parse(event.data);
                    ncaSocket.removeEventListener('message', handler);
                    if (result.code === "200") {{
                        resolve(result.responseObject);
                    }} else if (result.code === "NONE") {{
                        reject(new Error("Вы отменили выбор сертификата."));
                    }} else {{
                        reject(new Error("NCALayer: " + (result.message || 'Неизвестная ошибка')));
                    }}
                }};
                ncaSocket.addEventListener('message', handler);
                ncaSocket.send(JSON.stringify({{
                    module: "kz.gov.pki.knca.commonUtils",
                    method: "createCMSSignatureFromBase64",
                    args: ["PKCS12", "SIGNATURE", docData.pdf_b64, false]
                }}));
            }});

            btn.innerHTML = '<span class="spinner"></span> Сохранение подписи...';

            // 3. Send CMS signature to our server
            const saveResp = await fetch(`${{API_BASE}}/edo/public/${{SHARE_UUID}}/sign`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ cms_signature_b64: signResult }})
            }});
            const saveData = await saveResp.json();

            if (saveData.success) {{
                showSuccess();
            }} else {{
                throw new Error(saveData.error || 'Ошибка сохранения подписи');
            }}
        }} catch(err) {{
            alert('Ошибка: ' + err.message);
            btn.disabled = false;
            btn.innerHTML = '<span class="material-icons-round">security</span> Подписать через NCALayer';
        }}
    }}

    // ── Sign via eGov Mobile (Phone) ──
    async function signViaEgovMobile() {{
        const btn = document.getElementById('sign-egov-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Регистрация подписи...';

        try {{
            // 1. Initiate signing on server (returns SIGEX deeplink)
            const resp = await fetch(`${{API_BASE}}/edo/public/${{SHARE_UUID}}/sign-mobile`, {{
                method: 'POST'
            }});
            const data = await resp.json();

            if (!data.success) throw new Error(data.error || 'Ошибка регистрации');

            egovMobileLink = data.egov_mobile_link;

            // 2. Show waiting section
            document.getElementById('sign-section').classList.add('hidden');
            document.getElementById('waiting-section').classList.remove('hidden');

            // 3. Open eGov Mobile
            if (egovMobileLink) {{
                window.location.href = egovMobileLink;
            }}

            // 4. Start polling for signature
            pollForSignature(data.signing_session_id);

        }} catch(err) {{
            alert('Ошибка: ' + err.message);
            btn.disabled = false;
            btn.innerHTML = '<span class="material-icons-round">phone_iphone</span> Подписать через eGov Mobile';
        }}
    }}

    function openEgovAgain() {{
        if (egovMobileLink) window.location.href = egovMobileLink;
    }}

    function pollForSignature(sessionId) {{
        let attempts = 0;
        const maxAttempts = 120;
        const timer = setInterval(async () => {{
            attempts++;
            try {{
                const resp = await fetch(`${{API_BASE}}/edo/public/${{SHARE_UUID}}/sign-status?session_id=${{sessionId}}`);
                const data = await resp.json();
                if (data.status === 'signed') {{
                    clearInterval(timer);
                    showSuccess();
                }}
            }} catch(e) {{}}
            if (attempts >= maxAttempts) {{
                clearInterval(timer);
                document.getElementById('waiting-text').textContent = 'Время истекло. Попробуйте снова.';
            }}
        }}, 3000);
    }}

    function showSuccess() {{
        document.getElementById('sign-section').classList.add('hidden');
        document.getElementById('waiting-section').classList.add('hidden');
        document.getElementById('success-section').classList.remove('hidden');
        document.getElementById('success-section').innerHTML = `
            <div class="success-card">
                <div class="success-icon">✅</div>
                <h3 style="font-weight: 700; margin-bottom: 4px;">Документ подписан!</h3>
                <p style="color: #6b7280; font-size: 14px;">Ваша электронная подпись успешно наложена</p>
            </div>
        `;
    }}

    async function rejectDocument() {{
        const comment = prompt('Укажите причину отклонения:');
        if (comment === null) return;
        try {{
            const resp = await fetch(`${{API_BASE}}/edo/public/${{SHARE_UUID}}/reject`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ comment }})
            }});
            const data = await resp.json();
            if (data.success) {{
                document.getElementById('sign-section').innerHTML = `
                    <div class="card" style="text-align: center; padding: 24px;">
                        <span style="font-size: 36px;">❌</span>
                        <h3 style="margin-top: 8px; font-weight: 700;">Документ отклонён</h3>
                        <p style="color: #8e8e93; font-size: 14px; margin-top: 4px;">Причина: ${{comment || 'Не указана'}}</p>
                    </div>
                `;
            }} else {{
                alert('Ошибка: ' + (data.error || 'Не удалось отклонить'));
            }}
        }} catch(err) {{
            alert('Ошибка: ' + err.message);
        }}
    }}

    function downloadPdf() {{
        window.open(`${{API_BASE}}/edo/public/${{SHARE_UUID}}/pdf`, '_blank');
    }}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ──────────────────────────────────────────────
# GET /edo/public/{share_uuid}/pdf-b64 — PDF as Base64 (for NCALayer signing)
# ──────────────────────────────────────────────
@router.get("/public/{share_uuid}/pdf-b64")
async def get_public_pdf_b64(share_uuid: str, db: Session = Depends(get_db)):
    """Return PDF document bytes as base64 for NCALayer CMS signing."""
    from app.core import s3
    
    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()
    if not share:
        return JSONResponse({"success": False, "error": "Документ не найден"}, status_code=404)

    doc = db.query(Document).filter(Document.id == share.document_id).first()
    if not doc or not doc.pdf_path:
        return JSONResponse({"success": False, "error": "PDF не найден"}, status_code=404)

    pdf_bytes = await s3.download_file(doc.pdf_path)

    if not pdf_bytes:
        return JSONResponse({"success": False, "error": f"Файл не найден в S3"}, status_code=404)

    return {
        "success": True,
        "pdf_b64": base64.b64encode(pdf_bytes).decode("ascii"),
        "size_bytes": len(pdf_bytes),
        "md5": hashlib.md5(pdf_bytes).hexdigest(),
    }


# ──────────────────────────────────────────────
# GET /edo/public/{share_uuid}/pdf — Download PDF
# ──────────────────────────────────────────────
@router.get("/public/{share_uuid}/pdf")
async def download_public_pdf(share_uuid: str, db: Session = Depends(get_db)):
    """Download the PDF file."""
    from fastapi.responses import Response
    from app.core import s3
    import os

    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Документ не найден")

    doc = db.query(Document).filter(Document.id == share.document_id).first()
    if not doc or not doc.pdf_path:
        raise HTTPException(status_code=404, detail="PDF не найден")

    pdf_bytes = await s3.download_file(doc.pdf_path)

    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Файл не найден в S3")

    filename = f"{doc.title or 'document'}.pdf"
    if doc.pdf_path.endswith("_stamped.pdf"):
        filename = filename.replace(".pdf", "_stamped.pdf")

    import urllib.parse
    encoded_filename = urllib.parse.quote(filename)

    return Response(
        pdf_bytes, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"}
    )


# ──────────────────────────────────────────────
# POST /edo/public/{share_uuid}/sign — Save CMS signature from NCALayer
# ──────────────────────────────────────────────
@router.post("/public/{share_uuid}/sign")
async def save_guest_signature(
    share_uuid: str,
    req: GuestSignRequest,
    db: Session = Depends(get_db),
):
    """Save CMS signature submitted by counterparty via NCALayer."""
    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()
    if not share:
        return JSONResponse({"success": False, "error": "Документ не найден"}, status_code=404)

    doc = db.query(Document).filter(Document.id == share.document_id).first()
    if not doc:
        return JSONResponse({"success": False, "error": "Документ удалён"}, status_code=404)

    # Check not already signed by receiver
    existing = db.query(Signature).filter(
        Signature.document_id == doc.id,
        Signature.signer_role == "receiver",
    ).first()
    if existing:
        return JSONResponse({"success": False, "error": "Документ уже подписан получателем"}, status_code=400)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    sig = Signature(
        document_id=doc.id,
        signer_iin=req.signer_iin or "",
        signer_name=req.signer_name or "Контрагент",
        signer_org_name=req.signer_org or "",
        signer_role="receiver",
        certificate_serial=req.certificate_serial or "",
        signature_data=req.cms_signature_b64,
        signed_at=now,
    )
    db.add(sig)

    # Update document status
    doc.edo_status = "signed_both"
    doc.countersigned_at = now

    # Update share
    share.signed_at = now

    db.commit()
    logger.info("Guest signature saved for doc %d (share %s)", doc.id, share_uuid)

    # Auto-stamp PDF when both parties have signed
    try:
        from app.services.stamp_trigger import maybe_stamp_document
        await maybe_stamp_document(db, doc.id)
    except Exception as stamp_err:
        logger.warning("PDF stamp failed (non-critical): %s", stamp_err)

    return {"success": True, "message": "Подпись сохранена"}


# ──────────────────────────────────────────────
# POST /edo/public/{share_uuid}/sign-mobile — Initiate eGov Mobile signing for guest
# ──────────────────────────────────────────────
@router.post("/public/{share_uuid}/sign-mobile")
async def initiate_guest_mobile_sign(
    share_uuid: str,
    db: Session = Depends(get_db),
):
    """Register SIGEX session for counterparty signing via eGov Mobile."""
    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()
    if not share:
        return JSONResponse({"success": False, "error": "Документ не найден"}, status_code=404)

    doc = db.query(Document).filter(Document.id == share.document_id).first()
    if not doc:
        return JSONResponse({"success": False, "error": "Документ удалён"}, status_code=404)

    if not doc.pdf_path:
        return JSONResponse({"success": False, "error": "PDF не найден"}, status_code=400)

    import os
    pdf_path = doc.pdf_path
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join("/app", pdf_path)

    if not os.path.exists(pdf_path):
        return JSONResponse({"success": False, "error": "Файл не найден"}, status_code=404)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    try:
        # Register SIGEX session
        reg = await sigex.register_signing(
            description=f"Подписание: {doc.title or 'Документ'}"
        )

        # Create signing session in DB
        data_url = reg.get("dataURL", "")
        session = SigningSession(
            document_id=doc.id,
            user_id=doc.user_id,  # owner's user_id
            signer_role="receiver",
            sign_url=reg.get("signURL", ""),
            status="pending",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Queue background task to send data
        import asyncio
        asyncio.create_task(_send_guest_data_background(
            data_url=data_url,
            pdf_bytes=pdf_bytes,
            doc_title=doc.title or "Документ",
            signing_session_id=session.id,
            document_id=doc.id,
            share_uuid=share_uuid,
        ))

        return {
            "success": True,
            "signing_session_id": session.id,
            "egov_mobile_link": reg.get("eGovMobileLaunchLink", ""),
            "egov_business_link": reg.get("eGovBusinessLaunchLink", ""),
            "qr_code_b64": reg.get("qrCode", ""),
        }

    except Exception as exc:
        logger.error("Guest mobile sign error: %s", exc)
        return JSONResponse(
            {"success": False, "error": str(exc)},
            status_code=500,
        )


async def _send_guest_data_background(
    data_url: str,
    pdf_bytes: bytes,
    doc_title: str,
    signing_session_id: int,
    document_id: int,
    share_uuid: str,
):
    """Background: send PDF data to SIGEX, then poll for signature."""
    document_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    try:
        await sigex.send_data_to_sign(
            data_url=data_url,
            document_b64=document_b64,
            names=[doc_title, doc_title, doc_title],
            mime="@file/pdf",
        )
        logger.info("Guest SIGEX data sent for doc %d", document_id)
    except Exception as exc:
        logger.error("Guest SIGEX send_data failed: %s", exc)
        return

    # Poll for signatures
    from app.core.db import SessionLocal
    try:
        sign_session_db = None
        db = SessionLocal()
        try:
            sign_session_db = db.query(SigningSession).filter(
                SigningSession.id == signing_session_id
            ).first()
            sign_url = sign_session_db.sign_url if sign_session_db else ""
        finally:
            db.close()

        if not sign_url:
            return

        signatures = await sigex.poll_signatures(
            sign_url=sign_url,
            max_wait_seconds=300,
            poll_interval=3.0,
        )

        if not signatures:
            return

        cms_b64 = signatures[0]

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            sig = Signature(
                document_id=document_id,
                signer_iin="",
                signer_name="Контрагент",
                signer_org_name="",
                signer_role="receiver",
                signature_data=cms_b64,
                signed_at=now,
            )
            db.add(sig)

            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.edo_status = "signed_both"
                doc.countersigned_at = now

            session = db.query(SigningSession).filter(
                SigningSession.id == signing_session_id
            ).first()
            if session:
                session.status = "signed"

            share = db.query(DocumentShare).filter(
                DocumentShare.share_uuid == share_uuid
            ).first()
            if share:
                share.signed_at = now

            db.commit()
            logger.info("Guest eGov Mobile signature saved for doc %d", document_id)

            # Auto-stamp PDF
            try:
                from app.services.stamp_trigger import maybe_stamp_document
                await maybe_stamp_document(db, document_id)
            except Exception as stamp_err:
                logger.warning("PDF stamp failed (non-critical): %s", stamp_err)
        finally:
            db.close()

    except Exception as exc:
        logger.error("Guest poll_signatures error: %s", exc)


# ──────────────────────────────────────────────
# GET /edo/public/{share_uuid}/sign-status — Poll for eGov Mobile signature status
# ──────────────────────────────────────────────
@router.get("/public/{share_uuid}/sign-status")
async def guest_sign_status(
    share_uuid: str,
    session_id: int = 0,
    db: Session = Depends(get_db),
):
    """Check if the guest signing session has completed."""
    if session_id:
        session = db.query(SigningSession).filter(
            SigningSession.id == session_id,
        ).first()
        if session and session.status == "signed":
            return {"status": "signed"}

    # Also check if receiver signature exists
    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()
    if share:
        sig = db.query(Signature).filter(
            Signature.document_id == share.document_id,
            Signature.signer_role == "receiver",
        ).first()
        if sig:
            return {"status": "signed"}

    return {"status": "pending"}


# ──────────────────────────────────────────────
# POST /edo/public/{share_uuid}/reject — Reject document
# ──────────────────────────────────────────────
@router.post("/public/{share_uuid}/reject")
async def reject_document(
    share_uuid: str,
    req: GuestRejectRequest,
    db: Session = Depends(get_db),
):
    """Counterparty rejects the document."""
    share = db.query(DocumentShare).filter(
        DocumentShare.share_uuid == share_uuid,
    ).first()
    if not share:
        return JSONResponse({"success": False, "error": "Документ не найден"}, status_code=404)

    doc = db.query(Document).filter(Document.id == share.document_id).first()
    if not doc:
        return JSONResponse({"success": False, "error": "Документ удалён"}, status_code=404)

    doc.edo_status = "rejected"
    db.commit()

    logger.info("Document %d rejected via share %s. Comment: %s", doc.id, share_uuid, req.comment)
    return {"success": True, "message": "Документ отклонён"}


# ── Error HTML helper ──
def _error_html(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #f2f2f7; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: #fff; border-radius: 16px; padding: 32px; text-align: center; max-width: 400px; }}
        h2 {{ margin-bottom: 8px; }}
        p {{ color: #8e8e93; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>❌ {title}</h2>
        <p>{message}</p>
    </div>
</body>
</html>"""


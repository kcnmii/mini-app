"""
EDO Test Page — Standalone SIGEX signing test endpoint.

Serves an HTML page at /edo/test-sigex-page that:
  1. Generates a tiny XML test document
  2. Registers signing via SIGEX
  3. Shows QR code + eGov Mobile deeplink
  4. Sends data to SIGEX in background (after user opens eGov Mobile)
  5. Polls for CMS signature result
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from datetime import datetime

import httpx
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/edo", tags=["edo-test"])

SIGEX_BASE = "https://sigex.kz"

# Store active test sessions in memory (simple dict, not for production)
_test_sessions: dict[str, dict] = {}


def _generate_test_xml() -> tuple[str, str]:
    """Generate a small XML test document. Returns (xml_string, md5_hash)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<invoice>
  <number>TEST-001</number>
  <date>{now}</date>
  <supplier>
    <name>ТОО "Тест Компани"</name>
    <bin>140240030432</bin>
    <address>г. Алматы, ул. Тестовая 1</address>
  </supplier>
  <buyer>
    <name>ИП Тестов</name>
    <bin>960821350108</bin>
  </buyer>
  <items>
    <item>
      <name>Консультационные услуги</name>
      <quantity>1</quantity>
      <unit>услуга</unit>
      <price>50000</price>
      <total>50000</total>
    </item>
  </items>
  <total_sum>50000</total_sum>
  <currency>KZT</currency>
</invoice>"""
    md5 = hashlib.md5(xml.encode("utf-8")).hexdigest()
    return xml, md5


# ──────────────────────────────────────────────
# GET /edo/test-sigex-page — HTML test page
# ──────────────────────────────────────────────
@router.get("/test-sigex-page", response_class=HTMLResponse)
async def test_sigex_page():
    html = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIGEX Test — doc-mini-app</title>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro', 'Segoe UI', sans-serif;
            background: #0d1117; color: #e6edf3;
            min-height: 100vh; padding: 20px;
            display: flex; flex-direction: column; align-items: center;
        }
        .container { max-width: 480px; width: 100%; }
        h1 { font-size: 22px; font-weight: 700; margin-bottom: 8px; text-align: center; }
        .subtitle { font-size: 13px; color: #8b949e; text-align: center; margin-bottom: 24px; }
        .card {
            background: #161b22; border: 1px solid #30363d;
            border-radius: 16px; padding: 20px; margin-bottom: 16px;
        }
        .card-title {
            font-size: 14px; font-weight: 600; color: #8b949e;
            margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .xml-preview {
            background: #0d1117; border: 1px solid #30363d;
            border-radius: 10px; padding: 12px; font-family: 'JetBrains Mono', monospace;
            font-size: 11px; color: #7ee787; white-space: pre-wrap;
            max-height: 200px; overflow-y: auto; line-height: 1.5;
        }
        .info-row {
            display: flex; justify-content: space-between; align-items: center;
            padding: 8px 0; border-bottom: 1px solid #21262d;
            font-size: 14px;
        }
        .info-row:last-child { border-bottom: none; }
        .info-label { color: #8b949e; }
        .info-value { color: #e6edf3; font-weight: 600; font-family: monospace; font-size: 12px; }
        .btn {
            display: flex; align-items: center; justify-content: center; gap: 8px;
            width: 100%; height: 52px; border: none; border-radius: 14px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #238636, #2ea043);
            color: #fff; box-shadow: 0 4px 16px rgba(35,134,54,0.3);
        }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(35,134,54,0.4); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-egov {
            background: linear-gradient(135deg, #1f6feb, #388bfd);
            color: #fff; box-shadow: 0 4px 16px rgba(31,111,235,0.3);
            text-decoration: none; margin-bottom: 8px;
        }
        .btn-egov:hover { transform: translateY(-1px); }
        .qr-container {
            display: flex; flex-direction: column; align-items: center;
            padding: 16px; background: #fff; border-radius: 12px; margin: 12px 0;
        }
        .qr-container img { width: 200px; height: 200px; }
        .status-badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 600;
        }
        .status-pending { background: rgba(227,179,65,0.15); color: #e3b341; }
        .status-sending { background: rgba(31,111,235,0.15); color: #58a6ff; }
        .status-waiting { background: rgba(163,113,247,0.15); color: #a371f7; }
        .status-signed { background: rgba(46,160,67,0.15); color: #3fb950; }
        .status-error { background: rgba(248,81,73,0.15); color: #f85149; }
        .spinner {
            width: 16px; height: 16px; border: 2px solid currentColor;
            border-top-color: transparent; border-radius: 50%;
            animation: spin 0.8s linear infinite; display: inline-block;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .log-area {
            background: #0d1117; border: 1px solid #30363d;
            border-radius: 10px; padding: 12px; font-family: monospace;
            font-size: 11px; color: #8b949e; max-height: 300px;
            overflow-y: auto; line-height: 1.7;
        }
        .log-area .success { color: #3fb950; }
        .log-area .error { color: #f85149; }
        .log-area .info { color: #58a6ff; }
        .result-card {
            background: #0d2211; border: 1px solid #238636;
            border-radius: 16px; padding: 20px; margin-bottom: 16px;
            display: none;
        }
        .hidden { display: none; }
        .material-icons-round { font-size: 20px; vertical-align: middle; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 SIGEX Signing Test</h1>
        <p class="subtitle">Тестирование подписания через eGov Mobile</p>

        <!-- Step 1: Document Preview -->
        <div class="card" id="doc-card">
            <div class="card-title">📄 Тестовый XML документ</div>
            <div class="xml-preview" id="xml-preview">Загрузка...</div>
            <div style="margin-top: 12px;">
                <div class="info-row">
                    <span class="info-label">MD5 хеш</span>
                    <span class="info-value" id="md5-hash">—</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Размер</span>
                    <span class="info-value" id="doc-size">—</span>
                </div>
            </div>
        </div>

        <!-- Start Button -->
        <button class="btn btn-primary" id="start-btn" onclick="startSigning()">
            <span class="material-icons-round">draw</span>
            Начать подписание
        </button>

        <!-- Step 2: QR + Links (hidden initially) -->
        <div class="card hidden" id="qr-card">
            <div class="card-title">📱 Подписание через eGov Mobile</div>
            <div style="text-align: center; margin-bottom: 12px;">
                <span class="status-badge" id="status-badge">
                    <span class="spinner"></span> Инициализация...
                </span>
            </div>
            
            <a class="btn btn-egov hidden" id="egov-link" href="#" target="_blank">
                <span class="material-icons-round">phone_iphone</span>
                Открыть eGov Mobile
            </a>
            <a class="btn btn-egov hidden" id="egov-biz-link" href="#" target="_blank" style="background: linear-gradient(135deg, #8957e5, #a371f7);">
                <span class="material-icons-round">business</span>
                Открыть eGov Business
            </a>
            
            <div class="qr-container hidden" id="qr-wrap">
                <img id="qr-img" src="" alt="QR Code">
                <div style="color: #24292f; font-size: 12px; margin-top: 8px; font-weight: 500;">
                    Отсканируйте QR в eGov Mobile
                </div>
            </div>
        </div>

        <!-- Step 3: Result (hidden initially) -->
        <div class="result-card" id="result-card">
            <div class="card-title" style="color: #3fb950;">✅ Подпись получена</div>
            <div class="info-row">
                <span class="info-label">Статус</span>
                <span class="info-value" id="result-status" style="color: #3fb950;">—</span>
            </div>
            <div class="info-row">
                <span class="info-label">CMS подпись (base64)</span>
                <span class="info-value" id="result-sig" style="font-size: 10px; word-break: break-all; max-width: 60%;">—</span>
            </div>
        </div>

        <!-- Log -->
        <div class="card">
            <div class="card-title">📋 Лог</div>
            <div class="log-area" id="log"></div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;
        let currentSession = null;
        let pollTimer = null;

        function log(msg, type = '') {
            const el = document.getElementById('log');
            const ts = new Date().toLocaleTimeString('ru-RU');
            el.innerHTML += `<div class="${type}">[${ts}] ${msg}</div>`;
            el.scrollTop = el.scrollHeight;
        }

        // Load doc on page open
        async function loadDoc() {
            try {
                const resp = await fetch(`${API_BASE}/edo/test-sigex-generate`);
                const data = await resp.json();
                document.getElementById('xml-preview').textContent = data.xml_content;
                document.getElementById('md5-hash').textContent = data.md5;
                document.getElementById('doc-size').textContent = data.size_bytes + ' bytes';
                log('Тестовый XML документ сгенерирован', 'success');
            } catch (e) {
                log('Ошибка загрузки документа: ' + e.message, 'error');
            }
        }

        async function startSigning() {
            const btn = document.getElementById('start-btn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Регистрация в SIGEX...';

            try {
                log('Отправка запроса на регистрацию в SIGEX...', 'info');
                const resp = await fetch(`${API_BASE}/edo/test-sigex-sign`, { method: 'POST' });
                const data = await resp.json();

                if (!data.success) {
                    throw new Error(data.error || 'Unknown error');
                }

                currentSession = data;
                log('SIGEX сессия зарегистрирована!', 'success');
                log('dataURL: ' + data.data_url, 'info');
                log('signURL: ' + data.sign_url, 'info');

                // Show QR card
                document.getElementById('qr-card').classList.remove('hidden');
                
                const badge = document.getElementById('status-badge');
                badge.className = 'status-badge status-pending';
                badge.innerHTML = '<span class="spinner"></span> Откройте eGov Mobile и подпишите';

                // Show eGov links
                if (data.egov_mobile_link) {
                    const egovLink = document.getElementById('egov-link');
                    egovLink.href = data.egov_mobile_link;
                    egovLink.classList.remove('hidden');
                    log('eGov Mobile link: ' + data.egov_mobile_link, 'info');
                }
                if (data.egov_business_link) {
                    const egovBizLink = document.getElementById('egov-biz-link');
                    egovBizLink.href = data.egov_business_link;
                    egovBizLink.classList.remove('hidden');
                }

                // Show QR
                if (data.qr_code_b64) {
                    const qrWrap = document.getElementById('qr-wrap');
                    document.getElementById('qr-img').src = 'data:image/gif;base64,' + data.qr_code_b64;
                    qrWrap.classList.remove('hidden');
                }

                // Now send data in background via API
                log('Отправка данных в SIGEX (фоновый процесс)...', 'info');
                fetch(`${API_BASE}/edo/test-sigex-send-data`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        data_url: data.data_url,
                        xml_b64: data.xml_b64,
                    }),
                }).then(r => r.json()).then(result => {
                    if (result.success) {
                        log('Данные отправлены в SIGEX!', 'success');
                        badge.className = 'status-badge status-waiting';
                        badge.innerHTML = '<span class="spinner"></span> Ожидание подписи в eGov Mobile...';
                    } else {
                        log('Ошибка отправки данных: ' + result.error, 'error');
                    }
                }).catch(e => {
                    log('Ошибка сети при отправке: ' + e.message, 'error');
                });

                // Start polling for signature
                startPolling(data.sign_url);

            } catch (e) {
                log('Ошибка: ' + e.message, 'error');
                btn.disabled = false;
                btn.innerHTML = '<span class="material-icons-round">draw</span> Попробовать снова';
            }
        }

        function startPolling(signUrl) {
            log('Начинаем опрос SIGEX на наличие подписи...', 'info');
            let attempts = 0;
            const maxAttempts = 120; // 6 minutes

            pollTimer = setInterval(async () => {
                attempts++;
                try {
                    const resp = await fetch(`${API_BASE}/edo/test-sigex-poll?sign_url=${encodeURIComponent(signUrl)}`);
                    const data = await resp.json();

                    if (data.status === 'signed') {
                        clearInterval(pollTimer);
                        log('🎉 ПОДПИСЬ ПОЛУЧЕНА!', 'success');
                        log('CMS подпись (первые 100 символов): ' + data.signature_b64.substring(0, 100) + '...', 'success');
                        
                        const badge = document.getElementById('status-badge');
                        badge.className = 'status-badge status-signed';
                        badge.innerHTML = '✅ Подписано';

                        // Show result
                        const resultCard = document.getElementById('result-card');
                        resultCard.style.display = 'block';
                        document.getElementById('result-status').textContent = 'Подписано ЭЦП';
                        document.getElementById('result-sig').textContent = data.signature_b64.substring(0, 120) + '...';
                    } else if (attempts % 10 === 0) {
                        log(`Попытка ${attempts}/${maxAttempts} — подпись ещё не получена`, 'info');
                    }
                } catch (e) {
                    // silent retry
                }

                if (attempts >= maxAttempts) {
                    clearInterval(pollTimer);
                    log('Таймаут! Подпись не получена за 6 минут.', 'error');
                    const badge = document.getElementById('status-badge');
                    badge.className = 'status-badge status-error';
                    badge.innerHTML = '❌ Таймаут';
                }
            }, 3000);
        }

        loadDoc();
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


# ──────────────────────────────────────────────
# GET /edo/test-sigex-generate — Generate test XML
# ──────────────────────────────────────────────
@router.get("/test-sigex-generate")
async def test_sigex_generate():
    xml_content, md5 = _generate_test_xml()
    return {
        "xml_content": xml_content,
        "md5": md5,
        "size_bytes": len(xml_content.encode("utf-8")),
    }


# ──────────────────────────────────────────────
# POST /edo/test-sigex-sign — Register signing on SIGEX
# ──────────────────────────────────────────────
@router.post("/test-sigex-sign")
async def test_sigex_sign():
    try:
        xml_content, md5 = _generate_test_xml()
        xml_b64 = base64.b64encode(xml_content.encode("utf-8")).decode("ascii")

        # Step 1: Register signing on SIGEX
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{SIGEX_BASE}/api/egovQr",
                json={"description": f"Тест подписания doc-mini-app | MD5: {md5}"},
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("message"):
            return JSONResponse(
                {"success": False, "error": f"SIGEX error: {data['message']}"},
                status_code=502,
            )

        session_id = data["dataURL"].split("/")[-1]
        _test_sessions[session_id] = {
            "data_url": data["dataURL"],
            "sign_url": data["signURL"],
            "xml_b64": xml_b64,
            "md5": md5,
            "created_at": datetime.now().isoformat(),
        }

        logger.info("Test SIGEX session registered: %s", session_id)

        return {
            "success": True,
            "session_id": session_id,
            "data_url": data["dataURL"],
            "sign_url": data["signURL"],
            "egov_mobile_link": data.get("eGovMobileLaunchLink", ""),
            "egov_business_link": data.get("eGovBusinessLaunchLink", ""),
            "qr_code_b64": data.get("qrCode", ""),
            "xml_b64": xml_b64,
            "md5": md5,
        }

    except Exception as exc:
        logger.error("test_sigex_sign error: %s", exc)
        return JSONResponse(
            {"success": False, "error": str(exc)},
            status_code=500,
        )


# ──────────────────────────────────────────────
# POST /edo/test-sigex-send-data — Send document data to SIGEX
# This is called AFTER the user has opened eGov Mobile
# Uses long timeout because SIGEX blocks until mobile connects
# ──────────────────────────────────────────────
@router.post("/test-sigex-send-data")
async def test_sigex_send_data(body: dict):
    data_url = body.get("data_url", "")
    xml_b64 = body.get("xml_b64", "")

    if not data_url or not xml_b64:
        return JSONResponse({"success": False, "error": "Missing data_url or xml_b64"}, status_code=400)

    payload = {
        "signMethod": "CMS_SIGN_ONLY",
        "documentsToSign": [
            {
                "id": 1,
                "nameRu": "Тестовый счёт-фактура",
                "nameKz": "Тест шот-фактура",
                "nameEn": "Test invoice",
                "meta": [
                    {"name": "Приложение", "value": "doc-mini-app"},
                    {"name": "Тест", "value": "да"},
                ],
                "document": {
                    "file": {
                        "mime": "",
                        "data": xml_b64,
                    }
                },
            }
        ],
    }

    last_error = None
    for attempt in range(25):
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(65.0, connect=10.0)
            ) as client:
                resp = await client.post(data_url, json=payload)
                resp.raise_for_status()
                result = resp.json()

            if result.get("message"):
                return JSONResponse(
                    {"success": False, "error": f"SIGEX: {result['message']}"},
                    status_code=502,
                )

            logger.info("Test SIGEX data sent successfully on attempt %d", attempt + 1)
            return {"success": True, "attempt": attempt + 1}

        except (httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            last_error = str(exc)
            logger.warning("SIGEX send_data attempt %d timed out, retrying...", attempt + 1)
            await asyncio.sleep(0.5)
        except Exception as exc:
            last_error = str(exc)
            logger.warning("SIGEX send_data attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(1.0)

    return JSONResponse(
        {"success": False, "error": f"Failed after 25 attempts: {last_error}"},
        status_code=502,
    )


# ──────────────────────────────────────────────
# GET /edo/test-sigex-poll — Check for signatures
# ──────────────────────────────────────────────
@router.get("/test-sigex-poll")
async def test_sigex_poll(sign_url: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
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
                        return {
                            "status": "signed",
                            "signature_b64": signatures[0],
                            "signature_count": len(signatures),
                        }
            return {"status": "pending"}
    except Exception:
        return {"status": "pending"}

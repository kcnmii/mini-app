# 🔷 Этап 2 — Обмен документами: Детальный план

> **Цель**: Превратить одностороннее подписание в полноценный двусторонний ЭДО с гостевым окном для контрагентов, штампом ЭЦП на PDF и поддержкой NCALayer для десктопа.

---

## Обзор: Что именно строим

### Эталонный пример (скриншоты из Учёт.ЭДО)

**Шапка PDF** (вверху документа):
![Шапка ЭДО — MD5 хеш, ссылки для отправителя/получателя](/home/observer/.gemini/antigravity/brain/285aeba7-c89f-4d36-a0d7-4e4aa27a574a/stamp_header.png)

**Подвал PDF** (внизу документа — блок «подпись»):
![Штамп ЭЦП — данные подписантов, QR-коды, серийные номера сертификатов](/home/observer/.gemini/antigravity/brain/285aeba7-c89f-4d36-a0d7-4e4aa27a574a/stamp_footer.png)

---

## 📋 План задач (по порядку реализации)

### 2.1 Гостевая страница `/doc/{uuid}` (публичная, без авторизации)

> [!IMPORTANT]
> Это ключевая точка входа для контрагента. Он получает ссылку в WhatsApp/Email/Telegram и открывает в браузере.

**Что видит контрагент:**
- Превью PDF документа (рендерим страницы как изображения через существующий PDF-превью)
- Информацию: кто отправил, дата, сумма, тип документа
- Список подписей (кто уже подписал, с датой и серийным номером сертификата)
- **Кнопка «Подписать»** → определяет среду:
  - 📱 Телефон → eGov Mobile (через SIGEX deeplink, как в Этапе 1)
  - 💻 ПК → NCALayer (WebSocket `wss://127.0.0.1:13579/`, подпись CMS через PKCS12)
- **Кнопка «Скачать PDF»** → скачивает оригинал
- **Кнопка «Отклонить»** → с полем для комментария

**Бэкенд:**
- `GET /edo/public/{share_uuid}` — уже **частично реализован** в [router.py](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/modules/edo/router.py) (строка 277)
- `GET /edo/guest-page/{share_uuid}` — **новый** эндпоинт, возвращает полную HTML-страницу (как [test_page.py](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/modules/edo/test_page.py))
- `POST /edo/public/{share_uuid}/sign` — **новый**, принимает CMS-подпись от контрагента (роль `receiver`)
- `POST /edo/public/{share_uuid}/reject` — **новый**, отклонение с комментарием

**Фронтенд:**
- Самостоятельная HTML-страница (без React), как [test_page.py](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/modules/edo/test_page.py) — красивая, адаптивная
- Автоопределение устройства: `navigator.userAgent` → мобильный/десктоп
- На мобильном: кнопка «Подписать через eGov Mobile» (SIGEX deeplink)
- На десктопе: кнопка «Подписать через NCALayer» (WebSocket к `wss://127.0.0.1:13579/`)

---

### 2.2 Интеграция NCALayer для десктопных контрагентов

**Как работает NCALayer** (из [esf-test/public/ncalayer.html](file:///home/observer/Projects/new/doc-mini-app/esf-test/public/ncalayer.html)):
1. Браузер открывает WebSocket к `wss://127.0.0.1:13579/`
2. Отправляет JSON-запрос `signXml` или `createCMSSignatureFromBase64`
3. NCALayer показывает окно выбора сертификата
4. Пользователь выбирает [.p12](file:///home/observer/Projects/new/doc-mini-app/esf-test/GOST512_3aebc83943fdecfdb0f91f2b28be77fd38d6de6d.p12) файл + вводит PIN
5. NCALayer возвращает подпись (CMS Base64 или XML Dsig)

**Для подписания документов (АВР/НКЛ):**
```javascript
// CMS-подпись через NCALayer (аналог eGov Mobile CMS_SIGN_ONLY)
const request = {
    module: "kz.gov.pki.knca.commonUtils",
    method: "createCMSSignatureFromBase64",
    args: [
        "PKCS12",           // storeName
        "SIGNATURE",        // keyType
        documentBase64,     // base64-encoded PDF
        false               // не прикреплять данные (detached)
    ]
};
webSocket.send(JSON.stringify(request));
// Ответ: { code: "200", responseObject: "MIIG...==" } — CMS Base64
```

**Для ЭСФ (XML Dsig):**
```javascript
const request = {
    module: "kz.gov.pki.knca.commonUtils",
    method: "signXml",
    args: ["PKCS12", "SIGNATURE", xmlToSign, "", ""]
};
```

---

### 2.3 Штамп ЭЦП на PDF

**НЕ синяя печать!** Как на скриншотах — это текстовый блок в таблице.

**Шапка (верх первой страницы):**
```
Документ зарегистрирован и подписан с помощью сервиса ЭДО (https://edo.doc.onlink.kz)
MD5 Hash документа: b99ff2fd13612cde7bdd8cff673ac1e2
Ссылка на электронный документ:
  Для отправителя — https://doc.onlink.kz/doc/{uuid}?role=sender
  Для получателя  — https://doc.onlink.kz/doc/{uuid}?role=receiver
```

**Подвал (низ последней страницы) — таблица:**
```
┌──────────────────────────────────┬──────────────────────────────────┐
│ подпись                          │                                  │
│                                  │                                  │
│ Отправитель  ТОО "..." (БИН)    │ Получатель   ИП "..." (ИИН)     │
│ ФИО          ИВАНОВ И.И.        │ ФИО          ПЕТРОВ П.П.        │
│ Права        Первый руководитель│ Права        ИП (личный ключ)   │
│ Период       2026-01-21...      │ Период       2026-01-15...      │
│ Серийный №   4452aa18...        │ Серийный №   67dfffa5...        │
│ Дата подписания 2026-02-24 17:50│ Дата подписания 2026-02-26 11:27│
│                                  │                                  │
│ [QR-код: ссылка на проверку]     │ [QR-код: ссылка на проверку]     │
└──────────────────────────────────┴──────────────────────────────────┘
```

**Технически:**
- Используем **reportlab** (Python) для рисования блоков поверх существующего PDF (через `PyPDF2` merge)
- Или **генерируем через docgen** — добавляем секцию подписей в DOCX-шаблон → Gotenberg → PDF
- QR-код генерируем через `qrcode` (Python library) — содержит ссылку `https://doc.onlink.kz/doc/{uuid}`

---

### 2.4 Отправка ссылки контрагенту

**Каналы:**
- **Telegram бот** — сообщение с превью и кнопкой «Открыть документ»
- **Email** — через SMTP (на будущее)
- **Копирование ссылки** — кнопка в Mini App «Поделиться» → копирует ссылку

**В Mini App:**
- Кнопка «Поделиться» под документом → генерирует `share_uuid` → копирует ссылку
- Кнопка «Отправить в Telegram» → отправляет сообщение контрагенту через бота

---

## 🔄 Порядок реализации (по шагам)

| # | Задача | Файлы | Время |
|---|--------|-------|-------|
| 1 | **Бэкенд: API для гостевой страницы** | [edo/router.py](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/modules/edo/router.py) — новые эндпоинты `guest-page`, `public/.../sign`, `public/.../reject` | 30 мин |
| 2 | **Гостевая HTML-страница** | `edo/guest_page.py` — полная HTML с PDF-превью, NCALayer, eGov Mobile | 1.5 часа |
| 3 | **NCALayer JS-модуль** | Встроенный в guest_page: WebSocket → CMS подпись → POST на сервер | 30 мин |
| 4 | **Штамп ЭЦП на PDF** | `services/pdf_stamper.py` — reportlab + PyPDF2, шапка + подвал | 1 час |
| 5 | **Кнопка «Поделиться» в Mini App** | [EdoComponents.tsx](file:///home/observer/Projects/new/doc-mini-app/apps/miniapp/src/components/EdoComponents.tsx), [ViewDocumentView.tsx](file:///home/observer/Projects/new/doc-mini-app/apps/miniapp/src/views/ViewDocumentView.tsx) | 30 мин |
| 6 | **E2E-тестирование** | Полная цепочка от подписания до получения контрагентом | 30 мин |

---

## 🧪 Как проверим по окончанию Фазы 2

### Сценарий тестирования (E2E):

1. **Отправитель** (вы, в мини-аппе):
   - Открываете АВР или НКЛ → «Подробнее» → «Подписать ЭЦП»
   - eGov Mobile открывается → подписываете → возвращаетесь → «Подписано ✅»
   - Нажимаете «Поделиться» → получаете ссылку типа `https://doc.onlink.kz/doc/a1b2c3d4...`

2. **Контрагент** (друг/коллега):
   - Открывает ссылку в **Safari/Chrome на телефоне**:
     - Видит красивую страницу с превью PDF
     - Видит «Подписано отправителем: ФИО, дата»
     - Нажимает «Подписать через eGov Mobile» → подписывает → «Подписано обеими сторонами ✅✅»
   - ИЛИ открывает на **ПК в Chrome**:
     - Видит ту же страницу, но кнопка «Подписать через NCALayer»
     - Запускает NCALayer → выбирает сертификат → подписывает

3. **Результат**:
   - Документ получает статус `signed_both`
   - PDF автоматически обновляется со штампом ЭЦП (шапка + подвал с двумя QR-кодами)
   - Оба подписанта могут скачать финальный PDF

---

## Начинаем с задачи #1 → Бэкенд API для гостевой страницы

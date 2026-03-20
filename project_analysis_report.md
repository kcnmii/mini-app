# 📊 Анализ проекта doc-mini-app — Отчёт о прогрессе

> **Дата**: 20.03.2026  
> **Статус**: MVP Stage 1 — ~65% завершено

---

## 🏗 Архитектура проекта (что есть сейчас)

Проект состоит из **3 сервисов** + инфраструктуры:

| Сервис | Стек | Состояние |
|--------|------|-----------|
| **miniapp** (frontend) | React + TypeScript + Vite | ✅ Работает |
| **api** (backend) | FastAPI + SQLAlchemy | ✅ Работает |
| **docgen** (рендер DOCX) | Node.js + docxtemplater | ✅ Работает |
| **gotenberg** (PDF) | Docker image | ✅ Работает |
| **postgres** | PostgreSQL 16 | ✅ Настроен в docker-compose |
| **bot** | aiogram 3 | ✅ Работает |

---

## ✅ Что уже реализовано

### Модель данных (Backend — [db.py](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/core/db.py))

Очень хорошая база! Уже заложены **9 моделей**:

| Модель | Описание | Оценка |
|--------|----------|--------|
| [Client](file:///home/observer/Projects/new/doc-mini-app/apps/miniapp/src/types.ts#44-54) | Контрагент + связи с accounts/contacts | ✅ Полная |
| [ClientBankAccount](file:///home/observer/Projects/new/doc-mini-app/apps/miniapp/src/types.ts#28-36) | Банк. счета клиентов | ✅ Полная |
| [ClientContact](file:///home/observer/Projects/new/doc-mini-app/apps/miniapp/src/types.ts#37-43) | Контакты клиентов | ✅ Полная |
| [CatalogItem](file:///home/observer/Projects/new/doc-mini-app/apps/miniapp/src/types.ts#55-58) | Каталог товаров/услуг | ✅ Базовая |
| [Invoice](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/core/db.py#79-102) | Счёт — центральная сущность | ✅ Полная (status, due_date, deal_reference, payment_code) |
| [NewInvoiceItem](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/core/db.py#104-115) | Строки счёта | ✅ Полная (с nullable catalog_item_id) |
| [Payment](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/core/db.py#117-128) | Факт оплаты | ✅ Заложена (source: manual/bank_import) |
| [BankAccount](file:///home/observer/Projects/new/doc-mini-app/apps/miniapp/src/types.ts#18-26) | Банк. счета пользователя | ✅ Заложена |
| [BankTransaction](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/core/db.py#141-156) | Строки банковской выписки | ✅ Заложена (matched_invoice_id, is_processed) |
| [SupplierProfile](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/core/db.py#157-180) | Профиль поставщика | ✅ Полная (реквизиты, лого, подпись, печать) |

### Backend API Endpoints (11 модулей)

| Роутер | Эндпоинты | Статус |
|--------|-----------|--------|
| `auth` | Telegram init auth | ✅ |
| `clients` | CRUD клиентов с accounts/contacts | ✅ |
| `catalog` | CRUD каталога | ✅ |
| [invoices](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/modules/invoices/router.py#47-64) | LIST, CREATE, GET, UPDATE STATUS, MARK PAID, DELETE, PDF, Preview | ✅ Расширенный |
| [dashboard](file:///home/observer/Projects/new/doc-mini-app/apps/api/src/app/modules/dashboard/router.py#17-109) | Summary (awaiting/overdue/paid + фильтры по дате) | ✅ |
| `documents` | Старые документы (legacy) | ✅ |
| `render` | DOCX/PDF pipeline | ✅ |
| `telegram_bot` | Отправка счёта в Telegram | ✅ |
| `profile` | CRUD профиля поставщика | ✅ |
| `banks` | Банковские счета пользователя | ✅ |
| `health` | Health check | ✅ |

### Frontend (15 views, 10 components, 8 hooks)

| Функционал | Статус |
|------------|--------|
| Главный экран с **Дашбордом** (Ожидается/Просрочено/Получено) | ✅ |
| Создание счёта с формой | ✅ |
| Список счетов (InvoicesListView) | ✅ |
| Просмотр PDF документа (с конвертацией в PNG для mobile) | ✅ |
| CRUD клиентов + контакты + банк. счета | ✅ |
| CRUD каталога товаров | ✅ |
| Профиль с реквизитами, логотипом, подписью, печатью | ✅ |
| Добавление банковских счетов | ✅ |
| Выбор банка (BankPickerView) | ✅ |
| Фильтр по датам (DateFilterView) | ✅ |
| Кнопка «Загрузить выписку» | ✅ (UI есть) |
| Статусы счетов (draft/sent/paid/overdue) | ✅ |
| Отправка в Telegram | ✅ |
| StatusBadge компонент | ✅ |

### Docker & Deployment

- [docker-compose.yaml](file:///home/observer/Projects/new/doc-mini-app/docker-compose.yaml) с **PostgreSQL**, Gotenberg, docgen — ✅ полностью
- Dockerfiles для api, docgen, miniapp — ✅
- Развёрнуто на **Coolify** (doc.onlink.kz) — ✅

---

## 🔴 Критические проблемы (что надо делать СРОЧНО)

### 🎯 Что мы СДЕЛАЛИ (обновлено)

✅ **Самое сложное и критическое позади:**
1. **S3/MinIO хранилище** — теперь все PDF, DOCX и картинки стабильно сохраняются в MinIO. Данные в безопасности и не пропадут при рестартах.
2. **Alembic миграции** — мы настроили грамотное управление базой данных. База больше не сломается при деплое, `0001_baseline` зафиксирован, race condition между API и ботом устранен.

---

## 🟡 Важные недоработки (наш текущий фокус)

### 1. Парсер банковских выписок (в формате 1C)
UI кнопка «Загрузить выписку» есть, но backend парсинг 1C txt выписок **не реализован**. Модели `BankTransaction` и `Payment` уже есть, но:
- Нет endpoint для загрузки TXT формата 1C
- Нет matching engine (БИН+сумма, поиск номера в описании)
- Нет UI подтверждения совпадений

**Приоритет: 🟡 ВАЖНЫЙ** (это ключевая ценность продукта)

### 2. Уведомления / Напоминания через Telegram
- Нет автоматических уведомлений о просроченных счетах
- Нет напоминания «загрузите выписку»  
- Нет push о смене статуса счёта

**Приоритет: 🟡 ВАЖНЫЙ** (retention-feature)

### 3. Экспорт CSV/Excel для бухгалтера
Не реализован. Важен для B2B канала привлечения через бухгалтеров.

**Приоритет: 🟡 СРЕДНИЙ**

---

## 📋 Глобальный план действий по приоритетам

### ✅ Фаза 0 — Инфраструктурные критичные (Завершено!)
- [x] S3/MinIO хранилище для PDF, DOCX, изображений
- [x] Alembic миграции вместо ALTER TABLE хаков
- [x] Стабильная работа PostgreSQL на production

### 🟠 Фаза 1 — Ключевая ценность продукта (Прямо сейчас!)
1. Парсер банковских выписок 1C (.txt UTF-8)
2. Matching engine (БИН + Сумма → автосопоставление)
3. UI подтверждения совпадений (массовое "Отметить как оплачено")
4. Telegram уведомления (просрочки, оплаты, напоминания)

### 🟡 Фаза 2 — Расширение ценности
5. Экспорт CSV/Excel для бухгалтера
6. Генерация Акта из оплаченного счёта
7. Шаблоны повторяющихся счетов
8. Встроенный watermark бренда в PDF (виральный рост)

---

## 📈 Общий прогресс

```text
Архитектура и модели данных:  ████████████████████ 100%
Backend API:                  ████████████████░░░░ 80%
Frontend UI:                  ██████████████░░░░░░ 70%
Deployment/Docker:            ████████████████████ 100%
S3 хранилище (MinIO):         ████████████████████ 100% ✅
Миграции (Alembic):           ████████████████████ 100% ✅
Банковские выписки (1C):      ████░░░░░░░░░░░░░░░░ 20% (модели готовы, нужен парсер)
Уведомления:                  ██░░░░░░░░░░░░░░░░░░ 10%
Экспорт Excel/CSV:            ░░░░░░░░░░░░░░░░░░░░  0%
Акт/Накладная из счёта:       ░░░░░░░░░░░░░░░░░░░░  0%
```

---

## 💡 Итоговая рекомендация

> [!IMPORTANT]
> Инфраструктурный фундамент (БД, Файлы, Docker) теперь **монолитен и готов к production**.
> 
> Следующий шаг: **Парсер 1C выписок + Matching**. Это самая мякотка продукта, которая превращает его из простой выписывалки счетов в умного финансового помощника.

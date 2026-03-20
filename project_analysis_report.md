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

### 1. 💾 Хранилище файлов — НЕТ S3/MinIO!

> [!CAUTION]
> PDF и DOCX файлы хранятся **локально** в `tmp/output`. При перезапуске контейнера или деплое файлы **теряются**! Это самая критическая проблема для production.

**Что нужно:**
- Подключить **MinIO** (self-hosted S3) или **AWS S3 / Cloudflare R2**
- В `docker-compose.yaml` добавить MinIO сервис
- В backend заменить локальное сохранение на загрузку в S3
- PDF preview, скачивание и отправка в Telegram — должны получать файл из S3
- **Приоритет: 🔴 КРИТИЧЕСКИЙ**

### 2. 🗄 SQLite → PostgreSQL — миграция не полная

> [!WARNING]
> В `docker-compose.yaml` PostgreSQL уже настроен, но `config.py` всё ещё по умолчанию fallback на SQLite. Нет настоящей системы миграций (Alembic). Используются ручные `ALTER TABLE IF NOT EXISTS` хаки.

**Что нужно:**
- Интегрировать **Alembic** для миграций
- Убрать хаки с `ALTER TABLE` из `init_db()`
- Убедиться что production использует PostgreSQL через `DATABASE_URL`
- **Приоритет: 🔴 ВЫСОКИЙ**

### 3. 🖼 Загруженные изображения (logo, signature, stamp) — тоже локальные

Файлы логотипа, подписи и печати из `SupplierProfile` хранятся по `logo_path`, `signature_path`, `stamp_path` — всё локально. Те же проблемы что с PDF.

**Приоритет: 🔴 ВЫСОКИЙ** (решается вместе с S3)

---

## 🟡 Важные недоработки (следующий этап)

### 4. Парсер банковских выписок — не реализован

UI кнопка «Загрузить выписку» есть, но backend парсинг CSV выписок (Kaspi/Halyk/Jusan) **не реализован**. Модели `BankTransaction` и `Payment` уже есть, но:
- Нет endpoint для загрузки CSV
- Нет парсеров для разных банков
- Нет matching engine (БИН+сумма, поиск номера в описании)
- Нет UI подтверждения совпадений

**Приоритет: 🟡 ВАЖНЫЙ** (это ключевая ценность продукта по research.md)

### 5. Уведомления / Напоминания через Telegram

- Нет автоматических уведомлений о просроченных счетах
- Нет напоминания «загрузите выписку»  
- Нет push о смене статуса счёта

**Приоритет: 🟡 ВАЖНЫЙ** (retention-feature)

### 6. «Отметить как оплачено» — есть API, проверить UI

Backend endpoint `POST /invoices/{id}/mark-paid` есть и создаёт `Payment`. Нужно убедиться что UI flow полностью работает.

### 7. Экспорт CSV/Excel для бухгалтера

Не реализован. Важен для B2B канала привлечения через бухгалтеров.

**Приоритет: 🟡 СРЕДНИЙ**

### 8. Автогенерация Акта/Накладной из счёта

Нет кнопки «Создать акт» из оплаченного счёта. Модель `Document` есть, но нет связи Invoice → Act/Waybill.

**Приоритет: 🟡 СРЕДНИЙ**

---

## 🟢 Что можно отложить (по рекомендациям research.md)

| Функционал | Почему позже | Рекомендация research.md |
|------------|-------------|-------------------------|
| КП (коммерческие предложения) | Нет стандартного формата, усложнит UI | Этап 2+ |
| Договоры как сущность | У МСБ нет стандарта, `deal_reference` достаточно | Этап 2+ |
| Акты сверки | Делаются раз в квартал, не ежедневная боль | Этап 2 |
| ЭСФ (электронные счета-фактуры) | Сложная интеграция (SOAP/XML/ЭЦП), только для НДС-плательщиков ~20% рынка | Этап 3 (5-10k пользователей) |
| Склад и остатки | Усложнит в мини-1С | Не делать |
| CRM / роли / команды | Размывает фокус | Не делать |
| AI-подсказки | Nice-to-have | После основного функционала |
| Browser auth (Telegram Login Widget) | Не критично для Mini App | Позже |

---

## 📋 Глобальный план действий по приоритетам

### 🔴 Фаза 0 — Инфраструктурные критичные (1-2 недели)

```
1. S3/MinIO хранилище для PDF, DOCX, изображений
2. Alembic миграции вместо ALTER TABLE хаков
3. Проверить что production PostgreSQL работает стабильно
4. Backup стратегия для PostgreSQL
```

### 🟠 Фаза 1 — Ключевая ценность продукта (2-3 недели)

```
5. Парсер банковских выписок (начать с Kaspi CSV)
6. Matching engine (БИН + сумма → автосопоставление)
7. UI подтверждения совпадений
8. Telegram уведомления (просрочки, оплаты, напоминания)
9. Полный flow «Отметить как оплачено» в UI
```

### 🟡 Фаза 2 — Расширение ценности (3-4 недели)

```
10. Экспорт CSV/Excel для бухгалтера
11. Генерация Акта из оплаченного счёта
12. Шаблоны повторяющихся счетов
13. Встроенный watermark бренда в PDF (виральный рост)
14. Генерация Накладной из счёта
```

### 🟢 Фаза 3 — Рост и масштаб

```
15. Акты сверки (report per client)
16. Дебиторка по клиентам (кто должен больше всего)
17. Аналитика денежного потока
18. Партнерская программа для бухгалтеров
19. КП
20. ЭСФ интеграция (при 5-10k пользователей)
```

---

## 🎯 Оценка рекомендаций из research.md

| Рекомендация | Моя оценка | Статус в коде |
|-------------|-----------|---------------|
| Позиционирование: «контроль денег», не «генератор PDF» | ✅ Абсолютно верно | ✅ Dashboard уже реализован с Ожидается/Просрочено/Получено |
| Статусы draft/sent/paid/overdue | ✅ Правильно | ✅ Реализовано и на backend и на frontend |
| due_date для расчёта просрочек | ✅ Критично | ✅ Есть в модели Invoice |
| deal_reference вместо сущности Deal | ✅ Отличное решение для MVP | ✅ Есть в модели Invoice |
| Payments как отдельная сущность | ✅ Верно | ✅ Модель есть, endpoint mark_paid есть |
| BankTransaction для выписок | ✅ Правильная модель | ⚠️ Модель есть, но парсинг не реализован |
| BankAccount пользователя | ✅ Нужно | ✅ Модель и UI есть |
| Каталог необязательный | ✅ Правильно | ✅ Есть возможность ручного ввода + каталог |
| ЭСФ отложить | ✅ Однозначно | ✅ Не делается |
| Вирусный watermark в PDF | ✅ Сильная идея | ❌ Не реализовано |
| Бухгалтеры как канал роста | ✅ Отличная стратегия | ❌ Нужен экспорт CSV |

---

## 📈 Общий прогресс

```
Архитектура и модели данных:  ████████████████████ 90%
Backend API:                  ████████████████░░░░ 80%
Frontend UI:                  ██████████████░░░░░░ 70%
Deployment/Docker:            ████████████████░░░░ 80%
S3 хранилище:                 ░░░░░░░░░░░░░░░░░░░░  0%  🔴
Миграции (Alembic):           ░░░░░░░░░░░░░░░░░░░░  0%  🔴
Банковские выписки:           ████░░░░░░░░░░░░░░░░ 20% (модели есть)
Уведомления:                  ██░░░░░░░░░░░░░░░░░░ 10%
Экспорт CSV:                  ░░░░░░░░░░░░░░░░░░░░  0%
Акт/Накладная из счёта:       ░░░░░░░░░░░░░░░░░░░░  0%
```

---

## 💡 Итоговая рекомендация

> [!IMPORTANT]
> **Сейчас самое важное — две инфраструктурные вещи:**
> 1. **S3 хранилище** — без этого production ненадёжен, файлы теряются
> 2. **Alembic миграции** — без этого любое изменение модели может сломать production базу
> 
> После этого фокус на **парсер выписок + matching** — это то, что превратит продукт из «генератора счетов» в «контроль денег бизнеса».

Архитектура продукта заложена **очень правильно** — модели данных уже соответствуют рекомендациям из research.md. Основная работа теперь в **доведении до production-ready** и реализации matching engine для автоматического сопоставления выписок со счетами.

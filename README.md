# doc-mini-app

Telegram Mini App для быстрого создания счетов на основе DOCX-шаблонов и отправки готового PDF через Telegram.

Сейчас проект находится в стадии локального MVP для тестирования основного сценария:

1. открыть интерфейс
2. создать клиента
3. создать товар
4. собрать счет
5. сгенерировать PDF из DOCX-шаблона
6. отправить документ в Telegram
7. увидеть счет в истории последних документов

## Цель проекта

Продукт задуман как быстрый генератор документов для малого и среднего бизнеса внутри Telegram.

Это не CRM, не ERP и не бухгалтерская система. Основной сценарий:

> пользователь открывает Mini App, создает счет за 1-3 минуты и сразу отправляет его клиенту.

В исходном ТЗ были заявлены:
- счета
- простые КП
- клиенты и контакты
- каталог товаров/услуг
- шаблоны документов
- PDF и опционально DOCX
- история документов
- отправка через Telegram

На текущем этапе в коде реализован упрощенный, но уже рабочий invoice-first MVP. КП пока исключены из UI и отложены на следующий этап.

## Текущий scope

Что уже работает:
- Telegram bot на `aiogram 3`
- backend на `FastAPI`
- frontend на `React + Vite`
- отдельный `docgen` сервис на Node.js с `docxtemplater`
- конвертация DOCX -> PDF через `Gotenberg`
- локальная авторизация Mini App через `initData`
- локальный browser mode для тестирования
- хранение клиентов, товаров и истории счетов в `SQLite`
- отправка PDF счета в Telegram

Что сейчас сознательно не делается:
- КП в интерфейсе
- роли и командная работа
- склад и остатки
- платежи
- WhatsApp API
- сложный универсальный конструктор Word-шаблонов
- production storage и production-ready multi-user data model

## Архитектура

Система разделена на 3 приложения:

- `apps/miniapp` - frontend интерфейс Mini App / browser mode
- `apps/api` - основной backend, Telegram auth, CRUD, рендер pipeline orchestration
- `apps/docgen` - DOCX render service на `docxtemplater`

Дополнительно:
- `templates/system` - системные DOCX-шаблоны и их манифесты
- `data` - локальная SQLite база для тестирования
- `tmp/output` - локально сгенерированные DOCX/PDF
- `scripts/start-dev.sh` / `scripts/stop-dev.sh` - локальный запуск и остановка

### Почему DOCX-first

Ключевое архитектурное решение проекта:

- источником правды для документа является DOCX-шаблон
- шаблон содержит ключи `{...}` и loops для таблиц
- данные подставляются через `docxtemplater`
- полученный DOCX конвертируется в PDF через `Gotenberg`

Pipeline:

1. frontend собирает payload счета
2. backend нормализует и передает payload в `docgen`
3. `docgen` рендерит DOCX из шаблона
4. backend отправляет DOCX в `Gotenberg`
5. получается PDF
6. PDF сохраняется локально в `tmp/output`
7. документ попадает в историю
8. PDF может быть отправлен через Telegram bot

## Стек

### Frontend

- React
- TypeScript
- Vite
- mobile-first UI
- browser mode + Telegram Mini App mode

### Backend

- FastAPI
- Pydantic
- SQLite для локального тестирования
- задел под PostgreSQL/Redis в `.env` и `docker-compose.yml`

### Bot

- aiogram 3
- polling mode
- web_app button для production HTTPS режима
- отправка документов через `sendDocument`

### Documents

- docxtemplater
- Gotenberg

## Актуальное состояние относительно исходного ТЗ

### Реализовано

- Telegram bot
- Telegram Mini App auth endpoint
- локальный browser mode
- создание счета
- генерация PDF
- отправка PDF в Telegram
- клиенты
- товары
- история последних документов
- шаблонный DOCX pipeline

### Частично реализовано

- история документов:
  сейчас хранится локально в SQLite как простая история счетов
- авторизация:
  Mini App auth реализована, browser auth через Telegram Login Widget пока не внедрена
- storage:
  production storage не подключен, локально файлы лежат в `tmp/output`

### Пока не реализовано

- простые КП
- контакты как отдельная сущность
- полноценные counterparties / company detail forms
- bank accounts
- группы каталога
- статусная модель документа (`draft/generated/shared/archived`)
- DOCX download endpoint
- шаблоны пользователя
- AI-функции
- production PostgreSQL persistence
- S3/MinIO integration как основной storage

## Структура репозитория

```text
apps/
  api/        FastAPI backend
  docgen/     Node.js DOCX render service
  miniapp/    React frontend

templates/
  system/
    invoice-kz/v1/
    proposal-simple/v1/

docs/
  architecture/

scripts/
  start-dev.sh
  stop-dev.sh

data/
  docmini.sqlite3

tmp/
  logs/
  output/
```

## Локальная БД

Для локального тестирования сейчас используется `SQLite`.

Файл БД:

- [data/docmini.sqlite3](/home/observer/Projects/new/doc-mini-app/data/docmini.sqlite3)

Что хранится сейчас:
- клиенты
- товары
- история сохраненных счетов
- позиции сохраненных счетов

Это временное решение для MVP-разработки. В production целевой вариант остается `PostgreSQL`.

## Локальный запуск

### 1. Установка зависимостей

```bash
cd /home/observer/Projects/new/doc-mini-app
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -e apps/api
cd apps/docgen && npm install
cd ../miniapp && npm install
```

### 2. Запуск всего проекта

```bash
cd /home/observer/Projects/new/doc-mini-app
bash scripts/start-dev.sh
```

Скрипт:
- читает корневой `.env`
- чистит старые процессы на портах `4001`, `8000`, `5173`
- поднимает `docgen`, `api`, `bot`, `miniapp`

### 3. Остановка

```bash
cd /home/observer/Projects/new/doc-mini-app
bash scripts/stop-dev.sh
```

### 4. Локальные адреса

- frontend: `http://127.0.0.1:5173`
- api: `http://127.0.0.1:8000`
- docgen: `http://127.0.0.1:4001`

## Как пользоваться локально

### Browser mode

Открой:

```text
http://127.0.0.1:5173
```

В текущем интерфейсе доступны вкладки:
- Главная
- Счета
- Клиенты
- Товары

### Типовой сценарий теста

1. Перейти в `Клиенты`
2. Создать клиента
3. Перейти в `Товары`
4. Создать один или несколько товаров
5. Перейти в `Счета`
6. Выбрать клиента
7. Добавить строки вручную или из каталога
8. Нажать `Сохранить`
9. Нажать `PDF`
10. Нажать `В Telegram`
11. Проверить карточку документа на главной

## Telegram логика

### Что уже есть

- `/start` у бота
- polling через `aiogram`
- отправка PDF счета в Telegram
- auth endpoint:
  - `POST /auth/telegram/init`

### Важное ограничение локального режима

Telegram Mini Apps требуют `HTTPS`.

Поэтому:
- локально в браузере приложение работает как обычный web UI
- локальный `http://127.0.0.1:5173` нельзя использовать как production `web_app` URL
- при отправке документа локально бот не прикладывает `web_app` кнопку, если URL не `https`

Для production Mini App нужен публичный `https` URL.

## Текущие API endpoints

### Auth

- `POST /auth/telegram/init`

### Clients

- `GET /clients`
- `POST /clients`

### Catalog

- `GET /catalog/items`
- `POST /catalog/items`

### Documents

- `GET /documents/recent`
- `POST /documents/invoice`

### Render

- `GET /render/invoice/sample`
- `POST /render/invoice/docx`
- `POST /render/invoice/pdf`
- `POST /render/invoice/debug`

### Telegram

- `POST /telegram/send-invoice`

## Конфигурация

Основной файл:

- [.env](/home/observer/Projects/new/doc-mini-app/.env)

Шаблон:

- [.env.example](/home/observer/Projects/new/doc-mini-app/.env.example)

Ключевые переменные:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_TEST_CHAT_ID`
- `SERVICE_URL_GOTENBERG`
- `SERVICE_USER_GOTENBERG`
- `SERVICE_PASSWORD_GOTENBERG`
- `DOCGEN_URL`
- `SQLITE_PATH`
- `VITE_API_BASE_URL`
- `TELEGRAM_APP_URL`
- `FRONTEND_ORIGIN`

## Что уже внедрено из ТЗ

Из исходного большого ТЗ в репозитории уже отражены следующие решения:

- Telegram как основной канал использования
- simple document generator вместо CRM/ERP
- DOCX templates как ядро логики
- отдельный `docgen` сервис под `docxtemplater`
- PDF render через `Gotenberg`
- bot -> mini app -> backend -> docgen/pdf pipeline
- mobile-first интерфейс
- разделы `Клиенты`, `Каталог`, `Документы`
- создание счета
- сохранение истории
- отправка в Telegram

## Что осталось сделать

### Ближайший этап

- стабилизировать новый UI-поток счетов
- добавить открытие сохраненного документа
- сделать нормальный список счетов на отдельной вкладке
- дать редактирование существующего счета
- улучшить подбор клиента и товаров в счете
- доработать desktop layout поверх mobile-first shell

### Следующий этап

- перейти с SQLite на PostgreSQL
- хранить PDF/DOCX в MinIO/S3
- добавить полноценную модель `documents` и `document_items`
- добавить статусы документов
- добавить контакты отдельно от клиентов
- добавить реквизиты и счета компаний

### Позже

- вернуть КП
- поддержать DOCX download как отдельный пользовательский сценарий
- простые шаблоны пользователя
- browser auth через Telegram Login Widget
- AI-подсказки для шаблонов и простых КП

## Что важно помнить

Главный принцип проекта остается тем же, что и в ТЗ:

> мы строим быстрый генератор документов внутри Telegram, где основной путь до первого счета должен быть максимально коротким

Все, что мешает этому сценарию, не должно попадать в MVP раньше времени.

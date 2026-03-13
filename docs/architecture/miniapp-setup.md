# Mini App Setup

## What works now

- local React Mini App UI
- Telegram init auth bootstrap call
- invoice PDF generation
- sending generated PDF to Telegram chat

## Required for real Telegram Mini App launch

Telegram Mini Apps require a public HTTPS URL.

Use one of these options:

- Cloudflare Tunnel
- ngrok
- your own domain with reverse proxy and TLS

## Minimal wiring

1. Run the API on `127.0.0.1:8000`.
2. Run the frontend on `127.0.0.1:5173`.
3. Set `VITE_API_BASE_URL` to the backend URL.
4. Expose the frontend through HTTPS.
5. Set `TELEGRAM_APP_URL` to that public HTTPS frontend URL for the bot.
6. Set `FRONTEND_ORIGIN` on the API to the same frontend origin.
7. Restart the API and bot.

## Local dev suggestion

- frontend: `http://127.0.0.1:5173`
- api: `http://127.0.0.1:8000`
- frontend can call API directly via `VITE_API_BASE_URL`

Example:

- `https://miniapp.example.com` -> frontend
- `https://api.example.com` -> backend

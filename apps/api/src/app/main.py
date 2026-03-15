from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import init_db
from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.clients.router import router as clients_router
from app.modules.documents.router import router as documents_router
from app.modules.health.router import router as health_router
from app.modules.render.router import router as render_router
from app.modules.profile.router import router as profile_router
from app.modules.telegram_bot.router import router as telegram_router
from app.modules.invoices.router import router as invoices_router
from app.modules.dashboard.router import router as dashboard_router

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "https://doc.onlink.kz", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(catalog_router)
app.include_router(documents_router)
app.include_router(health_router)
app.include_router(profile_router)
app.include_router(render_router)
app.include_router(telegram_router)
app.include_router(invoices_router)
app.include_router(dashboard_router)


@app.on_event("startup")
async def startup() -> None:
    init_db()

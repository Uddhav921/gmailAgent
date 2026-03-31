"""
AI Email Agent — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import connect_db, close_db
from app.routes.webhook import router as webhook_router
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await connect_db()
    print("✅ MongoDB connected")
    yield
    # Shutdown
    await close_db()
    print("🔌 MongoDB disconnected")


app = FastAPI(
    title="AI Email Agent",
    description="Autonomous email scheduling assistant — reads emails, detects intent, books meetings.",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "service": "AI Email Agent",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}

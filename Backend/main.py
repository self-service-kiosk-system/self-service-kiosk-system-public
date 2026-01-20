from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import FileResponse
from app.schemas.schemas import *
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from sqlalchemy import text
import app.config.database as db
from app.config.database import Base
import app.models.models as _models
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.health import router as health_router
from app.api.endpoints.admin import router as admin_router
from app.api.endpoints.menu import router as orders_router
from app.api.websocket.endpoints import websocket_router
#from app.api.websocket.router import router as websocket_router


load_dotenv()


# ============================================================================
# MIDDLEWARE PARA CACHE-CONTROL EN IMÁGENES
# ============================================================================
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Agregar Cache-Control solo para rutas de imágenes
        if request.url.path.startswith("/imagenes"):
            # Cachear imágenes por 30 días (2592000 segundos)
            # immutable indica que el contenido no cambiará
            response.headers["Cache-Control"] = "public, max-age=2592000, immutable"
            response.headers["Vary"] = "Accept-Encoding"
        
        return response

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
IS_DEV = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    with db.SessionLocal() as session:
        session.execute(text("SELECT 1"))
    if IS_DEV:
        Base.metadata.create_all(bind=db.engine)
    yield

app = FastAPI(
    title="API Pizzería",
    description="API para gestión de menú y pedidos de pizzería",
    version="1.0.0",
    lifespan=lifespan
)

# Agregar middleware de cache ANTES de otros middlewares
app.add_middleware(CacheControlMiddleware)

# Configurar ruta absoluta para imagenes
backend_dir = Path(__file__).resolve().parent
proyecto_root = backend_dir.parent
imagenes_path = proyecto_root / "Frontend" / "proyecto-pizzas" / "public" / "imagenes"
imagenes_path.mkdir(parents=True, exist_ok=True)

# AGREGAR: Servir archivos estáticos de imágenes
app.mount("/imagenes", StaticFiles(directory=str(imagenes_path)), name="imagenes")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(admin_router)
app.include_router(orders_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "message": "API de Pizzería - Sistema de Gestión",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "admin": "/admin/*",
            "menu": "/menu/*",
            "websocket": "/ws"
        }
    }
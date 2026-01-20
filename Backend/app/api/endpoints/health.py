from fastapi import APIRouter
from sqlalchemy import text
import app.config.database as db

router = APIRouter(tags=["health"])


@router.get("/health/db")
def health_db():
    """
    Endpoint temporal para verificar la conexión a la base de datos.
    Ejecuta un SELECT 1 para confirmar que la DB responde.
    """
    try:
        with db.SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception as e:
        # Devuelve el error para diagnóstico rápido
        return {"db": "error", "detail": str(e)}

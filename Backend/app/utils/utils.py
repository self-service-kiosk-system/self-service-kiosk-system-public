from fastapi import HTTPException
from typing import Callable, Any, Coroutine
from functools import wraps

SECRET_JWT = "tu_secreto_jwt_super_seguro"

AUTHORIZED_DEVICES = {
    # Dispositivos autorizados para acceso completo
    "device_123": "Local A",
}

# ============================================================================
# CONSTANTES PARA MODO DEMO
# ============================================================================

DEMO_DEVICE_ID = "public"
DEMO_LOCAL_ID = 1  # Local de demostración

def es_modo_demo(payload: dict) -> bool:
    """Verifica si el token pertenece al modo demo/portfolio"""
    return payload.get("device_id") == DEMO_DEVICE_ID or payload.get("is_demo") == True

# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

async def ejecutar_servicio(operacion: Coroutine[Any, Any, Any]):
    """
    Ejecuta una operación de servicio y maneja errores automáticamente.
    
    Uso simple:
        return await ejecutar_servicio(admin_service.obtener_locales())
    """
    try:
        return await operacion
    except HTTPException:
        raise  # Mantiene errores HTTP específicos (401, 404, etc.)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
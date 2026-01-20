"""
Dependencias de FastAPI reutilizables.

Este archivo contiene funciones de dependencia (Depends) que se usan
en múltiples endpoints para validación, autenticación, etc.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.services.admin_service import AdminService

# Extrae automáticamente el token del header "Authorization: Bearer <token>"
security = HTTPBearer()

# Instancia singleton del servicio de admin
_admin_service_instance = None


def get_admin_service() -> AdminService:
    """
    Obtiene o crea la instancia única de AdminService.
    
    Patrón Singleton: asegura que solo exista una instancia en toda la aplicación.
    """
    global _admin_service_instance
    if _admin_service_instance is None:
        _admin_service_instance = AdminService()
    return _admin_service_instance


async def verificar_admin(credentials = Depends(security)) -> bool:
    """
    Dependencia para proteger rutas de admin.
    
    Valida que el token JWT sea válido y pertenezca al administrador.
    
    Uso:
        @router.get("/admin/productos")
        async def obtener_productos(autorizado: bool = Depends(verificar_admin)):
            # Solo se ejecuta si el token es válido
            ...
    
    Raises:
        HTTPException 401: Si el token es inválido o no existe.
    """
    token = credentials.credentials
    service = get_admin_service()
    
    if not service.verificar_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado"
        )
    
    return True
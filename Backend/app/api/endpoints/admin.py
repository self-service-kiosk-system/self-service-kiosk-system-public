from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from typing import Optional
from app.services.admin_service import AdminService
from app.schemas.admin_schemas import (
    LoginRequest,
    LoginResponse,
    ProductoCreate,
    ProductoUpdate,
    ProductoResponse
)
from app.utils.utils import ejecutar_servicio
from app.utils.dependencies import verificar_admin, get_admin_service
from app.services.services import verify_token
from app.api.endpoints.menu import invalidate_menu_cache
from pydantic import BaseModel

router = APIRouter(tags=["admin"])
admin_service = get_admin_service()


# ============================================================================
# FUNCIÓN AUXILIAR PARA OBTENER local_id DEL TOKEN
# ============================================================================

async def obtener_local_id_usuario(payload: dict = Depends(verify_token)) -> int:
    """Extrae el local_id del token JWT (sistema nuevo)"""
    
    # Verificar que tenga los campos necesarios de admin
    if "user_id" not in payload or "local_id" not in payload:
        raise HTTPException(status_code=401, detail="No autorizado")
    
    return payload["local_id"]


# ============================================================================
# ENDPOINTS DE PRODUCTOS (CON FILTRADO POR local_id)
# ============================================================================

@router.get("/admin/productos")
async def obtener_productos(
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Obtiene productos del local del usuario autenticado"""
    return await ejecutar_servicio(admin_service.obtener_productos(local_id))


@router.post("/admin/productos")
async def crear_producto(
    nombre: str = Form(...),
    descripcion: str = Form(...),
    precio: float = Form(...),
    categoria_id: int = Form(...),
    disponible: bool = Form(True),
    destacado: bool = Form(False),
    imagen: Optional[UploadFile] = File(None),
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Crea un producto en el local del usuario"""
    
    datos = ProductoCreate(
        local_id=local_id,
        categoria_id=categoria_id,
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        disponible=disponible,
        destacado=destacado
    )
    
    result = await ejecutar_servicio(
        admin_service.crear_producto(local_id, datos, imagen)
    )
    
    # Invalidar caché del menú para este local
    invalidate_menu_cache(local_id)
    
    return result


@router.put("/admin/productos/{producto_id}")
async def actualizar_producto(
    producto_id: int,
    nombre: Optional[str] = Form(None),
    descripcion: Optional[str] = Form(None),
    precio: Optional[float] = Form(None),
    categoria_id: Optional[int] = Form(None),
    disponible: Optional[bool] = Form(None),
    destacado: Optional[bool] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Actualiza un producto del local del usuario"""
    
    datos = ProductoUpdate(
        categoria_id=categoria_id,
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        disponible=disponible,
        destacado=destacado
    )
    
    result = await ejecutar_servicio(
        admin_service.actualizar_producto(producto_id, local_id, datos, imagen)
    )
    
    # Invalidar caché del menú para este local
    invalidate_menu_cache(local_id)
    
    return result


@router.delete("/admin/productos/{producto_id}")
async def eliminar_producto(
    producto_id: int,
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Elimina un producto del local del usuario"""
    result = await ejecutar_servicio(
        admin_service.eliminar_producto(producto_id, local_id)
    )
    
    # Invalidar caché del menú para este local
    invalidate_menu_cache(local_id)
    
    return result


# ============================================================================
# ENDPOINTS DE CATEGORÍAS Y LOCALES
# ============================================================================

@router.get("/admin/categorias")
async def obtener_categorias(
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Obtiene categorías del local del usuario"""
    return await ejecutar_servicio(admin_service.obtener_categorias(local_id))


class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: str = ""


@router.post("/admin/categorias")
async def crear_categoria(
    datos: CategoriaCreate,
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Crea una nueva categoría para el local del usuario"""
    return await ejecutar_servicio(admin_service.crear_categoria(local_id, datos.nombre, datos.descripcion))


class CategoriaUpdate(BaseModel):
    nombre: str
    descripcion: str = ""


@router.put("/admin/categorias/{categoria_id}")
async def actualizar_categoria(
    categoria_id: int,
    datos: CategoriaUpdate,
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Actualiza una categoría del local del usuario"""
    return await ejecutar_servicio(
        admin_service.actualizar_categoria(local_id, categoria_id, datos.nombre, datos.descripcion)
    )


@router.delete("/admin/categorias/{categoria_id}")
async def eliminar_categoria(
    categoria_id: int,
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Elimina una categoría del local del usuario (solo si no tiene productos)"""
    return await ejecutar_servicio(
        admin_service.eliminar_categoria(local_id, categoria_id)
    )


class ReordenarCategoriasRequest(BaseModel):
    orden_ids: list[int]


@router.put("/admin/categorias/reordenar")
async def reordenar_categorias(
    datos: ReordenarCategoriasRequest,
    local_id: int = Depends(obtener_local_id_usuario)
):
    """Reordena las categorías del local del usuario"""
    return await ejecutar_servicio(
        admin_service.reordenar_categorias(local_id, datos.orden_ids)
    )


@router.get("/admin/locales")
async def obtener_locales(
    payload: dict = Depends(verify_token)
):
    """Obtiene locales (solo para referencia)"""
    
    # Solo super_admin puede ver todos los locales
    if payload.get("rol") == "super_admin":
        return await ejecutar_servicio(admin_service.obtener_locales())
    
    # Los demás solo ven su local
    from app.config.database import SessionLocal
    from app.models.models import Local
    
    with SessionLocal() as db:
        local = db.query(Local).filter(Local.id == payload["local_id"]).first()
        
        if not local:
            raise HTTPException(status_code=404, detail="Local no encontrado")
        
        return [{
            "id": local.id,
            "nombre": local.nombre,
            "direccion": local.direccion,
            "telefono": local.telefono
        }]


# ============================================================================
# SCHEMAS
# ============================================================================

# Respuesta genérica para mensajes
class MessageResponse(BaseModel):
    message: str
    id: Optional[int] = None
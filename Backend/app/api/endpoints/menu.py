from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
from app.services.services import verify_token
from app.services.menu_service import MenuService
from app.utils.utils import ejecutar_servicio
from app.config.database import get_db
from app.models.models import Producto, Categoria, Local, ConfiguracionCarrusel
from app.api.websocket.manager import manager
import asyncio

router = APIRouter(tags=["menu"])

# Instancia del servicio
menu_service = MenuService()

# Schema para la configuración del carrusel
class CarruselConfigSchema(BaseModel):
    mode: str = "all"
    selectedCategories: List[str] = []

# ============================================================================
# CACHÉ EN MEMORIA PARA REDUCIR QUERIES A LA BASE DE DATOS
# Solo se invalida cuando se modifican productos (crear/editar/eliminar)
# ============================================================================
_menu_cache: dict = {}  # {local_id: [...productos...]}

def get_cached_menu(local_id: int):
    """Obtiene menú desde caché si existe"""
    return _menu_cache.get(local_id)

def set_cached_menu(local_id: int, data: list):
    """Guarda menú en caché"""
    _menu_cache[local_id] = data

def invalidate_menu_cache(local_id: int = None):
    """Invalida caché de menú (llamar al crear/editar/eliminar productos)"""
    if local_id:
        _menu_cache.pop(local_id, None)
    else:
        _menu_cache.clear()

# ============================================================================

@router.get("/menu/productos")
async def obtener_menu(
    local_id: int = Query(..., description="ID del local"),
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Obtiene productos disponibles del menú para un local específico"""
    
    # Verificar que el dispositivo tiene acceso a este local
    if payload.get("local_id") != local_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a este local"
        )
    
    # Intentar obtener desde caché primero
    cached = get_cached_menu(local_id)
    if cached is not None:
        return cached
    
    productos = db.query(Producto).filter(
        Producto.local_id == local_id
    ).order_by(Producto.destacado.desc(), Producto.nombre).all()
    
    result = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "precio": float(p.precio),
            "imagen_url": p.imagen_url,
            "disponible": p.disponible,
            "destacado": p.destacado,
            "categorias": {
                "id": p.categoria.id,
                "nombre": p.categoria.nombre
            } if p.categoria else None
        }
        for p in productos
    ]
    
    # Guardar en caché para futuras consultas
    set_cached_menu(local_id, result)
    
    return result


@router.get("/menu/categorias")
async def obtener_categorias_menu(
    local_id: int = Query(..., description="ID del local"),
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Obtiene categorías activas de un local para el menú"""
    
    if payload.get("local_id") != local_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes acceso a este local"
        )
    
    categorias = db.query(Categoria).filter(
        Categoria.local_id == local_id,
        Categoria.esta_activo == True
    ).order_by(Categoria.orden).all()
    
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "descripcion": c.descripcion
        }
        for c in categorias
    ]

# ===== ENDPOINTS DE CONFIGURACIÓN DEL CARRUSEL =====

@router.get("/carrusel/config")
def obtener_config_carrusel(
    local_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Obtiene la configuración del carrusel para un local"""
    config = db.query(ConfiguracionCarrusel).filter(
        ConfiguracionCarrusel.local_id == local_id
    ).first()
    
    if not config:
        # Retornar configuración por defecto
        return {
            "mode": "all",
            "selectedCategories": []
        }
    
    return {
        "mode": config.modo,
        "selectedCategories": config.categorias_seleccionadas or []
    }


@router.put("/carrusel/config")
async def actualizar_config_carrusel(
    local_id: int = Query(...),
    config_data: CarruselConfigSchema = Body(...),
    db: Session = Depends(get_db)
):
    """Actualiza la configuración del carrusel (solo admin)"""
    
    config = db.query(ConfiguracionCarrusel).filter(
        ConfiguracionCarrusel.local_id == local_id
    ).first()
    
    if not config:
        # Crear nueva configuración
        config = ConfiguracionCarrusel(
            local_id=local_id,
            modo=config_data.mode,
            categorias_seleccionadas=config_data.selectedCategories
        )
        db.add(config)
    else:
        # Actualizar existente
        config.modo = config_data.mode
        config.categorias_seleccionadas = config_data.selectedCategories
    
    db.commit()
    db.refresh(config)
    
    response_data = {
        "mode": config.modo,
        "selectedCategories": config.categorias_seleccionadas or []
    }
    
    # Notificar a todos los dispositivos del local via WebSocket
    await manager.broadcast_to_local(local_id, {
        "titulo": "carrusel_config_actualizada",
        "datos": response_data
    })
    
    return response_data

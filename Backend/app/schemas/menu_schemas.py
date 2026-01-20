from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal


# ============================================================================
# SCHEMAS PARA EL MENÚ PÚBLICO
# ============================================================================

class ProductoMenu(BaseModel):
    """Producto para mostrar en el menú del kiosk"""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    imagen_url: Optional[str] = None
    destacado: bool = False
    
    class Config:
        from_attributes = True


class CategoriaMenu(BaseModel):
    """Categoría con sus productos"""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    productos: List[ProductoMenu] = []


class LocalMenu(BaseModel):
    """Local con sus categorías y productos"""
    id: int
    nombre: str
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    categorias: List[CategoriaMenu] = []


class MenuCompleto(BaseModel):
    """Respuesta completa del menú"""
    locales: List[LocalMenu]
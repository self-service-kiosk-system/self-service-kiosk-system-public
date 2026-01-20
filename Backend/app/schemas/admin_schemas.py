from pydantic import BaseModel, Field
from typing import Optional


# ============================================================================
# SCHEMAS DE AUTENTICACIÓN
# ============================================================================

class LoginRequest(BaseModel):
    usuario: str
    contrasena: str


class LoginResponse(BaseModel):
    token: str
    mensaje: str


# ============================================================================
# SCHEMAS DE PRODUCTOS
# ============================================================================

class ProductoBase(BaseModel):
    """Campos base compartidos por todos los schemas de productos"""
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str = Field(default="", max_length=500)
    precio: float = Field(..., gt=0, description="Precio debe ser mayor a 0")
    disponible: bool = Field(default=True)
    destacado: bool = Field(default=False)


class ProductoCreate(ProductoBase):
    """Schema para crear un nuevo producto"""
    local_id: int = Field(..., gt=0)
    categoria_id: int = Field(..., gt=0)
    # imagen se maneja por separado como UploadFile


class ProductoUpdate(BaseModel):
    """Schema para actualizar un producto (todos los campos son opcionales)"""
    categoria_id: Optional[int] = Field(None, gt=0)
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)
    precio: Optional[float] = Field(None, gt=0)
    disponible: Optional[bool] = None
    destacado: Optional[bool] = None
    # imagen se maneja por separado como UploadFile


class ProductoResponse(ProductoBase):
    """Schema para respuestas (incluye campos generados por la BD)"""
    id: int
    local_id: int
    categoria_id: int
    imagen_url: Optional[str] = None
    
    class Config:
        from_attributes = True  # Permite crear desde ORM models
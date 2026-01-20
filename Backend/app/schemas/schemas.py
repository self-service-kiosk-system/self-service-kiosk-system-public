from pydantic import BaseModel, EmailStr
from typing import Optional

class DeviceAuth(BaseModel):
    device_id: str
    secret_key: str

class UserLogin(BaseModel):
    """Schema para login de usuarios"""
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    """Schema para crear usuario (sin email obligatorio)"""
    nombre: str
    username: str  #Nuevo campo para login sin email
    password: str
    rol: str = "empleado"
    local_id: int
    email: Optional[EmailStr] = None  # Email opcional
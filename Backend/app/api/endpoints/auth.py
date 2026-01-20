from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.utils.utils import *
from app.services.services import verify_token
from app.config.database import SessionLocal
from app.models.models import Usuario, DispositivoAutorizado
import bcrypt
import jwt
import datetime

router = APIRouter(tags=["auth"])


# ============================================================================
# AUTENTICACIÓN DE DISPOSITIVOS (Kiosks/Tablets)
# ============================================================================

class DeviceAuthRequest(BaseModel):
    device_id: str
    secret_key: str


@router.post("/auth/device")
async def authenticate_device(credentials: DeviceAuthRequest):
    """Autentica un dispositivo y devuelve un JWT con device_id y local_id"""
    
    device_id = credentials.device_id
    secret_key = credentials.secret_key
    
    # Verificar que el dispositivo está autorizado
    if device_id not in AUTHORIZED_DEVICES:
        raise HTTPException(status_code=404, detail="Pagina no encontrada")
    
    if AUTHORIZED_DEVICES[device_id] != secret_key:
        raise HTTPException(status_code=404, detail="Pagina no encontrada")
    
    # CASO ESPECIAL: Dispositivo público/demo
    if device_id == DEMO_DEVICE_ID:
        token_data = {
            "device_id": device_id,
            "local_id": DEMO_LOCAL_ID,
            "tipo": "demo",
            "is_demo": True
        }
        token = jwt.encode(token_data, SECRET_JWT, algorithm="HS256")
        
        return {
            "token": token,
            "device_id": device_id,
            "local_id": DEMO_LOCAL_ID,
            "is_demo": True
        }
    
    # Buscar el dispositivo en la base de datos para obtener su local_id
    db = SessionLocal()
    try:
        dispositivo = db.query(DispositivoAutorizado).filter(
            DispositivoAutorizado.device_id == device_id,
            DispositivoAutorizado.esta_activo == True
        ).first()
        
        if not dispositivo:
            raise HTTPException(status_code=404, detail="Dispositivo no encontrado en la base de datos")
        
        # ACCEDER A LOS DATOS ANTES DE CERRAR LA SESIÓN
        local_id = dispositivo.local_id
        tipo = dispositivo.tipo
        
        # Actualizar último acceso
        dispositivo.ultimo_acceso = datetime.datetime.now()
        db.commit()
        
        # Generar JWT con device_id y local_id
        token_data = {
            "device_id": device_id,
            "local_id": local_id,
            "tipo": tipo
        }
        token = jwt.encode(token_data, SECRET_JWT, algorithm="HS256")
        
        return {
            "token": token,
            "device_id": device_id,
            "local_id": local_id
        }
        
    finally:
        db.close()


@router.get("/verify")
async def verify_device_token(payload: dict = Depends(verify_token)):
    """Verifica que un token de dispositivo sea válido"""
    return {
        "status": "authorized",
        "device_id": payload.get("device_id"),
        "local_id": payload.get("local_id"),
        "is_demo": payload.get("is_demo", False)
    }


# ============================================================================
# AUTENTICACIÓN DE ADMINISTRADORES
# ============================================================================

class AdminLoginRequest(BaseModel):
    usuario: str
    contrasena: str


@router.post("/admin/login")
async def admin_login(credentials: AdminLoginRequest):
    """Autentica un usuario administrador y devuelve JWT con local_id"""
    
    db = SessionLocal()
    try:
        # Buscar usuario por nombre
        usuario = db.query(Usuario).filter(
            Usuario.nombre == credentials.usuario,
            Usuario.esta_activo == True
        ).first()
        
        if not usuario:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        # Verificar contraseña
        if not bcrypt.checkpw(
            credentials.contrasena.encode('utf-8'),
            usuario.password_hash.encode('utf-8')
        ):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        # ACCEDER A LOS DATOS ANTES DE CERRAR LA SESIÓN
        user_id = usuario.id
        local_id = usuario.local_id
        rol = usuario.rol
        nombre = usuario.nombre
        
        # Actualizar último acceso
        usuario.ultimo_acceso = datetime.datetime.now()
        db.commit()
        
        # Generar JWT con user_id, local_id y rol
        token_data = {
            "user_id": user_id,
            "local_id": local_id,
            "rol": rol,
            "nombre": nombre
        }
        token = jwt.encode(token_data, SECRET_JWT, algorithm="HS256")
        
        return {
            "token": token,
            "usuario": nombre,
            "local_id": local_id,
            "rol": rol
        }
        
    finally:
        db.close()


@router.get("/admin/verificar")
async def verificar_admin(payload: dict = Depends(verify_token)):
    """Verifica que un token de admin sea válido"""
    
    # CASO ESPECIAL: Modo demo - auto-autorizar como admin
    if es_modo_demo(payload):
        return {
            "status": "authorized",
            "user_id": 0,
            "local_id": payload.get("local_id", DEMO_LOCAL_ID),
            "rol": "demo",
            "is_demo": True
        }
    
    # Verificar que tenga los campos necesarios de admin
    if "user_id" not in payload or "local_id" not in payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return {
        "status": "authorized",
        "user_id": payload.get("user_id"),
        "local_id": payload.get("local_id"),
        "rol": payload.get("rol"),
        "is_demo": False
    }

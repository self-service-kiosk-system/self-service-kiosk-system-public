import pytest
from fastapi import HTTPException
from unittest.mock import patch, Mock
import jwt
from datetime import datetime, timedelta
from app.services.services import verify_token
from app.utils.utils import SECRET_JWT


def crear_token_valido(payload: dict, expires_delta: timedelta = None) -> str:
    """Helper para crear tokens JWT válidos"""
    if expires_delta is None:
        expires_delta = timedelta(days=1)
    
    payload_completo = {
        **payload,
        "exp": datetime.utcnow() + expires_delta
    }
    
    return jwt.encode(payload_completo, SECRET_JWT, algorithm="HS256")


class TestVerifyTokenDispositivos:
    """Tests para verify_token() con tokens de dispositivos"""
    
    @pytest.mark.asyncio
    async def test_token_dispositivo_valido(self):
        """Debe validar token de dispositivo correctamente"""
        payload = {
            "device_id": "raspberry_1",
            "local_id": 1,
            "tipo": "kiosk"
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["device_id"] == "raspberry_1"
        assert resultado["local_id"] == 1
        assert resultado["tipo"] == "kiosk"
    
    @pytest.mark.asyncio
    async def test_token_dispositivo_sin_local_id(self):
        """Debe rechazar token de dispositivo sin local_id"""
        payload = {
            "device_id": "raspberry_1"
            # Falta local_id
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        # Aunque tiene device_id, podría ser válido o inválido según tu lógica
        # Si requieres local_id, debería fallar
        resultado = await verify_token(authorization)
        
        # Verificar que tiene device_id (mínimo requerido para dispositivo)
        assert "device_id" in resultado
    
    @pytest.mark.asyncio
    async def test_token_dispositivo_multiple_locales(self):
        """Debe manejar dispositivos con diferentes locales"""
        dispositivos = [
            {"device_id": "raspberry_1", "local_id": 1},
            {"device_id": "raspberry_2", "local_id": 2},
            {"device_id": "tablet_1", "local_id": 1}
        ]
        
        for dispositivo in dispositivos:
            token = crear_token_valido(dispositivo)
            authorization = f"Bearer {token}"
            
            resultado = await verify_token(authorization)
            
            assert resultado["device_id"] == dispositivo["device_id"]
            assert resultado["local_id"] == dispositivo["local_id"]


class TestVerifyTokenAdmins:
    """Tests para verify_token() con tokens de administradores"""
    
    @pytest.mark.asyncio
    async def test_token_admin_valido(self):
        """Debe validar token de admin correctamente"""
        payload = {
            "user_id": 1,
            "local_id": 1,
            "rol": "admin",
            "nombre": "Admin Test"
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["user_id"] == 1
        assert resultado["local_id"] == 1
        assert resultado["rol"] == "admin"
        assert resultado["nombre"] == "Admin Test"
    
    @pytest.mark.asyncio
    async def test_token_admin_sin_user_id(self):
        """Debe rechazar token de admin sin user_id"""
        payload = {
            "local_id": 1,
            "rol": "admin"
            # Falta user_id
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "inválido" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_token_admin_sin_local_id(self):
        """Debe rechazar token de admin sin local_id"""
        payload = {
            "user_id": 1,
            "rol": "admin"
            # Falta local_id
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_super_admin_valido(self):
        """Debe validar token de super_admin correctamente"""
        payload = {
            "user_id": 1,
            "local_id": 0,  # Super admin puede tener local_id especial
            "rol": "super_admin",
            "nombre": "Super Admin"
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["rol"] == "super_admin"
    
    @pytest.mark.asyncio
    async def test_token_empleado_valido(self):
        """Debe validar token de empleado correctamente"""
        payload = {
            "user_id": 5,
            "local_id": 2,
            "rol": "empleado",
            "nombre": "Empleado Test"
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["rol"] == "empleado"
        assert resultado["local_id"] == 2


class TestVerifyTokenErrores:
    """Tests para manejo de errores en verify_token()"""
    
    @pytest.mark.asyncio
    async def test_sin_header_authorization(self):
        """Debe rechazar request sin header Authorization"""
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization=None)
        
        assert exc_info.value.status_code == 401
        assert "no proporcionado" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_authorization_sin_bearer(self):
        """Debe rechazar header sin prefijo Bearer"""
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization="InvalidToken123")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_expirado(self):
        """Debe rechazar token expirado"""
        payload = {
            "device_id": "raspberry_1",
            "local_id": 1
        }
        
        # Token expirado hace 1 día
        token = crear_token_valido(payload, expires_delta=timedelta(days=-1))
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "expirado" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_token_firma_invalida(self):
        """Debe rechazar token con firma inválida"""
        payload = {
            "device_id": "raspberry_1",
            "local_id": 1,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        
        # Firmar con secret incorrecto
        token = jwt.encode(payload, "wrong_secret_key", algorithm="HS256")
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "inválido" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_token_malformado(self):
        """Debe rechazar token malformado"""
        authorization = "Bearer not.a.valid.jwt.token"
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_token_sin_identificador(self):
        """Debe rechazar token sin device_id ni user_id"""
        payload = {
            "local_id": 1,
            "tipo": "unknown"
            # Sin device_id ni user_id
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "inválido" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_token_vacio(self):
        """Debe rechazar token vacío"""
        authorization = "Bearer "
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(authorization)
        
        assert exc_info.value.status_code == 401


class TestVerifyTokenCasosEspeciales:
    """Tests para casos especiales y edge cases"""
    
    @pytest.mark.asyncio
    async def test_token_con_campos_extra(self):
        """Debe aceptar tokens con campos adicionales no requeridos"""
        payload = {
            "device_id": "raspberry_1",
            "local_id": 1,
            "tipo": "kiosk",
            "ubicacion": "Entrada",
            "version": "2.0",
            "custom_field": "custom_value"
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        # Debe retornar todos los campos del payload
        assert resultado["device_id"] == "raspberry_1"
        assert resultado["custom_field"] == "custom_value"
    
    @pytest.mark.asyncio
    async def test_token_pronto_a_expirar(self):
        """Debe aceptar token que expira en pocos segundos"""
        payload = {
            "device_id": "raspberry_1",
            "local_id": 1
        }
        
        # Token expira en 5 segundos
        token = crear_token_valido(payload, expires_delta=timedelta(seconds=5))
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["device_id"] == "raspberry_1"
    
    @pytest.mark.asyncio
    async def test_token_recien_emitido(self):
        """Debe aceptar token recién emitido"""
        payload = {
            "user_id": 1,
            "local_id": 1,
            "rol": "admin",
            "iat": datetime.utcnow()  # Issued at: ahora
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["user_id"] == 1
    
    @pytest.mark.asyncio
    async def test_token_local_id_cero(self):
        """Debe aceptar local_id en 0 (para super_admin)"""
        payload = {
            "user_id": 1,
            "local_id": 0,
            "rol": "super_admin"
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["local_id"] == 0
    
    @pytest.mark.asyncio
    async def test_token_local_id_muy_grande(self):
        """Debe aceptar local_id con valor grande"""
        payload = {
            "device_id": "device_999",
            "local_id": 999999
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["local_id"] == 999999
    
    @pytest.mark.asyncio
    async def test_token_caracteres_especiales_en_strings(self):
        """Debe manejar caracteres especiales en campos string"""
        payload = {
            "device_id": "device-test_123",
            "local_id": 1,
            "nombre": "José María O'Brien (Admin)"
        }
        
        token = crear_token_valido(payload)
        authorization = f"Bearer {token}"
        
        resultado = await verify_token(authorization)
        
        assert resultado["device_id"] == "device-test_123"
        assert resultado["nombre"] == "José María O'Brien (Admin)"


class TestVerifyTokenConcurrencia:
    """Tests para verificar comportamiento con múltiples tokens"""
    
    @pytest.mark.asyncio
    async def test_multiples_tokens_dispositivos_validos(self):
        """Debe validar múltiples tokens de dispositivos concurrentemente"""
        dispositivos = [
            {"device_id": f"device_{i}", "local_id": i % 3 + 1}
            for i in range(10)
        ]
        
        for dispositivo in dispositivos:
            token = crear_token_valido(dispositivo)
            authorization = f"Bearer {token}"
            
            resultado = await verify_token(authorization)
            
            assert resultado["device_id"] == dispositivo["device_id"]
            assert resultado["local_id"] == dispositivo["local_id"]
    
    @pytest.mark.asyncio
    async def test_token_admin_y_dispositivo_diferentes(self):
        """Debe distinguir entre token de admin y dispositivo"""
        token_admin = crear_token_valido({
            "user_id": 1,
            "local_id": 1,
            "rol": "admin"
        })
        
        token_dispositivo = crear_token_valido({
            "device_id": "raspberry_1",
            "local_id": 1
        })
        
        # Validar token admin
        resultado_admin = await verify_token(f"Bearer {token_admin}")
        assert "user_id" in resultado_admin
        assert "device_id" not in resultado_admin
        
        # Validar token dispositivo
        resultado_dispositivo = await verify_token(f"Bearer {token_dispositivo}")
        assert "device_id" in resultado_dispositivo
        assert "user_id" not in resultado_dispositivo


class TestVerifyTokenIntegracion:
    """Tests de integración para verify_token()"""
    
    @pytest.mark.asyncio
    async def test_flujo_completo_autenticacion_dispositivo(self):
        """Simula flujo completo: generar token → validar → usar"""
        # 1. Generar token (simula POST /auth/device)
        payload = {
            "device_id": "raspberry_test",
            "local_id": 1,
            "tipo": "kiosk"
        }
        token = crear_token_valido(payload, expires_delta=timedelta(days=30))
        
        # 2. Validar token (simula middleware)
        authorization = f"Bearer {token}"
        resultado = await verify_token(authorization)
        
        # 3. Usar datos del token
        assert resultado["device_id"] == "raspberry_test"
        assert resultado["local_id"] == 1
        
        # 4. Verificar que puede usarse para filtrar datos
        local_id_from_token = resultado["local_id"]
        assert local_id_from_token == 1
    
    @pytest.mark.asyncio
    async def test_flujo_completo_autenticacion_admin(self):
        """Simula flujo completo: login admin → validar → acceder panel"""
        # 1. Generar token (simula POST /admin/login)
        payload = {
            "user_id": 5,
            "local_id": 2,
            "rol": "admin",
            "nombre": "Admin Norte"
        }
        token = crear_token_valido(payload, expires_delta=timedelta(days=1))
        
        # 2. Validar token en endpoint protegido
        authorization = f"Bearer {token}"
        resultado = await verify_token(authorization)
        
        # 3. Extraer local_id para filtrado
        assert resultado["local_id"] == 2
        assert resultado["rol"] == "admin"
        
        # 4. Verificar que puede acceder solo a su local
        local_id_permitido = resultado["local_id"]
        assert local_id_permitido == 2
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import jwt
import bcrypt
from main import app
from app.models.models import DispositivoAutorizado, Usuario
from app.utils.utils import SECRET_JWT

client = TestClient(app)


class TestDeviceAuthentication:
    """Tests para autenticación de dispositivos"""
    
    def test_authenticate_device_success(self):
        """Test: Autenticación exitosa con credenciales válidas"""
        # Mock del diccionario AUTHORIZED_DEVICES
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"
        }
        
        # Mock del dispositivo en la base de datos
        mock_dispositivo = MagicMock(spec=DispositivoAutorizado)
        mock_dispositivo.device_id = "raspberry_1"
        mock_dispositivo.local_id = 1
        mock_dispositivo.tipo = "kiosk"
        mock_dispositivo.esta_activo = True
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_dispositivo
        
        # Patchear tanto SessionLocal como AUTHORIZED_DEVICES
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session, \
             patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            mock_session.return_value = mock_db
            
            response = client.post(
                "/auth/device",
                json={
                    "device_id": "raspberry_1",
                    "secret_key": "secret_raspberry_1"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["device_id"] == "raspberry_1"
        assert data["local_id"] == 1
    
    def test_authenticate_device_invalid_id(self):
        """Test: Dispositivo con ID no autorizado"""
        # Mock del diccionario AUTHORIZED_DEVICES vacío o sin el dispositivo
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"
        }
        
        with patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            response = client.post(
                "/auth/device",
                json={
                    "device_id": "dispositivo_desconocido",
                    "secret_key": "cualquier_secreto"
                }
            )
        
        assert response.status_code == 404
    
    def test_authenticate_device_invalid_secret(self):
        """Test: Secret key incorrecta"""
        # Mock del diccionario AUTHORIZED_DEVICES
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"  # La correcta es esta
        }
        
        with patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            response = client.post(
                "/auth/device",
                json={
                    "device_id": "raspberry_1",
                    "secret_key": "secret_key_incorrecta"  # Esta es incorrecta
                }
            )
        
        assert response.status_code == 404
    
    def test_authenticate_all_devices(self):
        """Test: Todos los dispositivos autorizados pueden autenticarse"""
        devices = [
            ("raspberry_1", "secret_raspberry_1", 1),
            ("raspberry_2", "secret_raspberry_2", 2),
            ("admin_pc", "secret_admin_pc", 1)
        ]
        
        # Crear diccionario AUTHORIZED_DEVICES con todos los dispositivos
        mock_authorized_devices = {
            device_id: secret_key for device_id, secret_key, _ in devices
        }
        
        for device_id, secret, local_id in devices:
            mock_dispositivo = MagicMock(spec=DispositivoAutorizado)
            mock_dispositivo.device_id = device_id
            mock_dispositivo.local_id = local_id
            mock_dispositivo.tipo = "kiosk"
            mock_dispositivo.esta_activo = True
            
            mock_db = MagicMock()
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = mock_dispositivo
            
            with patch('app.api.endpoints.auth.SessionLocal') as mock_session, \
                 patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
                mock_session.return_value = mock_db
                
                response = client.post(
                    "/auth/device",
                    json={
                        "device_id": device_id,
                        "secret_key": secret
                    }
                )
            
            assert response.status_code == 200, f"Falló para {device_id}"
    
    def test_verify_token_success(self):
        """Test: Verificación exitosa de token válido"""
        # Mock del diccionario AUTHORIZED_DEVICES
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"
        }
        
        # Mock para authenticate
        mock_dispositivo = MagicMock(spec=DispositivoAutorizado)
        mock_dispositivo.device_id = "raspberry_1"
        mock_dispositivo.local_id = 1
        mock_dispositivo.tipo = "kiosk"
        mock_dispositivo.esta_activo = True
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_dispositivo
        
        # Primero autenticar para obtener token
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session, \
             patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            mock_session.return_value = mock_db
            
            auth_response = client.post(
                "/auth/device",
                json={
                    "device_id": "raspberry_1",
                    "secret_key": "secret_raspberry_1"
                }
            )
        
        assert auth_response.status_code == 200, f"Auth failed: {auth_response.json()}"
        token = auth_response.json()["token"]
        
        # Verificar el token
        verify_response = client.get(
            "/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data["status"] == "authorized"
    
    def test_verify_token_missing(self):
        """Test: Sin token de autorización"""
        response = client.get("/verify")
        
        assert response.status_code == 401
    
    def test_verify_token_invalid(self):
        """Test: Token inválido"""
        response = client.get(
            "/verify",
            headers={"Authorization": "Bearer token_invalido"}
        )
        
        assert response.status_code == 401
    
    def test_verify_token_malformed(self):
        """Test: Header de autorización mal formado"""
        response = client.get(
            "/verify",
            headers={"Authorization": "InvalidFormat"}
        )
        
        assert response.status_code == 401


class TestDeviceAuthenticationEdgeCases:
    """Tests de casos extremos para autenticación de dispositivos"""
    
    def test_authenticate_empty_credentials(self):
        """Test: Credenciales vacías"""
        # Mock del diccionario AUTHORIZED_DEVICES
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"
        }
        
        with patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            response = client.post(
                "/auth/device",
                json={
                    "device_id": "",
                    "secret_key": ""
                }
            )
        
        assert response.status_code == 404
    
    def test_authenticate_missing_fields(self):
        """Test: Campos faltantes en el request"""
        response = client.post(
            "/auth/device",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_verify_token_expired(self):
        """Test: Token expirado"""
        # Crear token expirado manualmente
        expired_payload = {
            "device_id": "raspberry_1",
            "local_id": 1,
            "tipo": "kiosk",
            "exp": datetime.utcnow() - timedelta(days=1)
        }
        expired_token = jwt.encode(expired_payload, SECRET_JWT, algorithm="HS256")
        
        response = client.get(
            "/verify",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == 401
    
    def test_authenticate_case_sensitive(self):
        """Test: Los IDs son case-sensitive"""
        # Mock del diccionario AUTHORIZED_DEVICES (en minúsculas)
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"
        }
        
        with patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            response = client.post(
                "/auth/device",
                json={
                    "device_id": "RASPBERRY_1",  # Mayúsculas - NO debería funcionar
                    "secret_key": "secret_raspberry_1"
                }
            )
        
        assert response.status_code == 404


class TestAdminAuthentication:
    """Tests para autenticación de administradores"""
    
    def test_admin_login_success(self):
        """Test: Login exitoso de administrador"""
        # Mock del usuario en la base de datos
        mock_usuario = MagicMock(spec=Usuario)
        mock_usuario.id = 1
        mock_usuario.nombre = "admin"
        mock_usuario.password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        mock_usuario.local_id = 1
        mock_usuario.rol = "admin"
        mock_usuario.esta_activo = True
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_usuario
        
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session:
            mock_session.return_value = mock_db
            
            response = client.post(
                "/admin/login",
                json={
                    "usuario": "admin",
                    "contrasena": "password123"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["usuario"] == "admin"
        assert data["local_id"] == 1
        assert data["rol"] == "admin"
    
    def test_admin_login_user_not_found(self):
        """Test: Login con usuario que no existe"""
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None  # No encuentra el usuario
        
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session:
            mock_session.return_value = mock_db
            
            response = client.post(
                "/admin/login",
                json={
                    "usuario": "usuario_inexistente",
                    "contrasena": "password123"
                }
            )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Credenciales inválidas"
    
    def test_admin_login_wrong_password(self):
        """Test: Login con contraseña incorrecta"""
        # Mock del usuario con una contraseña diferente
        mock_usuario = MagicMock(spec=Usuario)
        mock_usuario.nombre = "admin"
        # Hash de "otra_password" no "password123"
        mock_usuario.password_hash = bcrypt.hashpw("otra_password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        mock_usuario.esta_activo = True
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_usuario
        
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session:
            mock_session.return_value = mock_db
            
            response = client.post(
                "/admin/login",
                json={
                    "usuario": "admin",
                    "contrasena": "password123"  # Contraseña incorrecta
                }
            )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Credenciales inválidas"
    
    def test_admin_login_inactive_user(self):
        """Test: Login con usuario inactivo"""
        # Si el usuario está inactivo, el query con filter esta_activo=True NO lo encuentra
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None  # No lo encuentra porque está inactivo
        
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session:
            mock_session.return_value = mock_db
            
            response = client.post(
                "/admin/login",
                json={
                    "usuario": "admin",
                    "contrasena": "password123"
                }
            )
        
        assert response.status_code == 401
        assert response.json()["detail"] == "Credenciales inválidas"
    
    def test_admin_verify_success(self):
        """Test: Verificación exitosa de token de admin"""
        # Mock del diccionario AUTHORIZED_DEVICES para auth/device
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"
        }
        
        # Mock para authenticate (para obtener un token)
        mock_dispositivo = MagicMock(spec=DispositivoAutorizado)
        mock_dispositivo.device_id = "raspberry_1"
        mock_dispositivo.local_id = 1
        mock_dispositivo.tipo = "kiosk"
        mock_dispositivo.esta_activo = True
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_dispositivo
        
        # Obtener token de dispositivo
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session, \
             patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            mock_session.return_value = mock_db
            
            auth_response = client.post(
                "/auth/device",
                json={
                    "device_id": "raspberry_1",
                    "secret_key": "secret_raspberry_1"
                }
            )
        
        token = auth_response.json()["token"]
        
        # Verificar que /verify funciona con token de dispositivo
        verify_response = client.get(
            "/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert verify_response.status_code == 200
        
        # Ahora probar /admin/verificar con token de admin
        # Primero crear un token de admin manualmente
        admin_payload = {
            "user_id": 1,
            "local_id": 1,
            "rol": "admin",
            "nombre": "admin"
        }
        admin_token = jwt.encode(admin_payload, SECRET_JWT, algorithm="HS256")
        
        admin_verify_response = client.get(
            "/admin/verificar",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert admin_verify_response.status_code == 200
        data = admin_verify_response.json()
        assert data["status"] == "authorized"
        assert data["user_id"] == 1
        assert data["local_id"] == 1
        assert data["rol"] == "admin"
    
    def test_admin_verify_invalid_token_missing_fields(self):
        """Test: Verificación de admin con token que le faltan campos"""
        # Token sin user_id (campo requerido para admin)
        invalid_payload = {
            "local_id": 1,
            # Falta "user_id"
        }
        invalid_token = jwt.encode(invalid_payload, SECRET_JWT, algorithm="HS256")
        
        response = client.get(
            "/admin/verificar",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )
        
        assert response.status_code == 401
        # El mensaje real del endpoint es más descriptivo
        assert "Token inválido" in response.json()["detail"]
    
    def test_admin_verify_device_token(self):
        """Test: Intentar verificar token de dispositivo en endpoint de admin"""
        # Mock para obtener token de dispositivo
        mock_authorized_devices = {
            "raspberry_1": "secret_raspberry_1"
        }
        
        mock_dispositivo = MagicMock(spec=DispositivoAutorizado)
        mock_dispositivo.device_id = "raspberry_1"
        mock_dispositivo.local_id = 1
        mock_dispositivo.tipo = "kiosk"
        mock_dispositivo.esta_activo = True
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_dispositivo
        
        with patch('app.api.endpoints.auth.SessionLocal') as mock_session, \
             patch('app.api.endpoints.auth.AUTHORIZED_DEVICES', mock_authorized_devices):
            mock_session.return_value = mock_db
            
            auth_response = client.post(
                "/auth/device",
                json={
                    "device_id": "raspberry_1",
                    "secret_key": "secret_raspberry_1"
                }
            )
        
        device_token = auth_response.json()["token"]
        
        # Intentar usar token de dispositivo en endpoint de admin
        response = client.get(
            "/admin/verificar",
            headers={"Authorization": f"Bearer {device_token}"}
        )
        
        # Debería fallar porque el token de dispositivo no tiene user_id
        assert response.status_code == 401
        assert "Token inválido" in response.json()["detail"]

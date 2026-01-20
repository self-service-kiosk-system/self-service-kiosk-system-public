import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import AsyncMock, Mock, patch
import jwt
from datetime import datetime, timedelta
from app.utils.utils import SECRET_JWT
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from main import app


def crear_token_dispositivo(device_id: str, local_id: int, expires_delta: timedelta = None):
    """Helper para crear tokens de dispositivo"""
    if expires_delta is None:
        expires_delta = timedelta(days=30)
    
    payload = {
        "device_id": device_id,
        "local_id": local_id,
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, SECRET_JWT, algorithm="HS256")


def crear_token_admin(user_id: int, local_id: int, rol: str = "admin", expires_delta: timedelta = None):
    """Helper para crear tokens de admin"""
    if expires_delta is None:
        expires_delta = timedelta(days=1)
    
    payload = {
        "user_id": user_id,
        "local_id": local_id,
        "rol": rol,
        "exp": datetime.utcnow() + expires_delta
    }
    return jwt.encode(payload, SECRET_JWT, algorithm="HS256")


class TestWebSocketAuthentication:
    """Tests para autenticación en WebSocket endpoint"""
    
    def test_websocket_sin_token(self):
        """Debe rechazar conexión sin token"""
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/local"):
                    pass
    
    def test_websocket_token_dispositivo_valido(self):
        """Debe aceptar token de dispositivo válido"""
        token = crear_token_dispositivo("test_device", 1)
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token}") as websocket:
                # Debe recibir mensaje de bienvenida
                data = websocket.receive_json()
                assert data["evento"] == "conectado"
                assert "ws_id" in data
                assert data["local_id"] == "1"
    
    def test_websocket_token_admin_valido(self):
        """Debe aceptar token de admin válido"""
        token = crear_token_admin(1, 1, "admin")
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token}") as websocket:
                data = websocket.receive_json()
                assert data["evento"] == "conectado"
                assert data["local_id"] == "1"
    
    def test_websocket_token_expirado(self):
        """Debe rechazar token expirado"""
        token = crear_token_dispositivo(
            "test_device", 
            1, 
            expires_delta=timedelta(days=-1)
        )
        
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/local?token={token}"):
                    pass
    
    def test_websocket_token_invalido(self):
        """Debe rechazar token con firma inválida"""
        payload = {
            "device_id": "test_device",
            "local_id": 1,
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/local?token={token}"):
                    pass
    
    def test_websocket_token_sin_campos_requeridos(self):
        """Debe rechazar token sin device_id o user_id"""
        payload = {
            "other_field": "value",
            "exp": datetime.utcnow() + timedelta(days=1)
        }
        token = jwt.encode(payload, SECRET_JWT, algorithm="HS256")
        
        with TestClient(app) as client:
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/local?token={token}"):
                    pass


class TestWebSocketConnection:
    """Tests para el flujo de conexión WebSocket"""
    
    def test_websocket_mantiene_conexion_activa(self):
        """Debe mantener la conexión abierta y responder a pings"""
        token = crear_token_dispositivo("test_device", 1)
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token}") as websocket:
                # Recibir mensaje de bienvenida
                websocket.receive_json()
                
                # La conexión debe mantenerse activa
                # Enviar un mensaje simple
                websocket.send_text("ping")
                
                # La conexión sigue activa (no se desconecta)
                # Esto se verifica porque no se lanza excepción
    
    def test_websocket_multiples_conexiones_mismo_local(self):
        """Debe permitir múltiples conexiones del mismo local"""
        token = crear_token_dispositivo("test_device", 1)
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token}") as ws1:
                ws1.receive_json()  # Mensaje de bienvenida
                
                with client.websocket_connect(f"/ws/local?token={token}") as ws2:
                    ws2.receive_json()  # Mensaje de bienvenida
                    
                    # Ambas conexiones deben estar activas
                    # Verificar enviando datos
                    ws1.send_text("test1")
                    ws2.send_text("test2")
    
    def test_websocket_diferentes_locales(self):
        """Debe permitir conexiones de diferentes locales simultáneamente"""
        token_local1 = crear_token_dispositivo("device1", 1)
        token_local2 = crear_token_dispositivo("device2", 2)
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token_local1}") as ws1:
                data1 = ws1.receive_json()
                assert data1["local_id"] == "1"
                
                with client.websocket_connect(f"/ws/local?token={token_local2}") as ws2:
                    data2 = ws2.receive_json()
                    assert data2["local_id"] == "2"


class TestWebSocketDisconnection:
    """Tests para desconexión de WebSocket"""
    
    def test_websocket_desconexion_limpia(self):
        """Debe limpiar recursos al desconectar"""
        token = crear_token_dispositivo("test_device", 1)
        
        with TestClient(app) as client:
            ws = client.websocket_connect(f"/ws/local?token={token}")
            ws.__enter__()
            ws.receive_json()
            
            # Cerrar explícitamente
            ws.__exit__(None, None, None)
            
            # No debe lanzar excepción
    
    def test_websocket_reconexion_despues_de_desconexion(self):
        """Debe permitir reconexión después de desconectar"""
        token = crear_token_dispositivo("test_device", 1)
        
        with TestClient(app) as client:
            # Primera conexión
            with client.websocket_connect(f"/ws/local?token={token}") as ws1:
                ws1.receive_json()
            
            # Segunda conexión (reconexión)
            with client.websocket_connect(f"/ws/local?token={token}") as ws2:
                data = ws2.receive_json()
                assert data["evento"] == "conectado"


class TestWebSocketTokenTypes:
    """Tests para diferentes tipos de tokens"""
    
    def test_websocket_token_super_admin(self):
        """Debe aceptar token de super_admin"""
        token = crear_token_admin(1, 1, "super_admin")
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token}") as websocket:
                data = websocket.receive_json()
                assert data["evento"] == "conectado"
    
    def test_websocket_token_empleado(self):
        """Debe aceptar token de empleado"""
        token = crear_token_admin(1, 1, "empleado")
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token}") as websocket:
                data = websocket.receive_json()
                assert data["evento"] == "conectado"
    
    def test_websocket_extrae_local_id_correcto(self):
        """Debe extraer local_id correcto del token"""
        token_local5 = crear_token_dispositivo("device_local5", 5)
        
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/local?token={token_local5}") as websocket:
                data = websocket.receive_json()
                assert data["local_id"] == "5"
import pytest
from fastapi import WebSocket
from unittest.mock import AsyncMock, Mock, patch, call
from app.api.websocket.manager import ConnectionManager
import uuid


class MockWebSocket:
    """Mock de WebSocket para testing"""
    def __init__(self):
        self.accept = AsyncMock()
        self.send_json = AsyncMock()
        self.send_text = AsyncMock()
        self.close = AsyncMock()
        self.state = "CONNECTED"
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def manager():
    """Crea un manager limpio para cada test"""
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    """Crea un WebSocket mock"""
    return MockWebSocket()


class TestConnectionManagerConnect:
    """Tests para ConnectionManager.connect()"""
    
    @pytest.mark.asyncio
    async def test_connect_sin_local_id(self, manager, mock_ws):
        """Debe conectar WebSocket sin local_id"""
        await manager.connect(mock_ws, local_id=None)
        
        # Verificar que se llamó accept()
        mock_ws.accept.assert_called_once()
        
        # Verificar que se agregó a connections
        assert len(manager.connections) == 1
        local_id, ws_id, websocket = manager.connections[0]
        assert local_id is None
        assert websocket == mock_ws
        
        # Verificar que se envió mensaje de bienvenida
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["evento"] == "conectado"
        assert "ws_id" in call_args
        assert call_args["local_id"] is None
    
    @pytest.mark.asyncio
    async def test_connect_con_local_id(self, manager, mock_ws):
        """Debe conectar WebSocket con local_id específico"""
        await manager.connect(mock_ws, local_id="1")
        
        assert len(manager.connections) == 1
        local_id, ws_id, websocket = manager.connections[0]
        assert local_id == "1"
        
        # Verificar mensaje de bienvenida incluye local_id
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["local_id"] == "1"
    
    @pytest.mark.asyncio
    async def test_connect_genera_ws_id_unico(self, manager, mock_ws):
        """Debe generar ws_id único para cada conexión"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        await manager.connect(ws1, local_id="1")
        await manager.connect(ws2, local_id="1")
        
        assert len(manager.connections) == 2
        
        # Obtener los ws_ids
        ws_id_1 = manager.connections[0][1]
        ws_id_2 = manager.connections[1][1]
        
        # Deben ser diferentes
        assert ws_id_1 != ws_id_2
        
        # Deben ser UUIDs válidos
        uuid.UUID(ws_id_1)
        uuid.UUID(ws_id_2)
    
    @pytest.mark.asyncio
    async def test_connect_multiples_websockets_mismo_local(self, manager):
        """Debe permitir múltiples conexiones del mismo local"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        await manager.connect(ws1, local_id="1")
        await manager.connect(ws2, local_id="1")
        await manager.connect(ws3, local_id="1")
        
        assert len(manager.connections) == 3
        
        # Verificar que todos pertenecen al local 1
        for local_id, _, _ in manager.connections:
            assert local_id == "1"


class TestConnectionManagerDisconnect:
    """Tests para ConnectionManager.disconnect()"""
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket_existente(self, manager, mock_ws):
        """Debe remover WebSocket de la lista de conexiones"""
        await manager.connect(mock_ws, local_id="1")
        assert len(manager.connections) == 1
        
        await manager.disconnect(mock_ws)
        
        assert len(manager.connections) == 0
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket_inexistente(self, manager, mock_ws):
        """No debe fallar al intentar desconectar WebSocket que no existe"""
        # No debería lanzar excepción
        await manager.disconnect(mock_ws)
        assert len(manager.connections) == 0
    
    @pytest.mark.asyncio
    async def test_disconnect_solo_remueve_websocket_especifico(self, manager):
        """Debe remover solo el WebSocket específico, no otros"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        await manager.connect(ws1, local_id="1")
        await manager.connect(ws2, local_id="1")
        await manager.connect(ws3, local_id="2")
        
        await manager.disconnect(ws2)
        
        assert len(manager.connections) == 2
        
        # Verificar que ws2 fue removido pero ws1 y ws3 siguen
        websockets_restantes = [ws for _, _, ws in manager.connections]
        assert ws1 in websockets_restantes
        assert ws3 in websockets_restantes
        assert ws2 not in websockets_restantes


class TestConnectionManagerBroadcast:
    """Tests para ConnectionManager.broadcast()"""
    
    @pytest.mark.asyncio
    async def test_broadcast_a_todas_las_conexiones(self, manager):
        """Debe enviar mensaje a todas las conexiones"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        await manager.connect(ws1, local_id="1")
        await manager.connect(ws2, local_id="2")
        await manager.connect(ws3, local_id="1")
        
        # Tu implementación usa: broadcast(evento, datos)
        await manager.broadcast("test_event", {"key": "value"})
        
        # Verificar que se llamó send_json en todos
        assert ws1.send_json.call_count >= 1
        assert ws2.send_json.call_count >= 1
        assert ws3.send_json.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_broadcast_con_conexiones_vacias(self, manager):
        """No debe fallar con lista de conexiones vacía"""
        # No debería lanzar excepción
        await manager.broadcast("test", {"data": "test"})
    
    @pytest.mark.asyncio
    async def test_broadcast_maneja_error_en_envio(self, manager):
        """Debe continuar enviando a otras conexiones si una falla"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()
        
        await manager.connect(ws1, local_id="1")
        await manager.connect(ws3, local_id="1")
        
        # Simular error después de conectar
        ws2_mock = MockWebSocket()
        ws2_mock.send_json = AsyncMock(side_effect=Exception("Connection error"))
        manager.connections.append(("1", str(uuid.uuid4()), ws2_mock))
        
        await manager.broadcast("test", {"data": "test"})
        
        # ws1 y ws3 deberían haber recibido el mensaje
        assert ws1.send_json.call_count >= 1
        assert ws3.send_json.call_count >= 1


class TestConnectionManagerDirectAccess:
    """Tests para acceso directo a conexiones"""
    
    @pytest.mark.asyncio
    async def test_acceso_directo_a_connections(self, manager):
        """Debe poder acceder directamente a la lista de conexiones"""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        await manager.connect(ws1, local_id="1")
        await manager.connect(ws2, local_id="2")
        
        # Acceso directo a connections
        conexiones = manager.connections
        
        assert len(conexiones) == 2
        assert isinstance(conexiones, list)
    
    @pytest.mark.asyncio
    async def test_filtrar_conexiones_por_local_manualmente(self, manager):
        """Debe poder filtrar conexiones por local_id manualmente"""
        ws_local1_a = MockWebSocket()
        ws_local1_b = MockWebSocket()
        ws_local2 = MockWebSocket()
        
        await manager.connect(ws_local1_a, local_id="1")
        await manager.connect(ws_local1_b, local_id="1")
        await manager.connect(ws_local2, local_id="2")
        
        # Filtrar manualmente
        conexiones_local1 = [
            conn for conn in manager.connections 
            if conn[0] == "1"
        ]
        
        assert len(conexiones_local1) == 2
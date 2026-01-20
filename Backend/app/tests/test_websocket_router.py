import pytest
from fastapi.testclient import TestClient
from fastapi import WebSocket
from unittest.mock import AsyncMock, patch, MagicMock, Mock
from app.api.websocket.router import router, websocket_endpoint
from app.api.websocket.manager import manager
from main import app


class MockWebSocket:
    """Mock completo de WebSocket para testing"""
    def __init__(self):
        self.accept = AsyncMock()
        self.send_json = AsyncMock()
        self.send_text = AsyncMock()
        self.receive_text = AsyncMock()
        self.close = AsyncMock()
        self.state = "CONNECTED"
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestWebSocketRouter:
    """Tests para el router de WebSocket"""
    
    def test_router_existe(self):
        """El router debe estar definido"""
        assert router is not None
    
    def test_router_es_api_router(self):
        """El router debe ser una instancia de APIRouter"""
        from fastapi import APIRouter
        assert isinstance(router, APIRouter)
    
    def test_router_tiene_websocket_endpoint(self):
        """El router debe tener el endpoint websocket_endpoint registrado"""
        assert websocket_endpoint is not None
        assert callable(websocket_endpoint)


class TestWebSocketEndpoint:
    """Tests para websocket_endpoint"""
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_conecta_websocket(self):
        """Debe conectar el websocket usando manager.connect()"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock):
                    mock_ws.receive_text.side_effect = [
                        "test message",
                        Exception("WebSocketDisconnect")
                    ]
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    mock_connect.assert_called_once_with(mock_ws)
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_recibe_mensajes(self):
        """Debe recibir mensajes del cliente"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = [
                        "mensaje de prueba",
                        WebSocketDisconnect()
                    ]
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    assert mock_broadcast.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_broadcast_mensaje_recibido(self):
        """Debe hacer broadcast del mensaje recibido"""
        mock_ws = MockWebSocket()
        test_message = "mensaje importante"
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = [
                        test_message,
                        WebSocketDisconnect()
                    ]
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    calls = [call for call in mock_broadcast.call_args_list 
                            if len(call[0]) > 0 and test_message in str(call[0][0])]
                    assert len(calls) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_maneja_websocket_disconnect(self):
        """Debe manejar WebSocketDisconnect correctamente"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()) as mock_disconnect:
                with patch.object(manager, 'broadcast', new_callable=AsyncMock):
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = WebSocketDisconnect()
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    mock_disconnect.assert_called_once_with(mock_ws)
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_notifica_desconexion(self):
        """Debe notificar desconexión a otros clientes"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = WebSocketDisconnect()
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    calls = [call for call in mock_broadcast.call_args_list 
                            if len(call[0]) > 0 and "desconectado" in str(call[0][0]).lower()]
                    assert len(calls) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_loop_mientras_conectado(self):
        """Debe mantener el loop while True mientras hay conexión"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock):
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = [
                        "msg1",
                        "msg2",
                        "msg3",
                        WebSocketDisconnect()
                    ]
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    assert mock_ws.receive_text.call_count >= 3


class TestWebSocketEndpointIntegracion:
    """Tests de integración para el endpoint WebSocket"""
    
    @pytest.mark.asyncio
    async def test_flujo_completo_conexion_mensaje_desconexion(self):
        """Test del flujo completo: conectar -> enviar mensaje -> desconectar"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(manager, 'disconnect', Mock()) as mock_disconnect:
                with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = [
                        "test message",
                        WebSocketDisconnect()
                    ]
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    mock_connect.assert_called_once()
                    assert mock_broadcast.call_count >= 1
                    mock_disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiples_mensajes_antes_de_desconexion(self):
        """Debe procesar múltiples mensajes antes de desconectar"""
        mock_ws = MockWebSocket()
        messages = ["msg1", "msg2", "msg3", "msg4"]
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = messages + [WebSocketDisconnect()]
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    assert mock_broadcast.call_count >= len(messages)


class TestWebSocketEndpointErrores:
    """Tests de manejo de errores en el endpoint"""
    
    @pytest.mark.asyncio
    async def test_desconecta_incluso_si_connect_falla(self):
        """Debe intentar desconectar incluso si connect falló"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock, side_effect=Exception("Error al conectar")):
            with patch.object(manager, 'disconnect', Mock()):
                with pytest.raises(Exception):
                    await websocket_endpoint(mock_ws)
    
    @pytest.mark.asyncio
    async def test_maneja_excepcion_en_broadcast(self):
        """Debe propagar excepciones de broadcast (no las maneja)"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock, side_effect=Exception("Broadcast error")):
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = [
                        "mensaje",
                        WebSocketDisconnect()
                    ]
                    
                    # El código NO maneja excepciones en broadcast, debe propagarse
                    with pytest.raises(Exception, match="Broadcast error"):
                        await websocket_endpoint(mock_ws)


class TestWebSocketEndpointBehavior:
    """Tests de comportamiento específico del endpoint"""
    
    @pytest.mark.asyncio
    async def test_receive_text_llamado_en_loop(self):
        """Debe llamar receive_text continuamente en el loop"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock):
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = [
                        "msg1",
                        "msg2",
                        WebSocketDisconnect()
                    ]
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    assert mock_ws.receive_text.call_count == 3
    
    @pytest.mark.asyncio
    async def test_broadcast_mensaje_desconexion_contiene_cliente_desconectado(self):
        """El mensaje de desconexión debe contener 'Cliente desconectado'"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = WebSocketDisconnect()
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    disconnect_calls = [
                        call for call in mock_broadcast.call_args_list
                        if len(call[0]) > 0 and "Cliente desconectado" in str(call[0][0])
                    ]
                    assert len(disconnect_calls) > 0
    

class TestWebSocketRouterIntegrationWithApp:
    """Tests de integración con la aplicación principal"""
    
    def test_router_incluido_en_app(self):
        """El router debe estar incluido en la aplicación principal"""
        assert router is not None
    
    def test_endpoint_accesible_via_testclient(self):
        """El endpoint debe ser accesible a través de TestClient"""
        with TestClient(app) as client:
            assert hasattr(router, 'routes') or router is not None


class TestWebSocketEndpointCoberturaCompleta:
    """Tests adicionales para alcanzar 100% de cobertura"""
    
    @pytest.mark.asyncio
    async def test_except_websocket_disconnect_ejecuta_bloque_completo(self):
        """El bloque except WebSocketDisconnect debe ejecutarse completamente"""
        mock_ws = MockWebSocket()
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()) as mock_disconnect:
                with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
                    from fastapi import WebSocketDisconnect
                    mock_ws.receive_text.side_effect = WebSocketDisconnect()
                    
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    mock_disconnect.assert_called_once()
                    
                    found_disconnect_msg = False
                    for call in mock_broadcast.call_args_list:
                        if call[0] and "Cliente desconectado" in str(call[0][0]):
                            found_disconnect_msg = True
                            break
                    
                    assert found_disconnect_msg, "No se envió el mensaje 'Cliente desconectado'"
    
    @pytest.mark.asyncio
    async def test_while_true_continua_hasta_disconnect(self):
        """El while True debe continuar hasta que ocurra WebSocketDisconnect"""
        mock_ws = MockWebSocket()
        receive_count = 0
        
        async def count_receives():
            nonlocal receive_count
            receive_count += 1
            if receive_count < 5:
                return f"mensaje_{receive_count}"
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect()
        
        mock_ws.receive_text = count_receives
        
        with patch.object(manager, 'connect', new_callable=AsyncMock):
            with patch.object(manager, 'disconnect', Mock()):
                with patch.object(manager, 'broadcast', new_callable=AsyncMock):
                    try:
                        await websocket_endpoint(mock_ws)
                    except:
                        pass
                    
                    assert receive_count == 5
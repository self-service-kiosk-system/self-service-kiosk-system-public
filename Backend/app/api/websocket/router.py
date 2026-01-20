from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Endpoint principal de WebSocket para comunicación en tiempo real"""
    await manager.connect(websocket)
    try:
        while True:
            # Recibir mensajes del cliente
            data = await websocket.receive_text()
            
            # Broadcast a todos los clientes conectados
            await manager.broadcast(data)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Cliente desconectado")
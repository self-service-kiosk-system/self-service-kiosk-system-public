from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.api.websocket.manager import manager
import jwt
from app.utils.utils import SECRET_JWT

websocket_router = APIRouter()


@websocket_router.websocket("/ws/local")  # ← SIN barra final
async def ws(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint con autenticación JWT.
    El token se envía como query parameter: ws://localhost:8000/ws/local?token=xxx
    """
    
    # 1. Verificar que el token existe
    if not token:
        await websocket.close(code=1008, reason="Token no proporcionado")
        return
    
    try:
        # 2. Decodificar y verificar el token
        payload = jwt.decode(token, SECRET_JWT, algorithms=["HS256"])
        
        # 3. Verificar que sea un token válido (dispositivo o admin)
        es_dispositivo = "device_id" in payload and "local_id" in payload
        es_admin = "user_id" in payload and "local_id" in payload
        
        if not es_dispositivo and not es_admin:
            await websocket.close(code=1008, reason="Token inválido")
            return
        
        # 4. Extraer local_id del token
        local_id = str(payload.get("local_id"))
        
        # 5. Conectar el WebSocket con el local_id
        await manager.connect(websocket, local_id=local_id)
        
        try:
            while True:
                # Mantener la conexión abierta
                data = await websocket.receive_text()
                # Opcional: manejar mensajes del cliente aquí
                
        except WebSocketDisconnect:
            await manager.disconnect(websocket)
            
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token expirado")
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Token inválido")
    except Exception as e:
        await websocket.close(code=1011, reason=f"Error: {str(e)}")

from fastapi import WebSocket
import uuid
import os
import json

from typing import Dict, Any, Optional, List

IS_DEV = os.getenv("ENVIRONMENT", "production") == "development"


class ConnectionManager:
    def __init__(self):
        # Estructura: [(local_id, ws_id, websocket)]
        self.connections: list[tuple[str | None, str, WebSocket]] = []

    async def connect(self, websocket: WebSocket, local_id: str | None = None):
        """Conecta un nuevo WebSocket y opcionalmente lo asigna a un local"""
        await websocket.accept()
        ws_id = str(uuid.uuid4())
        self.connections.append((local_id, ws_id, websocket))
        
        if IS_DEV:
            print(f"WS conectado: {ws_id} | Local: {local_id} | Total: {len(self.connections)}")
        
        # Enviar mensaje de bienvenida con el ID
        await websocket.send_json({
            "evento": "conectado",
            "ws_id": ws_id,
            "local_id": local_id
        })

    async def disconnect(self, websocket: WebSocket):
        """Desconecta un WebSocket"""
        ws_id = None
        local_id = None
        
        for l, w, ws in self.connections:
            if ws == websocket:
                ws_id = w
                local_id = l
                break
        
        self.connections = [
            (l, w, ws) for (l, w, ws) in self.connections if ws != websocket
        ]
        
        if IS_DEV and ws_id:
            print(f"WS desconectado: {ws_id} | Local: {local_id} | Total: {len(self.connections)}")
        
        try:
            await websocket.close()
        except Exception:
            pass

    async def broadcast(
        self,
        evento: str,
        datos: Dict[str, Any],
        local_id: str | None = None
    ):
        """
        Envía un evento a los clientes conectados.
        Args:
            evento: Tipo de evento ('producto_creado', 'producto_actualizado', etc.)
            datos: Payload del evento
            local_id: Si se especifica, solo envía a ese local. Si es None, envía a todos.
        """
        mensaje = json.dumps({
            "evento": evento,
            "datos": datos
        })
        
        enviados = 0
        for l, w, ws in self.connections:
            # Enviar si:
            # - local_id es None (broadcast general), O
            # - el ws está en el mismo local, O
            # - el ws no tiene local asignado (admin/monitor)
            if local_id is None or l == str(local_id) or l is None:
                try:
                    await ws.send_text(mensaje)
                    enviados += 1
                except Exception as e:
                    if IS_DEV:
                        print(f"Error enviando a {w}: {e}")
        
        if IS_DEV:
            print(f" Evento '{evento}' enviado a {enviados} conexiones | Local: {local_id}")

    async def broadcast_to_local(self, local_id: int, message: dict):
        """
        Envía un mensaje a todos los dispositivos de un local específico.
        Args:
            local_id: ID del local
            message: Diccionario con 'titulo' y 'datos'
        """
        evento = message.get("titulo", "unknown")
        datos = message.get("datos", {})
        
        mensaje = json.dumps({
            "evento": evento,
            "datos": datos
        })
        
        enviados = 0
        local_id_str = str(local_id)
        
        for l, w, ws in self.connections:
            # Enviar solo a conexiones del mismo local
            if l == local_id_str:
                try:
                    await ws.send_text(mensaje)
                    enviados += 1
                    if IS_DEV:
                        print(f" Enviado a WS {w} del local {l}")
                except Exception as e:
                    if IS_DEV:
                        print(f"Error enviando a {w}: {e}")
        
        if IS_DEV:
            print(f" Evento '{evento}' enviado a {enviados} conexiones del local {local_id}")

    def set_local(self, ws_id: str, local_id: str):
        """Actualiza el local_id de una conexión existente"""
        for i, (l, w, ws) in enumerate(self.connections):
            if w == ws_id:
                self.connections[i] = (local_id, ws_id, ws)
                if IS_DEV:
                    print(f"WS {ws_id} asignado a local_id={local_id}")
                return True
        return False


manager = ConnectionManager()

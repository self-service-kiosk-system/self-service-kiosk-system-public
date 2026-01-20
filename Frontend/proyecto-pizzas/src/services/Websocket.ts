const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

let socket: WebSocket | null = null;
let listeners: Record<string, ((datos: any) => void)[]> = {};
let reconnectTimeout: NodeJS.Timeout | null = null;
let isConnecting = false;

export type WSMessage = {
  titulo: string;
  datos?: any;
  [key: string]: any;
};

export const connectWebSocket = (): void => {
  // Evitar múltiples intentos de conexión simultáneos
  if (socket || isConnecting) {
    console.log(" WebSocket ya está conectado o conectándose");
    return;
  }

  // Leer desde localStorage primero, luego adminToken
  const token = localStorage.getItem('device_token') || localStorage.getItem('adminToken');
  
  if (!token) {
    console.error(" No hay token disponible para WebSocket");
    return;
  }

  isConnecting = true;
  const wsUrlWithToken = `${WS_URL}/ws/local?token=${token}`;
  console.log(" Conectando WebSocket a:", wsUrlWithToken);
  
  try {
    socket = new WebSocket(wsUrlWithToken);

    socket.onopen = () => {
      console.log(" Conectado al WebSocket");
      isConnecting = false;
      
      // Limpiar timeout de reconexión si existía
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
    };

    socket.onmessage = (event: MessageEvent) => {
      try {
        const data: WSMessage = JSON.parse(event.data);
        console.log("Mensaje recibido:", data);
        
        if (data.evento && listeners[data.evento]) {
          listeners[data.evento].forEach((cb) => cb(data.datos));
        } else {
          console.log("ℹEvento sin listener:", data.evento);
        }
      } catch (err) {
        console.error(" Error parseando mensaje:", err);
      }
    };

    socket.onclose = (event) => {
      console.log(` WebSocket cerrado. Código: ${event.code}, Razón: ${event.reason}`);
      socket = null;
      isConnecting = false;
      
      // Solo reconectar si no fue un cierre intencional (código 1000 = normal)
      if (event.code !== 1000) {
        console.log(" Programando reconexión en 5 segundos...");
        reconnectTimeout = setTimeout(() => {
          console.log(" Intentando reconectar...");
          connectWebSocket();
        }, 5000);
      }
    };

    socket.onerror = (error) => {
      console.error(" Error WebSocket:", error);
      isConnecting = false;
    };
    
  } catch (error) {
    console.error(" Error creando WebSocket:", error);
    isConnecting = false;
  }
};

export const disconnectWebSocket = (): void => {
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  
  if (socket) {
    socket.close(1000, "Desconexión manual");
    socket = null;
  }
  
  isConnecting = false;
  console.log(" WebSocket desconectado manualmente");
};

export const sendWebSocketMessage = (message: WSMessage): void => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message));
  } else {
    console.error(" WebSocket no está conectado");
  }
};

export const on = (evento: string, callback: (datos: any) => void): void => {
  if (!listeners[evento]) listeners[evento] = [];
  listeners[evento].push(callback);
  console.log(` Listener registrado para evento: ${evento}`);
};

export const off = (evento: string, callback: (datos: any) => void): void => {
  if (!listeners[evento]) return;
  listeners[evento] = listeners[evento].filter((cb) => cb !== callback);
  if (listeners[evento].length === 0) {
    delete listeners[evento];
    console.log(` Listener eliminado para evento: ${evento}`);
  }
};

export { socket };

export const __resetForTests = () => {
  disconnectWebSocket();
  listeners = {};
};
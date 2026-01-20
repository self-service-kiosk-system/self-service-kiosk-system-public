// Configuración de URLs del backend
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// Helper para construir URLs de endpoints
export const buildApiUrl = (endpoint) => {
  // Asegura que el endpoint comience con /
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_URL}${path}`;
};

// Helper para construir URLs de WebSocket
export const buildWsUrl = (endpoint) => {
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${WS_URL}${path}`;
};

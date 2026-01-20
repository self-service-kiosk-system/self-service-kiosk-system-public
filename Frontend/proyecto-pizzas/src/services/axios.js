import axios from 'axios';

// Instancia de axios preconfigurada con la URL base y manejo automático de tokens
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor: agrega automáticamente el token de admin en cada petición
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('adminToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para manejar errores 401 (token expirado)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token inválido, limpiar localStorage y redirigir
      localStorage.removeItem('adminToken');
      localStorage.removeItem('adminLocalId');
      localStorage.removeItem('adminNombre');
      localStorage.removeItem('adminRol');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
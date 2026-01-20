// App.tsx
import React, { createContext, useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Menu from './components/Menu/Menu';
import LoginAdmin from './components/Admin/LoginAdmin';
import PanelAdmin from './components/Admin/PanelAdmin';
import AgregarProducto from './components/Admin/AgregarProducto';
import EditarProducto from './components/Admin/EditarProducto';
import ProtectedRoute from './components/Admin/Protection';
import Carrusel from './components/Carrusel/Carrusel';
import { connectWebSocket, disconnectWebSocket } from './services/Websocket';

interface DemoContextType {
  isDemoMode: boolean;
  showDemoAlert: () => void;
}

export const DemoContext = createContext<DemoContextType>({
  isDemoMode: false,
  showDemoAlert: () => {}
});

const ProtectedApp = ({ children }) => {
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);

  const showDemoAlert = () => {
    alert('Modo Demo: Esta funcionalidad no está disponible en el modo de demostración.');
  };

  useEffect(() => {
    const authenticateDevice = async () => {
      try {
        // Verificar si hay token guardado
        const storedToken = localStorage.getItem('device_token');
        const storedDeviceId = localStorage.getItem('device_id');

        if (storedToken && storedDeviceId) {
          console.log(' Token encontrado en localStorage, verificando...');
          
          const response = await fetch(`${import.meta.env.VITE_API_URL}/verify`, {
            method: 'GET',
            headers: { 
              'Authorization': `Bearer ${storedToken}`,
              'Content-Type': 'application/json' 
            }
          });

          if (response.ok) {
            console.log(' Token válido - Acceso autorizado');
            setIsAuthorized(true);
            
            // Detectar modo demo
            if (storedDeviceId === 'public') {
              console.log('Modo demo detectado');
              setIsDemoMode(true);
            }
            
            connectWebSocket();
            
            // OCULTAR CURSOR si es kiosko (después de verificar)
            if (storedDeviceId.startsWith('raspberry_')) {
              const style = document.createElement('style');
              style.id = 'kiosk-cursor-style';
              style.innerHTML = `html, body, * { cursor: none !important; }`;
              if (!document.getElementById('kiosk-cursor-style')) {
                document.head.appendChild(style);
              }
            }
            
            return;
          } else {
            console.log(' Token expirado, limpiando...');
            localStorage.clear();
          }
        }

        //  Verificar credenciales en URL
        const params = new URLSearchParams(window.location.search);
        const deviceId = params.get('device_id');
        const secretKey = params.get('secret_key');

        if (!deviceId || !secretKey) {
          console.log('Sin credenciales - Acceso denegado');
          setIsAuthorized(false);
          return;
        }

        console.log(' Autenticando con credenciales de URL...');
        
        const authResponse = await fetch(`${import.meta.env.VITE_API_URL}/auth/device`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device_id: deviceId, secret_key: secretKey })
        });

        if (!authResponse.ok) {
          console.log(' Credenciales inválidas');
          setIsAuthorized(false);
          return;
        }

        const data = await authResponse.json();
        
        // Guardar en localStorage
        localStorage.setItem('device_token', data.token);
        localStorage.setItem('device_id', data.device_id);
        console.log(' Token guardado en localStorage');
        
        // Detectar modo demo
        if (deviceId === 'public') {
          console.log('Modo demo activado');
          setIsDemoMode(true);
        }
        
        // OCULTAR CURSOR si es kiosko (ANTES de limpiar URL)
        if (deviceId.startsWith('raspberry_')) {
          const style = document.createElement('style');
          style.id = 'kiosk-cursor-style';
          style.innerHTML = `html, body, * { cursor: none !important; }`;
          document.head.appendChild(style);
        }
        
        // Limpiar URL
        window.history.replaceState({}, '', '/');
        
        console.log(' Autenticación exitosa');
        setIsAuthorized(true);
        connectWebSocket();
        
      } catch (error) {
        console.error(' Error crítico:', error);
        setIsAuthorized(false);
      } finally {
        setIsLoading(false);
      }
    };

    authenticateDevice();

    return () => {
      disconnectWebSocket();
    };
  }, []);

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '1.5rem'
      }}>
        Verificando dispositivo...
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div style={{ 
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        fontFamily: 'Arial, sans-serif',
        backgroundColor: '#f5f5f5'
      }}>
        <h1 style={{ 
          fontSize: '120px', 
          margin: '0',
          color: '#333'
        }}>
          404
        </h1>
        <p style={{ 
          fontSize: '24px', 
          color: '#666',
          margin: '10px 0'
        }}>
          Página no encontrada
        </p>
      </div>
    );
  }

  return (
    <DemoContext.Provider value={{ isDemoMode, showDemoAlert }}>
      {children}
    </DemoContext.Provider>
  );
};


function App() {
  return (
    <Router>
      <ProtectedApp>
        <Routes>
          <Route path="/" element={<Menu />} />
          <Route path="/carrusel" element={<Carrusel />} />   {/* Pública */}
          <Route path="/login" element={<LoginAdmin />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <PanelAdmin />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/agregar"
            element={
              <ProtectedRoute>
                <AgregarProducto />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/editar/:id"
            element={
              <ProtectedRoute>
                <EditarProducto />
              </ProtectedRoute>
            }
          />
        </Routes>
      </ProtectedApp>
    </Router>
  );
}

export default App;
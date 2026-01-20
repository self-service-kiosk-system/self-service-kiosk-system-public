import { useContext, useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { DemoContext } from '../../App';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const { isDemoMode } = useContext(DemoContext);
  const [verificando, setVerificando] = useState(true);
  const [autorizado, setAutorizado] = useState(false);

  useEffect(() => {
    const verificarToken = async () => {
      const token = localStorage.getItem('adminToken');
      
      if (!token) {
        setVerificando(false);
        return;
      }

      try {
        // CAMBIAR: usar /admin/verificar del endpoint de auth.py
        const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/verificar`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          console.log('Token válido:', data);
          setAutorizado(true);
        } else {
          console.log('Token inválido');
          setAutorizado(false);
          // Limpiar localStorage si el token es inválido
          localStorage.removeItem('adminToken');
          localStorage.removeItem('adminLocalId');
          localStorage.removeItem('adminNombre');
          localStorage.removeItem('adminRol');
        }
      } catch (error) {
        console.error('Error verificando token:', error);
        setAutorizado(false);
      } finally {
        setVerificando(false);
      }
    };

    verificarToken();
  }, []);

  // En modo demo, permitir acceso sin token real
  if (isDemoMode) {
    return <>{children}</>;
  }

  if (verificando) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '1.5rem'
      }}>
        Verificando sesión...
      </div>
    );
  }

  return autorizado ? <>{children}</> : <Navigate to="/login" />;
};

export default ProtectedRoute;
import { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { DemoContext } from '../../App';
import './LoginAdmin.css';

const LoginAdmin = () => {
  const [usuario, setUsuario] = useState('');
  const [contrasena, setContrasena] = useState('');
  const [mostrarContrasena, setMostrarContrasena] = useState(false);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const navigate = useNavigate();
  const { isDemoMode } = useContext(DemoContext);

  useEffect(() => {
    // Si es modo demo, usar el device_token como adminToken y redirigir
    if (isDemoMode) {
      loginDemo();
      return;
    }

    // Verificar si ya hay sesion activa
    const token = localStorage.getItem('adminToken');
    if (token) {
      navigate('/admin');
    }
  }, [navigate, isDemoMode]);

  const loginDemo = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          usuario: 'Demo', 
          contrasena: 'demo123' 
        }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('adminToken', data.token);
        localStorage.setItem('adminLocalId', data.local_id.toString());
        localStorage.setItem('adminNombre', data.usuario);
        localStorage.setItem('is_demo_admin', 'true');
        navigate('/admin');
      }
    } catch (err) {
      console.error('Error en login demo:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setCargando(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          usuario, 
          contrasena 
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al iniciar sesión');
      }

      const data = await response.json();
      
      localStorage.setItem('adminToken', data.token);
      localStorage.setItem('adminLocalId', data.local_id.toString());
      localStorage.setItem('adminNombre', data.usuario);
      localStorage.setItem('adminRol', data.rol);
      
      console.log('Login exitoso, local_id:', data.local_id);
      
      navigate('/admin');
    } catch (err: any) {
      setError(err.message || 'Error al iniciar sesión');
      console.error('Error en login:', err);
    } finally {
      setCargando(false);
    }
  };

  // Si es modo demo, mostrar mensaje mientras redirige
  if (isDemoMode) {
    return (
      <div className="login-container">
        <div className="login-card">
          <p>Accediendo al panel de administracion... (en modo demo esto puede demorar mas de lo esperado)</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Panel de Administración</h1>
        <form onSubmit={handleSubmit} autoComplete="off">
          <div className="form-group">
            <label htmlFor="usuario">Usuario</label>
            <input
              type="text"
              id="usuario"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              required
              disabled={cargando}
              autoComplete="off"
            />
          </div>

          <div className="form-group">
            <label htmlFor="contrasena">Contraseña</label>
            <div className="password-input">
              <input
                type={mostrarContrasena ? 'text' : 'password'}
                id="contrasena"
                value={contrasena}
                onChange={(e) => setContrasena(e.target.value)}
                required
                disabled={cargando}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setMostrarContrasena(!mostrarContrasena)}
                tabIndex={-1}
              >
                {mostrarContrasena ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>
          </div>

          {error && <p className="error-message">{error}</p>}

          <button type="submit" disabled={cargando} className="btn-login">
            {cargando ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginAdmin;
import { useEffect, useState, useRef, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { on, off } from '../../services/Websocket';
import { preloadAndCacheImage, clearBlobCache } from '../../services/ImageCache';
import './Menu.css';

interface Categoria {
  id: number;
  nombre: string;
}

interface Producto {
  id: number;
  nombre: string;
  descripcion: string;
  precio: number;
  imagen_url: string | null;
  disponible: boolean;
  destacado?: boolean;
  categorias: {
    id: number;
    nombre: string;
  } | null;
}

// Componente optimizado para imágenes con caché persistente
const MenuImage = memo(({ src, alt }: { src: string | null; alt: string }) => {
  const [imageSrc, setImageSrc] = useState<string>('');
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (!src) {
      setIsLoaded(true);
      return;
    }
    
    let isMounted = true;
    
    preloadAndCacheImage(src).then(cachedUrl => {
      if (isMounted) {
        setImageSrc(cachedUrl);
        setIsLoaded(true);
      }
    });
    
    return () => { isMounted = false; };
  }, [src]);

  if (!src) {
    return <div className="sin-imagen">Sin imagen</div>;
  }

  if (!isLoaded) {
    return <div className="imagen-loading" />;
  }

  return (
    <img 
      src={imageSrc} 
      alt={alt}
      loading="lazy"
      decoding="async"
    />
  );
});

MenuImage.displayName = 'MenuImage';

function MenuKiosk() {
  const navigate = useNavigate();
  const [productos, setProductos] = useState<Producto[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [localId, setLocalId] = useState<number | null>(null);
  const [localNombre, setLocalNombre] = useState<string>('');
  const [categoriaActiva, setCategoriaActiva] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [isAdminLogged, setIsAdminLogged] = useState(false);
  
  const categoriaRefs = useRef<{ [key: number]: HTMLDivElement | null }>({});

  useEffect(() => {
    const deviceToken = localStorage.getItem('device_token');
    
    if (deviceToken) {
      try {
        const payload = JSON.parse(atob(deviceToken.split('.')[1]));
        setLocalId(payload.local_id);
      } catch (error) {
        console.error('❌ Error decodificando token:', error);
      }
    }
  }, []);

  useEffect(() => {
    if (localId) {
      cargarDatos();
    }
  }, [localId]);

  const cargarDatos = async () => {
    try {
      const deviceToken = localStorage.getItem('device_token');
      
      const productosResponse = await fetch(
        `${import.meta.env.VITE_API_URL}/menu/productos?local_id=${localId}`,
        {
          headers: { 'Authorization': `Bearer ${deviceToken}` }
        }
      );

      if (productosResponse.ok) {
        const productosData = await productosResponse.json();
        const productosConImagenes = productosData.map((p: any) => {
          let imagen_url = p.imagen_url;
          if (imagen_url && !imagen_url.startsWith('http')) {
            imagen_url = `${import.meta.env.VITE_API_URL}${imagen_url}`;
          }
          return { ...p, imagen_url };
        });
        setProductos(productosConImagenes);
      }

      const categoriasResponse = await fetch(
        `${import.meta.env.VITE_API_URL}/menu/categorias?local_id=${localId}`,
        {
          headers: { 'Authorization': `Bearer ${deviceToken}` }
        }
      );

      if (categoriasResponse.ok) {
        const categoriasData = await categoriasResponse.json();
        setCategorias(categoriasData);
        if (categoriasData.length > 0) {
          setCategoriaActiva(categoriasData[0].id);
        }
      }

      setLocalNombre(`Di Polo`);
      
    } catch (error) {
      console.error('❌ Error cargando datos:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!localId) return;

    // ========== PRODUCTOS ==========
    const handleProductoCreado = (producto: Producto) => {
      console.log('🆕 Producto creado:', producto);
      
      if (producto.imagen_url && !producto.imagen_url.startsWith('http')) {
        producto.imagen_url = `${import.meta.env.VITE_API_URL}${producto.imagen_url}`;
      }
      
      setProductos(prev => [...prev, producto]);
    };

    const handleProductoActualizado = (producto: Producto) => {
      console.log('✏️ Producto actualizado:', producto);
      
      if (producto.imagen_url && !producto.imagen_url.startsWith('http')) {
        producto.imagen_url = `${import.meta.env.VITE_API_URL}${producto.imagen_url}`;
      }
      
      setProductos(prev =>
        prev.map(p => (p.id === producto.id ? producto : p))
      );
    };

    const handleProductoEliminado = (datos: { id: number }) => {
      console.log('🗑️ Producto eliminado:', datos.id);
      setProductos(prev => prev.filter(p => p.id !== datos.id));
    };

    // ========== CATEGORÍAS ==========
    const handleCategoriaCreada = (categoria: Categoria) => {
      console.log('🆕 Categoría creada:', categoria);
      
      setCategorias(prev => {
        // Evitar duplicados
        if (prev.some(c => c.id === categoria.id)) {
          return prev;
        }
        // Agregar al final (se ordenará por "orden" en el backend)
        return [...prev, categoria];
      });
    };

    // Registrar listeners
    on('producto_creado', handleProductoCreado);
    on('producto_actualizado', handleProductoActualizado);
    on('producto_eliminado', handleProductoEliminado);
    on('categoria_creada', handleCategoriaCreada); // ✅ NUEVO

    // Cleanup al desmontar
    return () => {
      off('producto_creado', handleProductoCreado);
      off('producto_actualizado', handleProductoActualizado);
      off('producto_eliminado', handleProductoEliminado);
      off('categoria_creada', handleCategoriaCreada); // ✅ NUEVO
      
      // Limpiar blob URLs de memoria (no el cache persistente)
      clearBlobCache();
    };
  }, [localId]);

  const scrollToCategoria = (categoriaId: number) => {
    setCategoriaActiva(categoriaId);
    const element = categoriaRefs.current[categoriaId];
    if (element) {
      const headerHeight = 180;
      const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
      const offsetPosition = elementPosition - headerHeight;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  };

  useEffect(() => {
    const handleScroll = () => {
      const headerHeight = 180;
      
      for (const [id, element] of Object.entries(categoriaRefs.current)) {
        if (element) {
          const rect = element.getBoundingClientRect();
          if (rect.top <= headerHeight + 50 && rect.bottom >= headerHeight) {
            setCategoriaActiva(Number(id));
            break;
          }
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'A') {
        navigate('/login');
      }
    };
    
    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [navigate]);

  useEffect(() => {
    const checkAdminSession = () => {
      const adminToken = localStorage.getItem('adminToken');
      setIsAdminLogged(!!adminToken);
    };

    checkAdminSession();

    // Verificar cada segundo si el token sigue presente
    const interval = setInterval(checkAdminSession, 1000);

    return () => clearInterval(interval);
  }, []);

  const productosPorCategoria = categorias.map(categoria => ({
    ...categoria,
    productos: productos.filter(p => p.categorias?.id === categoria.id)
  })).filter(cat => cat.productos.length > 0);

  if (loading) {
    return (
      <div className="menu-loading">
        <div className="spinner"></div>
        <p>Cargando menú...</p>
      </div>
    );
  }

  return (
    <div className="menu-kiosk-container">
      <header className="menu-header">
        <div className="header-titulo">
          <h1 className="local-nombre">{localNombre}</h1>
          <p className="local-subtitulo">Pastas Caseras</p>
        </div>

        {isAdminLogged && (
          <button 
            className="btn-admin-panel"
            onClick={() => navigate('/admin')}
          >
            Panel de Administración
          </button>
        )}
        
        <div className="categorias-scroll-wrapper">
          <div className="categorias-selector">
            {categorias.map((categoria) => (
              <button
                key={categoria.id}
                className={`categoria-btn ${categoriaActiva === categoria.id ? 'activa' : ''}`}
                onClick={() => scrollToCategoria(categoria.id)}
              >
                {categoria.nombre}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="menu-content">
        {productosPorCategoria.map((categoria) => (
          <section
            key={categoria.id}
            className="categoria-section"
            ref={(el) => (categoriaRefs.current[categoria.id] = el)}
          >
            <h2 className="categoria-titulo">{categoria.nombre}</h2>
            
            <div className="productos-grid">
              {categoria.productos.map((producto) => (
                <div key={producto.id} className={`producto-card ${!producto.disponible ? 'sin-stock' : ''}`}>
                  <div className="producto-imagen">
                    {!producto.disponible && (
                      <div className="badge-sin-stock">Sin stock</div>
                    )}
                    <MenuImage src={producto.imagen_url} alt={producto.nombre} />
                  </div>
                  
                  <div className="producto-info">
                    <h3 className="producto-nombre">{producto.nombre}</h3>
                    <p className="producto-descripcion">{producto.descripcion}</p>
                    
                    <div className="producto-footer">
                      <span className="producto-precio">${producto.precio.toLocaleString('es-AR')}</span>
                      {producto.destacado && (
                        <span className="badge-destacado">Destacado</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="categoria-separador"></div>
          </section>
        ))}
      </main>

    </div>
  );
}

export default MenuKiosk;
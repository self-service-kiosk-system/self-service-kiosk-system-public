import { useState, useEffect, useCallback, memo, useRef } from "react";
import { connectWebSocket, disconnectWebSocket, on, off } from "../../services/Websocket";
import { useNavigate } from "react-router-dom";
import { preloadAndCacheImage, clearBlobCache } from "../../services/ImageCache";
import "./Carrusel.css";

interface Producto {
  id: number;
  nombre: string;
  descripcion: string;
  precio: number;
  imagen_url: string;
  disponible: boolean;
  categoria: string;
  destacado: boolean;
}

type CarruselMode = 'all' | 'featured' | 'categories';

interface CarruselConfig {
  mode: CarruselMode;
  selectedCategories: string[];
}

const getDefaultConfig = (): CarruselConfig => ({
  mode: 'all',
  selectedCategories: []
});

// Componente optimizado para imágenes con caché persistente
const OptimizedImage = memo(({ 
  src, 
  alt, 
  className,
  priority = false,
  preloadedUrl 
}: { 
  src: string; 
  alt: string; 
  className?: string;
  priority?: boolean;
  preloadedUrl?: string; // URL ya precargada
}) => {
  const [imageSrc, setImageSrc] = useState<string>(preloadedUrl || '');
  const [isLoaded, setIsLoaded] = useState(!!preloadedUrl);

  useEffect(() => {
    // Si ya tenemos la URL precargada, no hacer nada
    if (preloadedUrl) {
      setImageSrc(preloadedUrl);
      setIsLoaded(true);
      return;
    }
    
    if (!src) return;
    
    let isMounted = true;
    
    preloadAndCacheImage(src).then(cachedUrl => {
      if (isMounted) {
        setImageSrc(cachedUrl);
        setIsLoaded(true);
      }
    });
    
    return () => { isMounted = false; };
  }, [src, preloadedUrl]);

  if (!isLoaded) {
    return <div className="imagen-loading" />;
  }

  return (
    <img
      src={imageSrc}
      alt={alt}
      className={className}
      loading={priority ? "eager" : "lazy"}
      decoding="async"
    />
  );
});

OptimizedImage.displayName = 'OptimizedImage';

function Carrusel() {
  const navigate = useNavigate();
  
  // Detectar si es admin usando el token del localStorage
  const isAdmin = !!localStorage.getItem('adminToken');

  const [allProducts, setAllProducts] = useState<Producto[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Producto[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [localId, setLocalId] = useState<number>(1);
  
  // ✅ NUEVO: Mapa de imágenes precargadas (url original -> blob url)
  const [preloadedImages, setPreloadedImages] = useState<Map<string, string>>(new Map());
  const [imagesLoading, setImagesLoading] = useState(false);
  const preloadAbortRef = useRef<boolean>(false);
  
  // Config state
  const [config, setConfig] = useState<CarruselConfig>(getDefaultConfig);
  const [showPanel, setShowPanel] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  
  // Available categories
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);

  // Obtener local_id del token
  const getLocalId = useCallback(() => {
    const deviceToken = localStorage.getItem('device_token');
    let id = 1;
    
    if (deviceToken) {
      try {
        const payload = JSON.parse(atob(deviceToken.split('.')[1]));
        id = payload.local_id || 1;
      } catch (e) {
        console.error('Error decodificando token:', e);
      }
    }
    return id;
  }, []);

  // Fetch config from backend
  const fetchConfig = useCallback(async (localIdParam: number) => {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/carrusel/config?local_id=${localIdParam}`
      );
      
      if (response.ok) {
        const data = await response.json();
        setConfig({
          mode: data.mode || 'all',
          selectedCategories: data.selectedCategories || []
        });
      }
    } catch (err) {
      console.error('Error fetching carrusel config:', err);
    }
  }, []);

  // Save config to backend (solo admin)
  const saveConfigToBackend = useCallback(async (newConfig: CarruselConfig) => {
    if (!isAdmin) return;
    
    setSavingConfig(true);
    try {
      const adminToken = localStorage.getItem('adminToken');
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/carrusel/config?local_id=${localId}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${adminToken}`
          },
          body: JSON.stringify({
            mode: newConfig.mode,
            selectedCategories: newConfig.selectedCategories
          })
        }
      );
      
      if (!response.ok) {
        console.error('Error saving config:', await response.text());
      }
    } catch (err) {
      console.error('Error saving carrusel config:', err);
    } finally {
      setSavingConfig(false);
    }
  }, [isAdmin, localId]);

  // Fetch products
  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      
      const deviceToken = localStorage.getItem('device_token');
      const currentLocalId = getLocalId();
      setLocalId(currentLocalId);
      
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/menu/productos?local_id=${currentLocalId}`,
        {
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${deviceToken}` 
          }
        }
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar productos');
      }
      
      const data = await response.json();
      
      const productosConImagenes = data.map((p: any) => {
        let imagen_url = p.imagen_url;
        if (imagen_url && !imagen_url.startsWith('http')) {
          imagen_url = `${import.meta.env.VITE_API_URL}${imagen_url}`;
        }
        const categoria = p.categorias?.nombre || p.categoria || 'Sin categoría';
        return { 
          ...p, 
          imagen_url,
          categoria 
        };
      });
      
      const disponibles = productosConImagenes.filter((p: Producto) => p.disponible);
      setAllProducts(disponibles);
      
      const categories = [...new Set(disponibles.map((p: Producto) => p.categoria))].filter(Boolean).sort() as string[];
      setAvailableCategories(categories);
      
      // Fetch config después de obtener productos
      await fetchConfig(currentLocalId);
      
      setError(null);
    } catch (err) {
      setError("Error al cargar el menú");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [getLocalId, fetchConfig]);

  // ✅ NUEVO: Precargar TODAS las imágenes cuando cambian los productos
  useEffect(() => {
    if (allProducts.length === 0) return;
    
    preloadAbortRef.current = false;
    setImagesLoading(true);
    
    const preloadAllImages = async () => {
      const imageMap = new Map<string, string>();
      
      // Precargar todas las imágenes en paralelo
      const preloadPromises = allProducts.map(async (producto) => {
        if (preloadAbortRef.current) return;
        
        try {
          const cachedUrl = await preloadAndCacheImage(producto.imagen_url);
          imageMap.set(producto.imagen_url, cachedUrl);
        } catch (err) {
          console.warn(`Error precargando imagen de ${producto.nombre}:`, err);
          // Usar URL original como fallback
          imageMap.set(producto.imagen_url, producto.imagen_url);
        }
      });
      
      await Promise.all(preloadPromises);
      
      if (!preloadAbortRef.current) {
        setPreloadedImages(imageMap);
        setImagesLoading(false);
        console.log(`✅ ${imageMap.size} imágenes precargadas`);
      }
    };
    
    preloadAllImages();
    
    return () => {
      preloadAbortRef.current = true;
    };
  }, [allProducts]);

  // Filter products based on config
  useEffect(() => {
    let filtered: Producto[] = [];
    
    switch (config.mode) {
      case 'all':
        filtered = allProducts;
        break;
      case 'featured':
        filtered = allProducts.filter(p => p.destacado);
        break;
      case 'categories':
        if (config.selectedCategories.length > 0) {
          filtered = allProducts.filter(p => 
            config.selectedCategories.includes(p.categoria)
          );
        } else {
          filtered = allProducts;
        }
        break;
      default:
        filtered = allProducts;
    }
    
    setFilteredProducts(filtered);
    setCurrentIndex(0);
  }, [config, allProducts]);

  // Initial fetch and WebSocket
  useEffect(() => {
    fetchProducts();
    connectWebSocket();
    
    // Escuchar cambios de configuración del carrusel
    const handleConfigUpdate = (data: CarruselConfig) => {
      console.log('📺 Config carrusel actualizada via WS:', data);
      setConfig({
        mode: data.mode || 'all',
        selectedCategories: data.selectedCategories || []
      });
    };
    
    // Escuchar cambios de productos
    const handleProductoActualizado = () => {
      fetchProducts();
    };
    
    on('carrusel_config_actualizada', handleConfigUpdate);
    on('producto_creado', handleProductoActualizado);
    on('producto_actualizado', handleProductoActualizado);
    on('producto_eliminado', handleProductoActualizado);
    
    return () => {
      off('carrusel_config_actualizada', handleConfigUpdate);
      off('producto_creado', handleProductoActualizado);
      off('producto_actualizado', handleProductoActualizado);
      off('producto_eliminado', handleProductoActualizado);
      disconnectWebSocket();
      
      // Limpiar blob URLs de memoria
      clearBlobCache();
    };
  }, []); // Sin dependencias, o con las dependencias correctas

  // Auto-advance carousel
  useEffect(() => {
    if (filteredProducts.length <= 1) return;
    
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % filteredProducts.length);
    }, 5000);
    
    return () => clearInterval(interval);
  }, [filteredProducts.length]);

  // Handlers
  const handleModeChange = (mode: CarruselMode) => {
    const newConfig = {
      ...config,
      mode,
      selectedCategories: mode === 'categories' ? config.selectedCategories : []
    };
    setConfig(newConfig);
    saveConfigToBackend(newConfig);
  };

  const handleCategoryToggle = (category: string) => {
    const isSelected = config.selectedCategories.includes(category);
    const newCategories = isSelected
      ? config.selectedCategories.filter(c => c !== category)
      : [...config.selectedCategories, category];
    
    const newConfig = {
      ...config,
      selectedCategories: newCategories
    };
    setConfig(newConfig);
    saveConfigToBackend(newConfig);
  };

  const handleVolverAdmin = () => {
    navigate("/admin");
  };

  if (loading) {
    return (
      <div className="carrusel-container">
        <div className="loading">
          <div className="spinner"></div>
          <p>Cargando productos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="carrusel-container">
        <p className="no-productos">{error}</p>
      </div>
    );
  }

  return (
    <>
      <div className="carrusel-container">
        {/* Header */}
        <header className="carrusel-header">
          <div className="header-content">
            <div className="header-titulo">
              <h1 className="local-nombre">NUESTROS PRODUCTOS</h1>
              <p className="local-subtitulo">Deliciosas opciones para vos</p>
            </div>
            {/* Admin Controls dentro del header */}
            {isAdmin && (
              <div className="header-admin-buttons">
                <button className="btn-volver-admin" onClick={handleVolverAdmin}>
                  ← Volver al Panel
                </button>
                <button 
                  className="toggle-panel-btn"
                  onClick={() => setShowPanel(!showPanel)}
                >
                  {showPanel ? '✕ Ocultar' : 'Configurar'}
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Admin Panel (fuera del header pero visible cuando está activo) */}
        {isAdmin && showPanel && (
          <div className="admin-controls">
            <div className="admin-panel-carrusel">
                <button 
                  className="btn-cerrar-panel"
                  onClick={() => setShowPanel(false)}
                >
                  ✕
                </button>
                <h3>Modo del Carrusel</h3>
                {savingConfig && (
                  <p className="saving-indicator">Guardando...</p>
                )}
                <div className="mode-selector">
                  <button
                    className={`mode-btn ${config.mode === 'all' ? 'active' : ''}`}
                    onClick={() => handleModeChange('all')}
                  >
                    <span className="mode-btn-icon"></span>
                    <span className="mode-btn-text">Todos los productos</span>
                    <span className="mode-btn-check">✓</span>
                  </button>
                  <button
                    className={`mode-btn ${config.mode === 'featured' ? 'active' : ''}`}
                    onClick={() => handleModeChange('featured')}
                  >
                    <span className="mode-btn-icon"></span>
                    <span className="mode-btn-text">Solo destacados</span>
                    <span className="mode-btn-check">✓</span>
                  </button>
                  <button
                    className={`mode-btn ${config.mode === 'categories' ? 'active' : ''}`}
                    onClick={() => handleModeChange('categories')}
                  >
                    <span className="mode-btn-icon"></span>
                    <span className="mode-btn-text">Por categorías</span>
                    <span className="mode-btn-check">✓</span>
                  </button>
                </div>
                {config.mode === 'categories' && (
                  <div className="category-selector">
                    <h4>Selecciona las categorías:</h4>
                    <div className="category-chips">
                      {availableCategories.map(cat => (
                        <button
                          key={cat}
                          className={`category-chip ${
                            config.selectedCategories.includes(cat) ? 'selected' : ''
                          }`}
                          onClick={() => handleCategoryToggle(cat)}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          </div>
        )}

        {/* No products message */}
        {filteredProducts.length === 0 ? (
          <div className="no-products-message">
            <h2>Sin productos</h2>
            <p>
              {config.mode === 'featured' 
                ? 'No hay productos destacados disponibles.'
                : config.mode === 'categories' && config.selectedCategories.length === 0
                  ? 'Selecciona al menos una categoría.'
                  : 'No hay productos que coincidan con los filtros.'}
            </p>
          </div>
        ) : (
          <div className="carrusel-wrapper">
            <div className="carrusel-content">
              {filteredProducts.map((producto, index) => {
                const isVisible = index === currentIndex;
                
                // ✅ NUEVO: Obtener URL precargada del mapa
                const preloadedUrl = preloadedImages.get(producto.imagen_url);
                
                return (
                  <div 
                    key={producto.id} 
                    className={`carrusel-slide ${isVisible ? 'active' : ''}`}
                  >
                    <div className="producto-card">
                      <div className="producto-info">
                        <span className="producto-categoria">{producto.categoria}</span>
                        <h2 className="producto-nombre">{producto.nombre}</h2>
                        <p className="producto-descripcion">{producto.descripcion}</p>
                        <p className="producto-precio">${producto.precio.toLocaleString('es-CL')}</p>
                        {producto.destacado && (
                          <span className="carrusel-destacado">Destacado</span>
                        )}
                      </div>
                      <div className="producto-imagen-container">
                        <OptimizedImage
                          src={producto.imagen_url}
                          alt={producto.nombre}
                          className="producto-imagen"
                          priority={isVisible}
                          preloadedUrl={preloadedUrl}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {filteredProducts.length > 1 && (
          <div className="carrusel-dots">
            {filteredProducts.map((_, index) => (
              <button
                key={index}
                className={`carrusel-dot ${index === currentIndex ? 'active' : ''}`}
                onClick={() => setCurrentIndex(index)}
                aria-label={`Ir al producto ${index + 1}`}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}

export default Carrusel;
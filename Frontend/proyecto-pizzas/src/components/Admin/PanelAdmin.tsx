import { useEffect, useState, useContext, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { DemoContext } from '../../App';
import { preloadAndCacheImage, clearBlobCache, clearPersistentCache } from '../../services/ImageCache';
import './PanelAdmin.css';

// Componente optimizado para imágenes del admin con caché persistente
const AdminImage = memo(({ src, alt }: { src: string | null; alt: string }) => {
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

AdminImage.displayName = 'AdminImage';

interface Producto {
  id: number;
  nombre: string;
  descripcion: string;
  precio: number;
  imagen_url: string;
  categorias: { id: number; nombre: string } | null;
  disponible: boolean;
  destacado: boolean;
}

interface ProductosPorCategoria {
  [categoriaId: string]: {
    nombre: string;
    orden: number;
    productos: Producto[];
  };
}

interface Categoria {
  id: number;
  nombre: string;
  descripcion: string;
  orden: number;
}


const PanelAdmin = () => {
  const [productos, setProductos] = useState<Producto[]>([]);
  const [productosPorCategoria, setProductosPorCategoria] = useState<ProductosPorCategoria>({});
  const [cargando, setCargando] = useState(true);
  const [nombreLocal, setNombreLocal] = useState<string>('');
  const [modalEliminar, setModalEliminar] = useState<{ visible: boolean; productoId: number | null; nombreProducto: string }>({ visible: false, productoId: null, nombreProducto: '' });

  // Estado para controlar qué categorías están abiertas (debe ir aquí, no dentro del render)
  const [categoriasAbiertas, setCategoriasAbiertas] = useState<{ [categoriaId: string]: boolean }>({});

  // Estados para modal de categorías
  const [modalCategorias, setModalCategorias] = useState(false);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [cargandoCategorias, setCargandoCategorias] = useState(false);
  const [categoriaEditando, setCategoriaEditando] = useState<number | null>(null);
  const [nombreCategoriaEdit, setNombreCategoriaEdit] = useState('');
  const [errorCategoria, setErrorCategoria] = useState('');
  const [guardandoCategoria, setGuardandoCategoria] = useState(false);
  const [modalEliminarCategoria, setModalEliminarCategoria] = useState<{ visible: boolean; categoriaId: number | null; nombreCategoria: string }>({ visible: false, categoriaId: null, nombreCategoria: '' });
  const [eliminandoCategoria, setEliminandoCategoria] = useState(false);

  // Estados para modal de crear nueva categoría
  const [mostrarModalNuevaCategoria, setMostrarModalNuevaCategoria] = useState(false);
  const [nuevaCategoria, setNuevaCategoria] = useState({ nombre: '', descripcion: '' });
  const [creandoCategoria, setCreandoCategoria] = useState(false);
  const [errorNuevaCategoria, setErrorNuevaCategoria] = useState('');

  // Estados para drag & drop de categorías
  const [draggedCategoria, setDraggedCategoria] = useState<number | null>(null);

  const navigate = useNavigate();
  const { isDemoMode, showDemoAlert } = useContext(DemoContext);

  useEffect(() => {
    cargarDatosIniciales();
    cargarNombreLocal();
  }, []);

  const cargarDatosIniciales = async () => {
    // Cargar categorías primero para tener el orden
    const token = localStorage.getItem('adminToken');
    try {
      const resCategorias = await fetch(`${import.meta.env.VITE_API_URL}/admin/categorias`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      
      let categoriasData: Categoria[] = [];
      if (resCategorias.ok) {
        categoriasData = await resCategorias.json();
        setCategorias(categoriasData);
      }
      
      // Ahora cargar productos con el orden de categorías
      await cargarProductosConOrden(categoriasData);
    } catch (error) {
      console.error('Error cargando datos:', error);
      setCargando(false);
    }
  };

  const cargarNombreLocal = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/locales`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          setNombreLocal(data[0].nombre);
        }
      }
    } catch (error) {
      console.error('Error cargando nombre del local:', error);
    }
  };

  const cargarProductosConOrden = async (categoriasData: Categoria[]) => {
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/productos`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const productosFormateados = (data || []).map((producto: any) => {
          // Construir URL completa si es relativa
          let imagen_url = producto.imagen_url;
          if (imagen_url && !imagen_url.startsWith('http')) {
            imagen_url = `${import.meta.env.VITE_API_URL}${imagen_url}`;
          }
          
          return {
            ...producto,
            imagen_url,
            categorias: Array.isArray(producto.categorias)
              ? producto.categorias[0] || null
              : producto.categorias || null,
          };
        });

        setProductos(productosFormateados);

        // Agrupar productos por categoría con orden
        const agrupados: ProductosPorCategoria = {};
        
        productosFormateados.forEach((producto: Producto) => {
          const categoriaId = producto.categorias?.id?.toString() || 'sin-categoria';
          const categoriaNombre = producto.categorias?.nombre || 'Sin categoría';
          
          // Buscar el orden de la categoría
          const categoriaInfo = categoriasData.find(c => c.id.toString() === categoriaId);
          const orden = categoriaInfo?.orden ?? 999;
          
          if (!agrupados[categoriaId]) {
            agrupados[categoriaId] = {
              nombre: categoriaNombre,
              orden: orden,
              productos: []
            };
          }
          agrupados[categoriaId].productos.push(producto);
        });

        setProductosPorCategoria(agrupados);
      } else {
        console.error('Error al cargar productos');
      }
    } catch (error) {
      console.error('Error cargando productos:', error);
    } finally {
      setCargando(false);
    }
  };

  const cargarProductos = async () => {
    // Usar categorías ya cargadas
    await cargarProductosConOrden(categorias);
  };

  const abrirModalEliminar = (id: number, nombre: string) => {
    if (isDemoMode) {
      showDemoAlert();
      return;
    }
    setModalEliminar({ visible: true, productoId: id, nombreProducto: nombre });
  };

  const cerrarModalEliminar = () => {
    setModalEliminar({ visible: false, productoId: null, nombreProducto: '' });
  };

  const confirmarEliminar = async () => {
    if (isDemoMode) {
      showDemoAlert();
      return;
    }
    if (!modalEliminar.productoId) return;

    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/productos/${modalEliminar.productoId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        // Actualizar lista de productos
        const nuevosProductos = productos.filter(p => p.id !== modalEliminar.productoId);
        setProductos(nuevosProductos);

        // Reagrupar productos por categoría con orden
        const agrupados: ProductosPorCategoria = {};
        nuevosProductos.forEach((producto: Producto) => {
          const categoriaId = producto.categorias?.id?.toString() || 'sin-categoria';
          const categoriaNombre = producto.categorias?.nombre || 'Sin categoría';
          
          // Buscar el orden de la categoría
          const categoriaInfo = categorias.find(c => c.id.toString() === categoriaId);
          const orden = categoriaInfo?.orden ?? 999;
          
          if (!agrupados[categoriaId]) {
            agrupados[categoriaId] = {
              nombre: categoriaNombre,
              orden: orden,
              productos: []
            };
          }
          agrupados[categoriaId].productos.push(producto);
        });
        setProductosPorCategoria(agrupados);

        cerrarModalEliminar();
      } else {
        alert('Error al eliminar producto');
      }
    } catch (error) {
      console.error('Error:', error);
      alert('Error al eliminar producto');
    }
  };

  const formatearPrecioVisualizacion = (precio: number): string => {
    // Convertir el número a string with 2 decimales
    const precioStr = precio.toFixed(2);
    const [entero, decimal] = precioStr.split('.');
    
    // Formatear la parte entera con puntos de miles
    const enteroFormateado = entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    
    // Retornar con coma como separador decimal
    return `${enteroFormateado},${decimal}`;
  };

  // ========================================
  // FUNCIONES PARA GESTION DE CATEGORÍAS
  // ========================================

  const abrirModalCategorias = async () => {
    setModalCategorias(true);
    await cargarCategorias();
  };

  const cerrarModalCategorias = () => {
    setModalCategorias(false);
    setCategoriaEditando(null);
    setNombreCategoriaEdit('');
    setErrorCategoria('');
  };

  const cargarCategorias = async () => {
    setCargandoCategorias(true);
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/categorias`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCategorias(data);
      }
    } catch (error) {
      console.error('Error cargando categorías:', error);
    } finally {
      setCargandoCategorias(false);
    }
  };

  const iniciarEdicionCategoria = (categoria: Categoria) => {
    if (isDemoMode) {
      showDemoAlert();
      return;
    }
    setCategoriaEditando(categoria.id);
    setNombreCategoriaEdit(categoria.nombre);
    setErrorCategoria('');
  };

  const cancelarEdicionCategoria = () => {
    setCategoriaEditando(null);
    setNombreCategoriaEdit('');
    setErrorCategoria('');
  };

  const guardarEdicionCategoria = async (categoriaId: number) => {
    if (isDemoMode) {
      showDemoAlert();
      return;
    }
    if (!nombreCategoriaEdit.trim()) {
      setErrorCategoria('El nombre es obligatorio');
      return;
    }

    setGuardandoCategoria(true);
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/categorias/${categoriaId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nombre: nombreCategoriaEdit.trim(),
          descripcion: ''
        }),
      });

      if (response.ok) {
        await cargarCategorias();
        await cargarProductos(); // Recargar productos para actualizar nombres de categorías
        setCategoriaEditando(null);
        setNombreCategoriaEdit('');
        setErrorCategoria('');
      } else {
        const errorData = await response.json();
        setErrorCategoria(errorData.detail || 'Error al actualizar');
      }
    } catch (error) {
      setErrorCategoria('Error de conexión');
    } finally {
      setGuardandoCategoria(false);
    }
  };

  // Funciones para drag & drop
  const handleDragStart = (e: React.DragEvent, categoriaId: number) => {
    if (isDemoMode) {
      e.preventDefault();
      return;
    }
    setDraggedCategoria(categoriaId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = async (e: React.DragEvent, targetCategoriaId: number) => {
    e.preventDefault();
    
    if (isDemoMode) {
      showDemoAlert();
      setDraggedCategoria(null);
      return;
    }
    
    if (draggedCategoria === null || draggedCategoria === targetCategoriaId) {
      setDraggedCategoria(null);
      return;
    }

    // Reordenar localmente primero
    const draggedIndex = categorias.findIndex(c => c.id === draggedCategoria);
    const targetIndex = categorias.findIndex(c => c.id === targetCategoriaId);
    
    if (draggedIndex === -1 || targetIndex === -1) {
      setDraggedCategoria(null);
      return;
    }

    const newCategorias = [...categorias];
    const [removed] = newCategorias.splice(draggedIndex, 1);
    newCategorias.splice(targetIndex, 0, removed);
    
    setCategorias(newCategorias);
    setDraggedCategoria(null);

    // Guardar el nuevo orden en el backend
    try {
      const token = localStorage.getItem('adminToken');
      const orden_ids = newCategorias.map(c => c.id);
      
      await fetch(`${import.meta.env.VITE_API_URL}/admin/categorias/reordenar`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ orden_ids }),
      });

      // Recargar productos para reflejar el nuevo orden
      await cargarProductos();
    } catch (error) {
      console.error('Error al reordenar:', error);
      // Recargar para restaurar el orden correcto
      await cargarCategorias();
    }
  };

  const handleDragEnd = () => {
    setDraggedCategoria(null);
  };

  const handleCrearCategoria = async () => {
    if (isDemoMode) {
      showDemoAlert();
      return;
    }
    if (!nuevaCategoria.nombre.trim()) {
      setErrorNuevaCategoria('El nombre es obligatorio');
      return;
    }

    setCreandoCategoria(true);
    setErrorNuevaCategoria('');

    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/categorias`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          nombre: nuevaCategoria.nombre.trim(),
          descripcion: nuevaCategoria.descripcion.trim(),
        }),
      });

      if (response.ok) {
        await cargarCategorias();
        await cargarProductos();
        setMostrarModalNuevaCategoria(false);
        setNuevaCategoria({ nombre: '', descripcion: '' });
      } else {
        const errorData = await response.json();
        setErrorNuevaCategoria(errorData.detail || 'Error al crear categoría');
      }
    } catch (error) {
      setErrorNuevaCategoria('Error de conexión');
    } finally {
      setCreandoCategoria(false);
    }
  };

  const abrirModalEliminarCategoria = (categoriaId: number, nombreCategoria: string) => {
    if (isDemoMode) {
      showDemoAlert();
      return;
    }
    setModalEliminarCategoria({ visible: true, categoriaId, nombreCategoria });
  };

  const cerrarModalEliminarCategoria = () => {
    setModalEliminarCategoria({ visible: false, categoriaId: null, nombreCategoria: '' });
  };

  const confirmarEliminarCategoria = async () => {
    if (isDemoMode) {
      showDemoAlert();
      return;
    }
    if (!modalEliminarCategoria.categoriaId) return;

    setEliminandoCategoria(true);
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/categorias/${modalEliminarCategoria.categoriaId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        await cargarCategorias();
        await cargarProductos();
        cerrarModalEliminarCategoria();
      } else {
        const errorData = await response.json();
        alert(errorData.detail || 'Error al eliminar categoría');
      }
    } catch (error) {
      alert('Error de conexión');
    } finally {
      setEliminandoCategoria(false);
    }
  };

  // UNIFICAR: Solo una función de logout que hace todo
  const handleLogout = async () => {
    // Limpiar caché de imágenes
    await clearPersistentCache();
    
    // Limpiar localStorage
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminLocalId');
    localStorage.removeItem('adminNombre');
    localStorage.removeItem('adminRol');
    
    navigate('/login');
  };

  // Cleanup al desmontar
  useEffect(() => {
    return () => {
      // Limpiar solo blob URLs de memoria, mantener cache persistente
      clearBlobCache();
    };
  }, []);

  if (cargando) {
    return (
      <div className="loading-container">
        <p className="loading-text">Cargando productos...</p>
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    );
  }




  const toggleCategoria = (categoriaId: string) => {
    setCategoriasAbiertas((prev) => ({
      ...prev,
      [categoriaId]: !prev[categoriaId],
    }));
  };

  return (
    <div className="panel-admin">
      <header className="panel-header">
        <div className="header-izquierda">
          <button className="btn-logout" onClick={handleLogout}>
            Cerrar Sesión
          </button>
          <button className="btn-ir-menu" onClick={() => navigate('/')}> 
            Ir al Menú
          </button>
          <button className="btn-ir-carrusel" onClick={() => navigate('/carrusel')}>
            Ir al Carrusel
          </button>
        </div>
        <div className="header-titulos">
          <h1>Panel de Administracion</h1>
          {nombreLocal && <h3 className="nombre-local">{nombreLocal}</h3>}
        </div>
        <div className="header-acciones">
          <button className="btn-agregar" onClick={() => {
            if (isDemoMode) {
              showDemoAlert();
              return;
            }
            navigate('/admin/agregar');
          }}>
            + Agregar Producto
          </button>
          <button className="btn-categorias" onClick={abrirModalCategorias}>
            Categorias
          </button>
        </div>
      </header>

      {Object.keys(productosPorCategoria).length === 0 ? (
        <div className="empty-state">
          <p>No hay productos registrados</p>
          <button className="btn-agregar" onClick={() => {
            if (isDemoMode) {
              showDemoAlert();
              return;
            }
            navigate('/admin/agregar');
          }}>
            + Agregar tu primer producto
          </button>
        </div>
      ) : (
        Object.entries(productosPorCategoria)
          .sort(([, a], [, b]) => a.orden - b.orden)
          .map(([categoriaId, { nombre, productos: productosCategoria }]) => (
          <div key={categoriaId} className="categoria-seccion">
            <h2
              className="categoria-titulo-admin categoria-titulo-desplegable"
              onClick={() => toggleCategoria(categoriaId)}
              style={{ cursor: 'pointer', userSelect: 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
            >
              <span>{nombre}</span>
              <span style={{ fontSize: 22, marginLeft: 10, transition: 'transform 0.3s', transform: categoriasAbiertas[categoriaId] ? 'rotate(90deg)' : 'rotate(0deg)' }}>
                ▶
              </span>
            </h2>
            <div
              className={`productos-lista productos-lista-desplegable${categoriasAbiertas[categoriaId] ? ' abierta' : ''}`}
              style={{
                maxHeight: categoriasAbiertas[categoriaId] ? `${productosCategoria.length * 220 + 60}px` : '0px',
                overflow: 'hidden',
                transition: 'max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                marginBottom: categoriasAbiertas[categoriaId] ? 20 : 0,
                paddingTop: categoriasAbiertas[categoriaId] ? 10 : 0,
                paddingBottom: categoriasAbiertas[categoriaId] ? 10 : 0,
              }}
            >
              {productosCategoria.map((producto) => (
                <div key={producto.id} className="producto-item">
                  <div className="producto-imagen">
                    <AdminImage src={producto.imagen_url} alt={producto.nombre} />
                  </div>

                  <div className="producto-info">
                    <h3>{producto.nombre}</h3>
                    <p className="producto-descripcion">{producto.descripcion}</p>
                    <div className="producto-meta">
                      <span className="producto-categoria">
                        {producto.categorias?.nombre || 'Sin categoría'}
                      </span>
                      <span className={`producto-estado ${producto.disponible ? 'disponible' : 'sin-stock'}`}>
                        {producto.disponible ? 'Disponible' : 'Sin Stock'}
                      </span>
                      {producto.destacado && (
                        <span className="producto-destacado">
                          Destacado
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="producto-precio">
                    ${formatearPrecioVisualizacion(producto.precio)}
                  </div>

                  <div className="producto-acciones">
                    <button
                      className="btn-editar"
                      onClick={() => {
                        if (isDemoMode) {
                          showDemoAlert();
                          return;
                        }
                        navigate(`/admin/editar/${producto.id}`);
                      }}
                    >
                      Editar
                    </button>
                    <button
                      className="btn-eliminar"
                      onClick={() => abrirModalEliminar(producto.id, producto.nombre)}
                    >
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}

      {/* Modal de confirmacion */}
      {modalEliminar.visible && (
        <div className="modal-overlay" onClick={cerrarModalEliminar}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Confirmar eliminación</h2>
            </div>
            <div className="modal-body">
              <p>¿Estás seguro de que deseas eliminar el producto?</p>
              <p className="producto-a-eliminar">"{modalEliminar.nombreProducto}"</p>
              <p className="advertencia">Esta acción no se puede deshacer.</p>
            </div>
            <div className="modal-footer">
              <button className="btn-modal-cancelar" onClick={cerrarModalEliminar}>
                Cancelar
              </button>
              <button className="btn-modal-eliminar" onClick={confirmarEliminar}>
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de gestión de categorías */}
      {modalCategorias && (
        <div className="modal-overlay">
          <div className="modal-categorias" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Gestión de Categorías</h2>
              <button className="btn-cerrar-modal" onClick={cerrarModalCategorias}>×</button>
            </div>
            <div className="modal-body-categorias">
              <button
                className="btn-agregar-categoria"
                onClick={() => {
                  if (isDemoMode) {
                    showDemoAlert();
                    return;
                  }
                  setMostrarModalNuevaCategoria(true);
                }}
              >
                + Agregar Categoría
              </button>
              {cargandoCategorias ? (
                <div className="cargando-categorias">
                  <p>Cargando categorías...</p>
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              ) : categorias.length === 0 ? (
                <p className="sin-categorias">No hay categorías creadas</p>
              ) : (
                <ul className="lista-categorias">
                  {categorias.map((categoria) => (
                    <li 
                      key={categoria.id} 
                      className={`categoria-item ${draggedCategoria === categoria.id ? 'dragging' : ''}`}
                      draggable={categoriaEditando !== categoria.id && !guardandoCategoria && !isDemoMode}
                      onDragStart={(e) => handleDragStart(e, categoria.id)}
                      onDragOver={handleDragOver}
                      onDrop={(e) => handleDrop(e, categoria.id)}
                      onDragEnd={handleDragEnd}
                    >
                      {categoriaEditando === categoria.id ? (
                      guardandoCategoria ? (
                        <div className="categoria-guardando">
                          <span>Guardando...</span>
                          <div className="loading-dots">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                        </div>
                      ) : (
                        <div className="categoria-editando">
                          <input
                            type="text"
                            value={nombreCategoriaEdit}
                            onChange={(e) => setNombreCategoriaEdit(e.target.value)}
                            className="input-categoria-edit"
                            autoFocus
                          />
                          <button
                            className="btn-confirmar-edit"
                            onClick={() => guardarEdicionCategoria(categoria.id)}
                            title="Confirmar"
                          >
                            ✓
                          </button>
                          <button
                            className="btn-cancelar-edit"
                            onClick={cancelarEdicionCategoria}
                            title="Cancelar"
                          >
                            ✕
                          </button>
                        </div>
                      )
                    ) : (
                        <div className="categoria-vista">
                          <span className="drag-handle" title="Arrastrar para reordenar">⠿</span>
                          <span className="categoria-nombre">{categoria.nombre}</span>
                          <div className="categoria-acciones">
                            <button
                              className="btn-editar-cat"
                              onClick={() => iniciarEdicionCategoria(categoria)}
                              title="Editar"
                            >
                              ✏️
                            </button>
                            <button
                              className="btn-eliminar-cat"
                              onClick={() => abrirModalEliminarCategoria(categoria.id, categoria.nombre)}
                              title="Eliminar"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {errorCategoria && (
                <p className="error-categoria">{errorCategoria}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal para crear nueva categoría */}
      {mostrarModalNuevaCategoria && (
        <div className="modal-overlay" onClick={() => !creandoCategoria && setMostrarModalNuevaCategoria(false)}>
          <div className="modal-nueva-categoria" onClick={(e) => e.stopPropagation()}>
            <h3>Nueva Categoría</h3>
            
            <div className="modal-form-group">
              <label>Nombre *</label>
              <input
                type="text"
                value={nuevaCategoria.nombre}
                onChange={(e) => setNuevaCategoria(prev => ({ ...prev, nombre: e.target.value }))}
                maxLength={100}
              />
            </div>

            <div className="modal-form-group">
              <label>Descripción</label>
              <input
                type="text"
                value={nuevaCategoria.descripcion}
                onChange={(e) => setNuevaCategoria(prev => ({ ...prev, descripcion: e.target.value }))}
                maxLength={200}
              />
            </div>

            {errorNuevaCategoria && (
              <div className="modal-error">{errorNuevaCategoria}</div>
            )}

            <div className="modal-actions">
              <button
                type="button"
                className="btn-modal-cancelar"
                onClick={() => {
                  setMostrarModalNuevaCategoria(false);
                  setNuevaCategoria({ nombre: '', descripcion: '' });
                  setErrorNuevaCategoria('');
                }}
                disabled={creandoCategoria}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-modal-crear"
                onClick={handleCrearCategoria}
                disabled={creandoCategoria}
              >
                {creandoCategoria ? 'Creando...' : 'Crear'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmación para eliminar categoría */}
      {modalEliminarCategoria.visible && (
        <div className="modal-overlay" onClick={!eliminandoCategoria ? cerrarModalEliminarCategoria : undefined}>
          <div className="modal-content modal-eliminar-categoria" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header modal-header-warning">
              <h2>Eliminar Categoría</h2>
            </div>
            <div className="modal-body">
              {eliminandoCategoria ? (
                <div className="eliminando-categoria">
                  <p>Eliminando categoría y productos...</p>
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              ) : (
                <>
                  <p>¿Estás seguro de eliminar la categoría?</p>
                  <p className="producto-a-eliminar">"{modalEliminarCategoria.nombreCategoria}"</p>
                  <p className="advertencia-grave">
                    <strong>Atención:</strong> Esta acción eliminará también <strong>todos los productos</strong> que pertenecen a esta categoría.
                  </p>
                </>
              )}
            </div>
            {!eliminandoCategoria && (
              <div className="modal-footer">
                <button className="btn-modal-cancelar" onClick={cerrarModalEliminarCategoria}>
                  Cancelar
                </button>
                <button className="btn-modal-eliminar" onClick={confirmarEliminarCategoria}>
                  Eliminar Categoría
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PanelAdmin;

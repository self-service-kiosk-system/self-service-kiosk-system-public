
import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import './AgregarProducto.css';

interface Categoria {
  id: number;
  nombre: string;
}

interface Local {
  id: number;
  nombre: string;
}

interface Producto {
  id: number;
  local_id: number;
  categoria_id: number;
  nombre: string;
  descripcion: string;
  precio: number;
  disponible: boolean;
  destacado: boolean;
  imagen_url: string | null;
}

const EditarProducto = () => {
  const { id } = useParams<{ id: string }>();
  const [localUsuario, setLocalUsuario] = useState<Local | null>(null);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [cargando, setCargando] = useState(false);
  const [cargandoDatos, setCargandoDatos] = useState(true);
  const [error, setError] = useState('');
  const [erroresValidacion, setErroresValidacion] = useState<{[key: string]: string}>({});
  const navigate = useNavigate();

  // Estados para modal de nueva categoría
  const [mostrarModalCategoria, setMostrarModalCategoria] = useState(false);
  const [nuevaCategoria, setNuevaCategoria] = useState({ nombre: '', descripcion: '' });
  const [creandoCategoria, setCreandoCategoria] = useState(false);
  const [errorCategoria, setErrorCategoria] = useState('');

  const [formData, setFormData] = useState({
    local_id: '',
    categoria_id: '',
    nombre: '',
    descripcion: '',
    precio: '',
    disponible: true,
    destacado: false,
  });

  const [imagen, setImagen] = useState<File | null>(null);
  const [previsualizacion, setPrevisualizacion] = useState<string>('');
  const [productoOriginal, setProductoOriginal] = useState<Producto | null>(null);

  // Cargar local del usuario primero
  useEffect(() => {
    cargarLocalUsuario();
  }, []);

  // Cargar producto cuando tengamos el ID y el local del usuario
  useEffect(() => {
    if (id && localUsuario) {
      cargarProducto();
    }
  }, [id, localUsuario]);

  // Cargar categorías cuando cambie el local_id Y tengamos el producto original
  useEffect(() => {
    if (formData.local_id && productoOriginal) {
      cargarCategorias(parseInt(formData.local_id));
    }
  }, [formData.local_id, productoOriginal]);

  const cargarProducto = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/productos`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Error al cargar productos');
      }

      const productos = await response.json();
      const producto = productos.find((p: Producto) => p.id === parseInt(id!));
      
      if (!producto) {
        setError('Producto no encontrado');
        setCargandoDatos(false);
        return;
      }

      console.log('Producto cargado:', producto);
      
      // Guardar referencia del producto original
      setProductoOriginal(producto);

      // Cargar datos del producto en el formulario
      setFormData({
        local_id: producto.local_id.toString(),
        categoria_id: producto.categoria_id.toString(),
        nombre: producto.nombre,
        descripcion: producto.descripcion || '',
        precio: producto.precio.toString(),
        disponible: producto.disponible,
        destacado: producto.destacado,
      });
      
      // Manejar la imagen actual
      if (producto.imagen_url) {
        setPrevisualizacion(producto.imagen_url);
      }
      
      setCargandoDatos(false);
    } catch (err) {
      console.error('Error cargando producto:', err);
      setError('Error al cargar el producto');
      setCargandoDatos(false);
    }
  };

  const cargarLocalUsuario = async () => {
    try {
      const token = localStorage.getItem('adminToken');
      const localId = localStorage.getItem('adminLocalId');
      
      if (!localId) {
        setError('No se encontró información del local del usuario');
        setCargandoDatos(false);
        return;
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/locales`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        // Buscar el local del usuario
        const local = data.find((l: Local) => l.id === parseInt(localId));
        
        if (local) {
          setLocalUsuario(local);
          // Establecer automáticamente el local_id en el formulario
          setFormData(prev => ({ ...prev, local_id: local.id.toString() }));
        } else {
          setError('No se encontró el local asociado al usuario');
          setCargandoDatos(false);
        }
      } else {
        setError('Error al cargar información del local');
        setCargandoDatos(false);
      }
    } catch (err) {
      setError('Error de conexión al cargar local');
      setCargandoDatos(false);
    }
  };

  const cargarCategorias = async (localId: number) => {
    try {
      const token = localStorage.getItem('adminToken');
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/admin/categorias?local_id=${localId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setCategorias(data);
      } else {
        setError('Error al cargar categorías');
      }
    } catch (err) {
      console.error('Error cargando categorías:', err);
      setError('Error de conexión al cargar categorías');
    }
  };

  const handleCrearCategoria = async () => {
    if (!nuevaCategoria.nombre.trim()) {
      setErrorCategoria('El nombre es obligatorio');
      return;
    }

    setCreandoCategoria(true);
    setErrorCategoria('');

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
        const data = await response.json();
        // Recargar categorías y seleccionar la nueva
        await cargarCategorias(parseInt(formData.local_id));
        setFormData(prev => ({ ...prev, categoria_id: data.id.toString() }));
        setMostrarModalCategoria(false);
        setNuevaCategoria({ nombre: '', descripcion: '' });
      } else {
        const errorData = await response.json();
        setErrorCategoria(errorData.detail || 'Error al crear categoría');
      }
    } catch (err) {
      setErrorCategoria('Error de conexión');
    } finally {
      setCreandoCategoria(false);
    }
  };

  const validarFormulario = (): boolean => {
    const errores: {[key: string]: string} = {};

    // Validar nombre
    if (!formData.nombre.trim()) {
      errores.nombre = 'El nombre es obligatorio';
    } else if (formData.nombre.length > 100) {
      errores.nombre = 'El nombre no puede superar los 100 caracteres';
    }

    // Validar descripción
    if (formData.descripcion.length > 500) {
      errores.descripcion = 'La descripción no puede superar los 500 caracteres';
    }

    // Validar precio
    if (!formData.precio.trim()) {
      errores.precio = 'El precio es obligatorio';
    } else {
      const precioNumerico = parsePrecio(formData.precio);
      if (isNaN(precioNumerico) || precioNumerico < 0) {
        errores.precio = 'El precio debe ser un número válido mayor o igual a 0';
      }
    }

    // Validar local y categoría
    if (!formData.local_id) {
      errores.local_id = 'Debe seleccionar un local';
    }
    if (!formData.categoria_id) {
      errores.categoria_id = 'Debe seleccionar una categoría';
    }

    setErroresValidacion(errores);
    return Object.keys(errores).length === 0;
  };

  const parsePrecio = (precioStr: string): number => {
    // Eliminar puntos de miles y reemplazar coma por punto decimal
    const precioLimpio = precioStr.replace(/\./g, '').replace(',', '.');
    return parseFloat(precioLimpio);
  };

  const formatearPrecio = (valor: string): string => {
    // Eliminar todo excepto números y coma
    let limpio = valor.replace(/[^\d,]/g, '');
    
    // Permitir solo una coma
    const partes = limpio.split(',');
    if (partes.length > 2) {
      limpio = partes[0] + ',' + partes.slice(1).join('');
    }
    
    // Limitar decimales a 2 dígitos
    if (partes.length === 2 && partes[1].length > 2) {
      limpio = partes[0] + ',' + partes[1].substring(0, 2);
    }
    
    // Formatear con puntos de miles
    const [entero, decimal] = limpio.split(',');
    const enteroFormateado = entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    
    return decimal !== undefined ? `${enteroFormateado},${decimal}` : enteroFormateado;
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target;
    
    // Limpiar error específico del campo
    if (erroresValidacion[name]) {
      setErroresValidacion(prev => {
        const nuevos = {...prev};
        delete nuevos[name];
        return nuevos;
      });
    }
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({ ...prev, [name]: checked }));
    } else if (name === 'precio') {
      // Formatear precio mientras se escribe
      const precioFormateado = formatearPrecio(value);
      setFormData(prev => ({ ...prev, [name]: precioFormateado }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleImagenChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImagen(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPrevisualizacion(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setErroresValidacion({});

    // Validar formulario
    if (!validarFormulario()) {
      setError('Por favor, corrija los errores en el formulario');
      return;
    }

    setCargando(true);

    try {
      const token = localStorage.getItem('adminToken');
      const formDataToSend = new FormData();

      // Agregar campos al FormData
      formDataToSend.append('categoria_id', formData.categoria_id);
      formDataToSend.append('nombre', formData.nombre);
      formDataToSend.append('descripcion', formData.descripcion);
      
      // Convertir el precio formateado a número
      const precioNumerico = parsePrecio(formData.precio);
      formDataToSend.append('precio', precioNumerico.toString());
      
      formDataToSend.append('disponible', formData.disponible.toString());
      formDataToSend.append('destacado', formData.destacado.toString());

      // Solo agregar imagen si se seleccionó una nueva
      if (imagen) {
        formDataToSend.append('imagen', imagen);
      }

      const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/productos/${id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formDataToSend,
      });

      if (response.ok) {
        navigate('/admin');
      } else {
        const data = await response.json();
        setError(data.detail || 'Error al actualizar producto');
      }
    } catch (err) {
      console.error('Error actualizando producto:', err);
      setError('Error de conexión con el servidor');
    } finally {
      setCargando(false);
    }
  };

  if (cargandoDatos) {
    return (
      <div className="agregar-producto-container">
        <div className="loading-container">
          <p className="loading-text">Cargando datos del producto...</p>
          <div className="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="agregar-producto-container">
      <form onSubmit={handleSubmit} className="agregar-producto-form">
        <div className="form-header-with-button">
          <h1>Editar Producto</h1>
          <button type="button" className="btn-volver" onClick={() => navigate('/admin')}>
            ← Volver al Panel
          </button>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="local_id">Local</label>
            <input
              type="text"
              id="local_id_display"
              value={localUsuario?.nombre || 'Cargando...'}
              disabled
              className="input-disabled"
              title="El local está asociado a tu cuenta de usuario"
            />
            <input
              type="hidden"
              name="local_id"
              value={formData.local_id}
            />
          </div>

          <div className="form-group">
            <label htmlFor="categoria_id">Categoría *</label>
            <div className="categoria-input-wrapper">
              <select
                id="categoria_id"
                name="categoria_id"
                value={formData.categoria_id}
                onChange={handleInputChange}
                required
                disabled={!formData.local_id}
                className={erroresValidacion.categoria_id ? 'input-error' : ''}
              >
                <option value="">Seleccionar categoría</option>
                {categorias.map((categoria) => (
                  <option key={categoria.id} value={categoria.id}>
                    {categoria.nombre}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn-crear-categoria"
                onClick={() => setMostrarModalCategoria(true)}
                disabled={!formData.local_id}
                title="Crear nueva categoría"
              >
                + Nueva
              </button>
            </div>
            {erroresValidacion.categoria_id && (
              <span className="error-campo">{erroresValidacion.categoria_id}</span>
            )}
          </div>
        </div>

        {/* Modal para crear nueva categoría */}
        {mostrarModalCategoria && (
          <div className="modal-overlay" onClick={() => setMostrarModalCategoria(false)}>
            <div className="modal-categoria" onClick={(e) => e.stopPropagation()}>
              <h3>Nueva Categoría</h3>
              
              <div className="modal-form-group">
                <label>Nombre *</label>
                <input
                  type="text"
                  value={nuevaCategoria.nombre}
                  onChange={(e) => setNuevaCategoria(prev => ({ ...prev, nombre: e.target.value }))}
                  placeholder="Nombre de la categoría"
                  maxLength={100}
                />
              </div>

              <div className="modal-form-group">
                <label>Descripción</label>
                <input
                  type="text"
                  value={nuevaCategoria.descripcion}
                  onChange={(e) => setNuevaCategoria(prev => ({ ...prev, descripcion: e.target.value }))}
                  placeholder="Descripción (opcional)"
                  maxLength={200}
                />
              </div>

              {errorCategoria && (
                <div className="modal-error">{errorCategoria}</div>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-modal-cancelar"
                  onClick={() => {
                    setMostrarModalCategoria(false);
                    setNuevaCategoria({ nombre: '', descripcion: '' });
                    setErrorCategoria('');
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

        <div className="form-group">
          <label htmlFor="nombre">
            Nombre del Producto * 
            <span className="limite-caracteres">
              ({formData.nombre.length}/100 caracteres)
            </span>
          </label>
          <input
            type="text"
            id="nombre"
            name="nombre"
            value={formData.nombre}
            onChange={handleInputChange}
            required
            maxLength={100}
            placeholder="Ej: Hamburguesa Clásica"
            className={erroresValidacion.nombre ? 'input-error' : ''}
          />
          {erroresValidacion.nombre && (
            <span className="error-campo">{erroresValidacion.nombre}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="descripcion">
            Descripción 
            <span className="limite-caracteres">
              ({formData.descripcion.length}/500 caracteres)
            </span>
          </label>
          <textarea
            id="descripcion"
            name="descripcion"
            value={formData.descripcion}
            onChange={handleInputChange}
            rows={4}
            maxLength={500}
            placeholder="Descripción detallada del producto..."
            className={erroresValidacion.descripcion ? 'input-error' : ''}
          />
          {erroresValidacion.descripcion && (
            <span className="error-campo">{erroresValidacion.descripcion}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="precio">Precio *</label>
          <div className="input-precio-wrapper">
            <span className="signo-peso">$</span>
            <input
              type="text"
              id="precio"
              name="precio"
              value={formData.precio}
              onChange={handleInputChange}
              required
              className={erroresValidacion.precio ? 'input-error input-precio' : 'input-precio'}
            />
          </div>
          {erroresValidacion.precio && (
            <span className="error-campo">{erroresValidacion.precio}</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="imagen">Imagen del Producto</label>
          <input
            type="file"
            id="imagen"
            accept="image/*"
            onChange={handleImagenChange}
          />
          {previsualizacion && (
            <div className="imagen-preview">
              <img src={previsualizacion} alt="Vista previa" />
              {imagen && <p className="texto-nueva-imagen">Nueva imagen seleccionada</p>}
            </div>
          )}
        </div>

        <div className="form-checkboxes">
          <div className="checkbox-group">
            <input
              type="checkbox"
              id="disponible"
              name="disponible"
              checked={formData.disponible}
              onChange={handleInputChange}
            />
            <label htmlFor="disponible">Producto disponible</label>
          </div>

          <div className="checkbox-group">
            <input
              type="checkbox"
              id="destacado"
              name="destacado"
              checked={formData.destacado}
              onChange={handleInputChange}
            />
            <label htmlFor="destacado">Producto destacado</label>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="form-actions">
          <button
            type="button"
            className="btn-cancelar"
            onClick={() => navigate('/admin')}
            disabled={cargando}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="btn-guardar"
            disabled={cargando}
          >
            {cargando ? 'Actualizando...' : 'Actualizar Producto'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditarProducto;

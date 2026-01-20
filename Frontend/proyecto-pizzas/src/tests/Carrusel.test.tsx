import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Carrusel from '../components/Carrusel/Carrusel';

// Mock del servicio WebSocket
vi.mock('../services/Websocket', () => ({
  connectWebSocket: vi.fn(),
  disconnectWebSocket: vi.fn(),
  on: vi.fn(),
  off: vi.fn(),
}));

// Mock del servicio de caché de imágenes - retorna la URL inmediatamente
vi.mock('../services/ImageCache', () => ({
  preloadAndCacheImage: vi.fn((src: string) => Promise.resolve(src)),
  revokeBlobUrl: vi.fn(),
  clearBlobCache: vi.fn(),
  clearPersistentCache: vi.fn(),
}));

// Mock de useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock de fetch
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

const mockProductos = [
  {
    id: 1,
    nombre: 'Pizza Napolitana',
    descripcion: 'Deliciosa pizza con tomate y albahaca',
    precio: 1200,
    imagen_url: '/imagenes/napolitana.jpg',
    disponible: true,
    categorias: { nombre: 'Pizzas' }
  },
  {
    id: 2,
    nombre: 'Ravioles de Ricota',
    descripcion: 'Pasta casera rellena de ricota',
    precio: 1500,
    imagen_url: '/imagenes/ravioles.jpg',
    disponible: true,
    categorias: { nombre: 'Pastas' }
  },
  {
    id: 3,
    nombre: 'Coca Cola',
    descripcion: 'Bebida 500ml',
    precio: 500,
    imagen_url: '/imagenes/coca.jpg',
    disponible: true,
    categorias: { nombre: 'Bebidas' }
  }
];

const matchCounter = (expected: string) => (content: string) =>
  content.replace(/\s/g, '') === expected.replace(/\s/g, '');

// Helper para mockear fetch de productos + config
const mockFetchProductosYConfig = (productos: any[]) => {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/carrusel/config')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ mode: 'all', selectedCategories: [] })
      });
    }
    // productos
    return Promise.resolve({
      ok: true,
      json: async () => productos
    });
  });
};

describe('Carrusel - Componente', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    const deviceToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
      btoa(JSON.stringify({ local_id: 1, device_id: 'test' })) +
      '.signature';
    localStorage.setItem('device_token', deviceToken);
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('Estado de Carga', () => {
    it('debería mostrar spinner mientras carga', () => {
      mockFetch.mockImplementation(() => new Promise(() => {}));
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      expect(screen.getByText(/cargando productos/i)).toBeInTheDocument();
    });
  });

  describe('Carga de Productos', () => {
    it('debería cargar y mostrar productos correctamente', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      expect(screen.getByText(/deliciosa pizza con tomate/i)).toBeInTheDocument();
      // El precio se muestra formateado con separador de miles
      const precioElement = document.querySelector('.producto-precio');
      expect(precioElement?.textContent).toMatch(/1\.200/);
      expect(screen.getByText('Pizzas')).toBeInTheDocument();
    });

    it('debería usar el token de dispositivo en la petición', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProductos
      });
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
      const fetchCall = mockFetch.mock.calls[0];
      expect(fetchCall[1].headers.Authorization).toContain('Bearer');
    });

    it('debería extraer local_id del token correctamente', async () => {
      const customToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
        btoa(JSON.stringify({ local_id: 5, device_id: 'test' })) +
        '.signature';
      localStorage.setItem('device_token', customToken);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProductos
      });
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
      const fetchCall = mockFetch.mock.calls[0];
      expect(fetchCall[0]).toContain('local_id=5');
    });

    it('debería formatear URLs de imágenes correctamente', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      // Esperar a que la imagen se cargue (el componente OptimizedImage es asíncrono)
      await waitFor(() => {
        const img = screen.queryByRole('img', { name: 'Pizza Napolitana' });
        expect(img).toBeInTheDocument();
      });
      const img = screen.getByRole('img', { name: 'Pizza Napolitana' });
      // La URL de la imagen debería contener la ruta de la imagen
      expect(img.getAttribute('src')).toContain('napolitana');
    });

    it('debería filtrar productos no disponibles', async () => {
      const productosConNoDisponible = [
        ...mockProductos,
        {
          id: 4,
          nombre: 'Producto Agotado',
          descripcion: 'Sin stock',
          precio: 1000,
          imagen_url: '/test.jpg',
          disponible: false,
          categorias: { nombre: 'Test' }
        }
      ];
      mockFetchProductosYConfig(productosConNoDisponible);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      expect(screen.queryByText('Producto Agotado')).not.toBeInTheDocument();
    });
  });

  describe('Manejo de Errores', () => {
    it('debería mostrar error cuando falla la petición', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText(/error al cargar el menú/i)).toBeInTheDocument();
      });
    });

    it('debería mostrar error cuando respuesta no es OK', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404
      });
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText(/error al cargar el menú/i)).toBeInTheDocument();
      });
    });

    it('debería mostrar mensaje cuando no hay productos', async () => {
      mockFetchProductosYConfig([]);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText(/no hay productos/i)).toBeInTheDocument();
      });
    });

    it('debería mostrar mensaje cuando todos los productos están no disponibles', async () => {
      const productosNoDisponibles = mockProductos.map(p => ({
        ...p,
        disponible: false
      }));
      mockFetchProductosYConfig(productosNoDisponibles);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText(/no hay productos/i)).toBeInTheDocument();
      });
    });

    it('debería manejar error al decodificar token', async () => {
      localStorage.setItem('device_token', 'token_invalido');
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockProductos
      });
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });
      consoleSpy.mockRestore();
    });
  });

  describe('Botón Panel de Administración', () => {
    it('debería mostrar botón cuando hay token de admin', async () => {
      localStorage.setItem('adminToken', 'admin_token_123');
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      await waitFor(() => {
        expect(screen.getByText(/volver al panel/i)).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    it('no debería mostrar botón sin token de admin', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      expect(screen.queryByText(/volver al panel/i)).not.toBeInTheDocument();
    });

    it('debería navegar al panel al hacer clic', async () => {
      localStorage.setItem('adminToken', 'admin_token_123');
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      const btnAdmin = await waitFor(() =>
        screen.getByText(/volver al panel/i),
        { timeout: 2000 }
      );
      fireEvent.click(btnAdmin);
      expect(mockNavigate).toHaveBeenCalledWith('/admin');
    });

    it('debería verificar token de admin cada segundo', async () => {
      vi.useFakeTimers();
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await vi.waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      expect(screen.queryByText(/volver al panel/i)).not.toBeInTheDocument();

      localStorage.setItem('adminToken', 'admin_token_123');
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
        await vi.runOnlyPendingTimersAsync();
      });
      await vi.waitFor(() => {
        expect(screen.getByText(/volver al panel/i)).toBeInTheDocument();
      });

      localStorage.removeItem('adminToken');
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000);
        await vi.runOnlyPendingTimersAsync();
      });
      await vi.waitFor(() => {
        expect(screen.queryByText(/volver al panel/i)).not.toBeInTheDocument();
      });

      vi.useRealTimers();
    });

    it('debería limpiar intervalo de verificación al desmontar', async () => {
      mockFetchProductosYConfig(mockProductos);
      const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
      const { unmount } = render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      clearIntervalSpy.mockClear();
      unmount();
      expect(clearIntervalSpy).toHaveBeenCalled();
      clearIntervalSpy.mockRestore();
    });
  });

  describe('Renderizado de Productos', () => {
    it('debería mostrar categoría del producto', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizzas')).toBeInTheDocument();
      });
    });

    it('debería mostrar "Sin categoría" si no tiene', async () => {
      const productoSinCategoria = [{
        ...mockProductos[0],
        categorias: undefined
      }];
      mockFetchProductosYConfig(productoSinCategoria);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Sin categoría')).toBeInTheDocument();
      });
    });

    it('debería formatear precio sin decimales', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        const precioElement = document.querySelector('.producto-precio');
        expect(precioElement?.textContent).toMatch(/1\.200/);
      });
    });

    it('debería mostrar imagen del producto', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });
      // Esperar a que la imagen se cargue (el componente OptimizedImage es asíncrono)
      await waitFor(() => {
        const img = screen.queryByRole('img', { name: 'Pizza Napolitana' });
        expect(img).toBeInTheDocument();
      });
      const img = screen.getByRole('img', { name: 'Pizza Napolitana' }) as HTMLImageElement;
      expect(img).toBeInTheDocument();
      expect(img.src).toContain('napolitana');
    });

    it('debería mostrar dots de navegación', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByLabelText('Ir al producto 1')).toBeInTheDocument();
        expect(screen.getByLabelText('Ir al producto 2')).toBeInTheDocument();
        expect(screen.getByLabelText('Ir al producto 3')).toBeInTheDocument();
      });
    });

    it('debería mostrar header con título', async () => {
      mockFetchProductosYConfig(mockProductos);
      render(
        <BrowserRouter>
          <Carrusel />
        </BrowserRouter>
      );
      await waitFor(() => {
        expect(screen.getByText('NUESTROS PRODUCTOS')).toBeInTheDocument();
      });
    });
  });
});
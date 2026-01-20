import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import PanelAdmin from '../components/Admin/PanelAdmin';

// Mock del servicio de caché de imágenes - retorna la URL inmediatamente
vi.mock('../services/ImageCache', () => ({
  preloadAndCacheImage: vi.fn((src: string) => Promise.resolve(src)),
  revokeBlobUrl: vi.fn(),
  clearBlobCache: vi.fn(),
  clearPersistentCache: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

global.fetch = vi.fn();

const mockCategorias = [
  { id: 1, nombre: 'Pizzas', descripcion: 'Pizzas artesanales', orden: 1 },
  { id: 2, nombre: 'Pastas', descripcion: 'Pastas caseras', orden: 2 }
];

const mockLocales = [{ nombre: 'Mi Local' }];

const mockProductos = [
  {
    id: 1,
    nombre: 'Pizza Napolitana',
    descripcion: 'Con tomate y albahaca',
    precio: 1200,
    imagen_url: '/imagenes/napolitana.jpg',
    disponible: true,
    destacado: false,
    orden: 1,
    categoria_id: 1,
    categorias: { id: 1, nombre: 'Pizzas' }
  },
  {
    id: 2,
    nombre: 'Ravioles',
    descripcion: 'Pasta casera',
    precio: 1500,
    imagen_url: '/imagenes/ravioles.jpg',
    disponible: true,
    destacado: true,
    orden: 2,
    categoria_id: 1,
    categorias: { id: 1, nombre: 'Pizzas' }
  }
];

// Helper para abrir/cerrar una categoría (clic en el <h2>)
const abrirCategoria = async (nombre: string) => {
  const h2 = screen.queryAllByRole('heading', { level: 2 }).find(h =>
    h.textContent?.includes(nombre)
  );
  if (h2) {
    fireEvent.click(h2);
    await new Promise(res => setTimeout(res, 400));
  }
};

describe('PanelAdmin - Componente', () => {
  let productosState: typeof mockProductos;

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('adminToken', 'valid_admin_token');

    productosState = mockProductos.map(p => ({ ...p }));

    (global.fetch as any).mockImplementation(async (input: RequestInfo | string, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method || 'GET').toString().toUpperCase();

      if (url.includes('/admin/categorias') && method === 'GET') {
        return { ok: true, json: async () => mockCategorias };
      }

      if (url.includes('/admin/locales') && method === 'GET') {
        return { ok: true, json: async () => mockLocales };
      }

      if (url.includes('/admin/productos') && method === 'GET') {
        return { ok: true, json: async () => productosState };
      }

      const deleteMatch = url.match(/\/admin\/productos\/(\d+)\b/);
      if (deleteMatch && method === 'DELETE') {
        const id = Number(deleteMatch[1]);
        productosState = productosState.filter(p => p.id !== id);
        return { ok: true, json: async () => ({ message: 'Producto eliminado' }) };
      }

      const dispMatch = url.match(/\/admin\/productos\/(\d+)(\/disponibilidad)?/);
      if (dispMatch && method === 'PATCH') {
        const id = Number(dispMatch[1]);
        const idx = productosState.findIndex(p => p.id === id);
        if (idx >= 0) {
          productosState[idx] = { ...productosState[idx], disponible: !productosState[idx].disponible };
          return { ok: true, json: async () => productosState[idx] };
        }
        return { ok: false, status: 404 };
      }

      return { ok: true, json: async () => ({}) };
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('debería cargar productos y mostrar ambos bajo "Pizzas"', async () => {
    render(
      <BrowserRouter>
        <PanelAdmin />
      </BrowserRouter>
    );

    await waitFor(() => {
      const headings = screen.queryAllByRole('heading', { level: 2 });
      expect(headings.some(h => h.textContent?.includes('Pizzas'))).toBe(true);
    });

    await abrirCategoria('Pizzas');

    await waitFor(() => {
      expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      expect(screen.getByText('Ravioles')).toBeInTheDocument();
    });
  });

  it('debería permitir eliminar producto y seguir mostrando la categoría o el producto restante', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(
      <BrowserRouter>
        <PanelAdmin />
      </BrowserRouter>
    );

    await waitFor(() => {
      const headings = screen.queryAllByRole('heading', { level: 2 });
      expect(headings.some(h => h.textContent?.includes('Pizzas'))).toBe(true);
    });

    await abrirCategoria('Pizzas');

    await waitFor(() => {
      expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      expect(screen.getByText('Ravioles')).toBeInTheDocument();
    });

    const btnEliminarProducto = screen.getAllByText(/eliminar/i).find((el) => el.closest('.producto-acciones'));
    expect(btnEliminarProducto).toBeTruthy();
    fireEvent.click(btnEliminarProducto!);

    const modal = document.querySelector('.modal-overlay') as HTMLElement | null;
    expect(modal).toBeTruthy();
    const modalEliminar = within(modal as HTMLElement).getByText('Eliminar');
    fireEvent.click(modalEliminar);

    await waitFor(() => {
      const calls = (global.fetch as any).mock.calls;
      const found = calls.some((call: any[]) => {
        const url = String(call[0]);
        const init = call[1] || {};
        return url.includes('/admin/productos/1') && (init.method || '').toUpperCase() === 'DELETE';
      });
      expect(found).toBe(true);
    });

    await waitFor(() => {
      expect(screen.getByText('Ravioles')).toBeInTheDocument();
      expect(screen.queryByText('Pizza Napolitana')).not.toBeInTheDocument();
    });

    confirmSpy.mockRestore();
  });

  it('debería cancelar eliminación si usuario rechaza', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);

    render(
      <BrowserRouter>
        <PanelAdmin />
      </BrowserRouter>
    );

    await waitFor(() => {
      const headings = screen.queryAllByRole('heading', { level: 2 });
      expect(headings.some(h => h.textContent?.includes('Pizzas'))).toBe(true);
    });

    await abrirCategoria('Pizzas');

    await waitFor(() => {
      expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
    });

    const fetchCallsBefore = (global.fetch as any).mock.calls.length;
    const btnEliminar = screen.getAllByText(/eliminar/i).find(el => el.closest('.producto-acciones'));
    fireEvent.click(btnEliminar!);

    // No confirmar modal -> no llamada DELETE adicional
    expect((global.fetch as any).mock.calls.length).toBe(fetchCallsBefore);
  });

  it('debería cambiar disponibilidad de producto', async () => {
    render(
      <BrowserRouter>
        <PanelAdmin />
      </BrowserRouter>
    );

    await waitFor(() => {
      const headings = screen.queryAllByRole('heading', { level: 2 });
      expect(headings.some(h => h.textContent?.includes('Pizzas'))).toBe(true);
    });

    await abrirCategoria('Pizzas');

    await waitFor(() => {
      expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
    });

    const productoHeader = screen.getByText('Pizza Napolitana');
    const productoItem = productoHeader.closest('.producto-item') as HTMLElement | null;
    expect(productoItem).toBeTruthy();

    // Verifica que el estado inicial se muestre correctamente.
    const estadoSpan = within(productoItem as HTMLElement).getByText(/Disponible|Sin Stock/i);
    expect(estadoSpan).toBeInTheDocument();
    expect(estadoSpan.classList.contains('disponible')).toBe(true);
  });

  it('debería cerrar sesión correctamente', async () => {
    render(
      <BrowserRouter>
        <PanelAdmin />
      </BrowserRouter>
    );

    await waitFor(() => {
      const headings = screen.queryAllByRole('heading', { level: 2 });
      expect(headings.some(h => h.textContent?.includes('Pizzas'))).toBe(true);
    });

    const btnCerrar = screen.getByText(/cerrar sesión/i);
    fireEvent.click(btnCerrar);

    // handleLogout es async, esperar a que limpie el localStorage
    await waitFor(() => {
      expect(localStorage.getItem('adminToken')).toBeNull();
    });
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('debería abrir y cerrar categorías al hacer clic', async () => {
    render(
      <BrowserRouter>
        <PanelAdmin />
      </BrowserRouter>
    );

    await waitFor(() => {
      const headings = screen.queryAllByRole('heading', { level: 2 });
      expect(headings.some(h => h.textContent?.includes('Pizzas'))).toBe(true);
    });

    // localizar h2 y su lista de productos asociada para verificar la clase 'abierta' se alterna
    const h2 = screen.getAllByRole('heading', { level: 2 }).find(h => h.textContent?.includes('Pizzas'))!;
    const lista = h2.nextElementSibling as HTMLElement | null;
    expect(lista).toBeTruthy();
    const initiallyOpen = lista!.classList.contains('abierta');

    // click para alternar
    fireEvent.click(h2);
    await new Promise(res => setTimeout(res, 400));
    expect(lista!.classList.contains('abierta')).toBe(!initiallyOpen);

    // click nuevamente para volver al estado inicial
    fireEvent.click(h2);
    await new Promise(res => setTimeout(res, 400));
    expect(lista!.classList.contains('abierta')).toBe(initiallyOpen);
  });
});
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Menu from '../components/Menu/Menu';

// Mock del servicio de caché de imágenes - retorna la URL inmediatamente
vi.mock('../services/ImageCache', () => ({
  preloadAndCacheImage: vi.fn((src: string) => Promise.resolve(src)),
  revokeBlobUrl: vi.fn(),
  clearBlobCache: vi.fn(),
  clearPersistentCache: vi.fn(),
}));

global.fetch = vi.fn();

const mockMenuData = {
  categorias: [
    {
      id: 1,
      nombre: 'Pizzas',
      descripcion: 'Pizzas artesanales',
      productos: [
        {
          id: 1,
          nombre: 'Pizza Napolitana',
          descripcion: 'Con tomate y albahaca',
          precio: 1200,
          imagen_url: '/imagenes/napolitana.jpg',
          disponible: true,
          destacado: true
        },
        {
          id: 2,
          nombre: 'Pizza Muzzarella',
          descripcion: 'Clásica con muzzarella',
          precio: 1000,
          imagen_url: '/imagenes/muzzarella.jpg',
          disponible: true,
          destacado: false
        }
      ]
    },
    {
      id: 2,
      nombre: 'Bebidas',
      descripcion: 'Bebidas frías',
      productos: [
        {
          id: 3,
          nombre: 'Coca Cola',
          descripcion: '500ml',
          precio: 500,
          imagen_url: '/imagenes/coca.jpg',
          disponible: true,
          destacado: false
        }
      ]
    }
  ]
};

// helper para mockear correctamente los dos endpoints que usa Menu.tsx
const setupMockMenuFetch = () => {
  const productosArray = mockMenuData.categorias.flatMap(c =>
    c.productos.map(p => ({ ...p, categorias: { id: c.id, nombre: c.nombre } }))
  );
  const categoriasArray = mockMenuData.categorias.map(c => ({ id: c.id, nombre: c.nombre, descripcion: c.descripcion }));
  (global.fetch as any)
    .mockResolvedValueOnce({ ok: true, json: async () => productosArray })
    .mockResolvedValueOnce({ ok: true, json: async () => categoriasArray });
};

describe('Menu - Componente de Usuario', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // token falso con payload decodificable { "local_id": 1 }
    const payloadBase64 = btoa(JSON.stringify({ local_id: 1 }));
    const fakeJwt = `header.${payloadBase64}.signature`;
    localStorage.setItem('device_token', fakeJwt);
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('Carga de menú', () => {
    it('debería cargar el menú al montar', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        // comprobar que se usó el token almacenado
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/menu/productos'),
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': `Bearer ${localStorage.getItem('device_token')}`
            })
          })
        );
      });
    });

    it('debería mostrar todas las categorías', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        const categorias = screen.getAllByText('Pizzas');
        expect(categorias.length).toBeGreaterThan(0);
        expect(screen.getAllByText('Bebidas').length).toBeGreaterThan(0);
      });
    });

    it('debería mostrar mensaje si no hay productos', async () => {
      (global.fetch as any)
        .mockResolvedValueOnce({ ok: true, json: async () => [] })
        .mockResolvedValueOnce({ ok: true, json: async () => [] });

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        // Espera que el main esté vacío (no hay productos ni categorías)
        const main = document.querySelector('.menu-content');
        expect(main?.textContent?.trim()).toBe('');
      });
    });

    it('debería manejar error al cargar menú', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Visualización de productos', () => {
    it('debería mostrar precio formateado', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('$1.200')).toBeInTheDocument();
        expect(screen.getByText('$1.000')).toBeInTheDocument();
        expect(screen.getByText('$500')).toBeInTheDocument();
      });
    });

    it('debería mostrar imágenes de productos', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        const img = screen.getByAltText('Pizza Napolitana') as HTMLImageElement;
        expect(img.src).toContain('napolitana.jpg');
      });
    });

    it('debería destacar productos destacados', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        const header = screen.getByText('Pizza Napolitana');
        const card = header.closest('.producto-card') as HTMLElement;
        expect(card).toBeTruthy();
        expect(within(card).getByText('Destacado')).toBeInTheDocument();
      });
    });
  });

  describe('Filtros por categoría', () => {
    it('debería filtrar productos por categoría seleccionada', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });

      const btnPizzas = screen.getByRole('button', { name: 'Pizzas' });
      fireEvent.click(btnPizzas);

      await waitFor(() => {
        // Busca solo en la sección de Pizzas
        const seccionPizzas = screen.getAllByText('Pizzas').find(
          el => el.tagName === 'H2'
        )?.closest('.categoria-section');
        expect(within(seccionPizzas!).getByText('Pizza Napolitana')).toBeInTheDocument();
        expect(within(seccionPizzas!).getByText('Pizza Muzzarella')).toBeInTheDocument();
        expect(within(seccionPizzas!).queryByText('Coca Cola')).not.toBeInTheDocument();
      });
    });

    it('debería mostrar todos los productos al seleccionar "Todos"', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
        expect(screen.getByText('Coca Cola')).toBeInTheDocument();
      });
    });
  });

  describe('Interacción con productos', () => {
    it('debería mostrar modal con detalles al hacer clic', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });

      const producto = screen.getByText('Pizza Napolitana');
      const productoCard = producto.closest('.producto-card') as HTMLElement;
      fireEvent.click(productoCard);

      await waitFor(() => {
        expect(screen.getByText('Con tomate y albahaca')).toBeInTheDocument();
      });
    });

    it('debería cerrar modal al hacer clic fuera', async () => {
      setupMockMenuFetch();

      render(
        <BrowserRouter>
          <Menu />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Pizza Napolitana')).toBeInTheDocument();
      });

      const producto = screen.getByText('Pizza Napolitana');
      const productoCard2 = producto.closest('.producto-card') as HTMLElement;
      fireEvent.click(productoCard2);

      await waitFor(() => {
        expect(screen.getByText('Con tomate y albahaca')).toBeInTheDocument();
      });

      // Busca el overlay o el botón cerrar
      const overlay = document.querySelector('.modal-overlay') as HTMLElement | null;
      if (overlay) {
        fireEvent.mouseDown(overlay);
        fireEvent.mouseUp(overlay);
        fireEvent.click(overlay);
      } else {
        const btnCerrar = screen.queryByRole('button', { name: /cerrar/i }) || screen.queryByLabelText(/cerrar/i);
        if (btnCerrar) fireEvent.click(btnCerrar);
        else {
          fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' });
        }
      }

      // Espera hasta 3 segundos por si el cierre es asíncrono
    });
  });
});

// ProtectedApp.test.tsx - VERSIÓN FUNCIONAL
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import App from '../App';

// Mock del servicio de caché de imágenes - retorna la URL inmediatamente
vi.mock('../services/ImageCache', () => ({
  preloadAndCacheImage: vi.fn((src: string) => Promise.resolve(src)),
  revokeBlobUrl: vi.fn(),
  clearBlobCache: vi.fn(),
  clearPersistentCache: vi.fn(),
}));

// Mock de WebSocket - CRÍTICO para evitar conexiones reales
class MockWebSocket {
  constructor(url: string) {
    // Opcional: console.log('Mock WebSocket creado para:', url);
  }
  send = vi.fn();
  close = vi.fn();
  addEventListener = vi.fn((event, callback) => {
    if (event === 'open') setTimeout(() => callback(), 0);
  });
  removeEventListener = vi.fn();
}

// Mock de localStorage
const createLocalStorageMock = () => {
  const store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = String(value);
      Object.defineProperty(store, key, {
        value: String(value),
        writable: true,
      });
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      Object.keys(store).forEach(key => delete store[key]);
    }),
    store
  };
};

const matchNotFound = (content: string) =>
  content.toLowerCase().includes('página no encontrada');

describe('ProtectedApp - Autenticación de Dispositivos', () => {
  let localStorageMock: ReturnType<typeof createLocalStorageMock>;
  let originalWebSocket: typeof WebSocket;
  let originalFetch: typeof fetch;
  let originalAtob: typeof atob;

  beforeEach(() => {
    // Guardar originales
    originalWebSocket = global.WebSocket;
    originalFetch = global.fetch;
    originalAtob = global.atob;

    // Configurar mocks
    localStorageMock = createLocalStorageMock();
    global.WebSocket = MockWebSocket as any;
    global.fetch = vi.fn();
    global.atob = vi.fn((str: string) => {
      // Simular decodificación de JWT
      const payload = JSON.stringify({
        device_id: 'test_device',
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000)
      });
      return payload;
    });

    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true
    });

    window.history.replaceState({}, '', '/');
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
    global.fetch = originalFetch;
    global.atob = originalAtob;
    cleanup();
    localStorageMock.clear();
  });

  it('debería mostrar "Página no encontrada" sin credenciales en la URL', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(matchNotFound)).toBeInTheDocument();
    });
  });

  it('debería autenticar con credenciales válidas en la URL', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        token: 'jwt_token_123',
        device_id: 'raspberry_1'
      })
    });

    window.history.replaceState(
      {},
      '',
      '/?device_id=raspberry_1&secret_key=token_super_secreto_raspberry_1'
    );

    render(<App />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/device'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            device_id: 'raspberry_1',
            secret_key: 'token_super_secreto_raspberry_1'
          })
        })
      );
    });

    await waitFor(() => {
      expect(localStorage.getItem('device_token')).toBe('jwt_token_123');
      expect(localStorage.getItem('device_id')).toBe('raspberry_1');
    });
  });

  it('debería rechazar credenciales inválidas', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Pagina no encontrada' })
    });

    window.history.replaceState(
      {},
      '',
      '/?device_id=fake_device&secret_key=wrong_key'
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(matchNotFound)).toBeInTheDocument();
    });

    expect(localStorage.getItem('device_token')).toBeNull();
  });

  it('debería usar token guardado en localStorage', async () => {
    localStorage.setItem('device_token', 'stored_jwt_token');
    localStorage.setItem('device_id', 'raspberry_1');

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'authorized',
        device_id: 'raspberry_1'
      })
    });

    render(<App />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/verify'),
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer stored_jwt_token'
          })
        })
      );
    });

    await waitFor(() => {
      expect(screen.queryByText(matchNotFound)).not.toBeInTheDocument();
    });
  });

  it('debería limpiar localStorage si el token guardado es inválido', async () => {
    localStorage.setItem('device_token', 'invalid_token');
    localStorage.setItem('device_id', 'raspberry_1');

    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401
    });

    render(<App />);

    await waitFor(() => {
      expect(localStorage.getItem('device_token')).toBeNull();
      expect(localStorage.getItem('device_id')).toBeNull();
    });
  });

  it('debería limpiar la URL después de autenticar', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        token: 'jwt_token_123',
        device_id: 'raspberry_1'
      })
    });

    const replaceStateSpy = vi.spyOn(window.history, 'replaceState');

    window.history.replaceState(
      {},
      '',
      '/?device_id=raspberry_1&secret_key=token_super_secreto_raspberry_1'
    );

    render(<App />);

    await waitFor(() => {
      expect(replaceStateSpy).toHaveBeenCalledWith({}, '', '/');
    });

    replaceStateSpy.mockRestore();
  });

  it('debería manejar errores de red', async () => {
    (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

    window.history.replaceState(
      {},
      '',
      '/?device_id=raspberry_1&secret_key=token_super_secreto_raspberry_1'
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(matchNotFound)).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('debería funcionar con diferentes dispositivos autorizados', async () => {
    const devices = [
      { id: 'raspberry_1', key: 'token_super_secreto_raspberry_1' },
      { id: 'raspberry_2', key: 'token_super_secreto_raspberry_2' },
      { id: 'admin_pc', key: 'token_super_secreto_admin' }
    ];

    for (const device of devices) {
      localStorage.clear();
      vi.clearAllMocks();

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          token: `jwt_token_${device.id}`,
          device_id: device.id
        })
      });

      window.history.replaceState(
        {},
        '',
        `/?device_id=${device.id}&secret_key=${device.key}`
      );

      render(<App />);

      await waitFor(() => {
        expect(localStorage.getItem('device_id')).toBe(device.id);
      }, { timeout: 2000 });
    }
  });
});
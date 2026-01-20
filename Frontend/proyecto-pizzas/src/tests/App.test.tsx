import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/react';
import App from '../App';

// Mock del servicio de caché de imágenes - retorna la URL inmediatamente
vi.mock('../services/ImageCache', () => ({
  preloadAndCacheImage: vi.fn((src: string) => Promise.resolve(src)),
  revokeBlobUrl: vi.fn(),
  clearBlobCache: vi.fn(),
  clearPersistentCache: vi.fn(),
}));

// Mock de fetch
globalThis.fetch = vi.fn();

// Mock de WebSocket
class MockWebSocket {
  url: string;
  readyState: number = WebSocket.OPEN;
  onopen: any = null;
  onclose: any = null;
  onerror: any = null;
  onmessage: any = null;

  constructor(url: string) {
    this.url = url;
  }

  send() {}
  close() {}
}

globalThis.WebSocket = MockWebSocket as any;

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    
    vi.mocked(globalThis.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: 'test_token' }),
    } as Response);
  });

  it('debe renderizar sin errores', () => {
    const { container } = render(<App />);
    expect(container).toBeTruthy();
  });

  it('debe renderizar la ruta raíz correctamente', () => {
    const { container } = render(<App />);
    expect(container.firstChild).toBeTruthy();
  });

  it('debe manejar rutas con parámetros', () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?device=test&local=1',
        href: 'http://localhost:3000/?device=test&local=1'
      },
      writable: true
    });

    const { container } = render(<App />);
    expect(container).toBeTruthy();
  });
});
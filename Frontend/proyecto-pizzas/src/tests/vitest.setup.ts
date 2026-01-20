// vitest.setup.ts
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock para import.meta.env
vi.mock('../services/Websocket', async () => {
  const actual = await vi.importActual('../services/Websocket');
  return {
    ...actual,
    VITE_WS_URL: 'ws://localhost:8000'
  };
});

// Mock global para Cache API (no existe en jsdom/node)
const mockCache = {
  match: vi.fn().mockResolvedValue(undefined),
  put: vi.fn().mockResolvedValue(undefined),
  delete: vi.fn().mockResolvedValue(true),
  keys: vi.fn().mockResolvedValue([]),
  add: vi.fn().mockResolvedValue(undefined),
  addAll: vi.fn().mockResolvedValue(undefined),
};

const mockCaches = {
  open: vi.fn().mockResolvedValue(mockCache),
  delete: vi.fn().mockResolvedValue(true),
  has: vi.fn().mockResolvedValue(false),
  keys: vi.fn().mockResolvedValue([]),
  match: vi.fn().mockResolvedValue(undefined),
};

// Asignar caches globalmente
Object.defineProperty(globalThis, 'caches', {
  value: mockCaches,
  writable: true,
});

// Mock para URL.createObjectURL y URL.revokeObjectURL
if (!globalThis.URL.createObjectURL) {
  globalThis.URL.createObjectURL = vi.fn((blob: Blob) => `blob:mock-url-${Math.random()}`);
}
if (!globalThis.URL.revokeObjectURL) {
  globalThis.URL.revokeObjectURL = vi.fn();
}

// Variables globales para los tests
declare global {
  var __ws_listeners: Record<string, Function[]>;
  var reconnectTimeout: NodeJS.Timeout | null;
}

beforeEach(() => {
  // Resetear variables globales
  globalThis.__ws_listeners = {};
  globalThis.reconnectTimeout = null;
  
  // Resetear mocks de cache
  vi.mocked(mockCache.match).mockReset().mockResolvedValue(undefined);
  vi.mocked(mockCache.put).mockReset().mockResolvedValue(undefined);
  vi.mocked(mockCaches.open).mockReset().mockResolvedValue(mockCache);
});
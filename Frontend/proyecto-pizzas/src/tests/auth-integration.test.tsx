import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import App from '../App';

// Mock del servicio de caché de imágenes - retorna la URL inmediatamente
vi.mock('../services/ImageCache', () => ({
  preloadAndCacheImage: vi.fn((src: string) => Promise.resolve(src)),
  revokeBlobUrl: vi.fn(),
  clearBlobCache: vi.fn(),
  clearPersistentCache: vi.fn(),
}));

global.fetch = vi.fn();

const matchNotFound = (content: string) =>
  content.toLowerCase().includes('página no encontrada');

describe('Integración: Protección de Rutas', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    localStorage.clear();
    window.history.replaceState({}, '', '/');
  });

  it('debería bloquear acceso a /login sin token', async () => {
    window.history.replaceState({}, '', '/login');

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(matchNotFound)).toBeInTheDocument();
      // No debería renderizar el componente LoginAdmin
      expect(screen.queryByText(/iniciar sesión/i)).not.toBeInTheDocument();
    });
  });

  it('debería permitir acceso a /login con token válido', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        token: 'valid_jwt',
        device_id: 'admin_pc'
      })
    });

    window.history.replaceState(
      {}, 
      '', 
      '/login?device_id=admin_pc&secret_key=token_super_secreto_admin'
    );

    render(<App />);

    await waitFor(() => {
      // Debería renderizar LoginAdmin después de autenticar
      expect(screen.queryByText(matchNotFound)).not.toBeInTheDocument();
    });
  });

  it('debería bloquear acceso a /admin sin token de dispositivo', async () => {
    window.history.replaceState({}, '', '/admin');

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(matchNotFound)).toBeInTheDocument();
    });
  });

  it('debería mantener sesión al navegar entre rutas', async () => {
    localStorage.setItem('device_token', 'valid_jwt');
    localStorage.setItem('device_id', 'raspberry_1');

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'authorized' })
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.queryByText(matchNotFound)).not.toBeInTheDocument();
    });

    // Simular navegación (el token debería persistir)
    expect(localStorage.getItem('device_token')).toBe('valid_jwt');
  });
});
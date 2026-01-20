import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Api from '../services/Api';

// Mock de fetch
globalThis.fetch = vi.fn() as any;

describe('Api Service', () => {
  const API_URL = 'http://localhost:8000';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('getData', () => {
    it('debe hacer una petición GET correctamente', async () => {
      const mockData = { id: 1, nombre: 'Test' };
      
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      } as Response);

      const result = await Api.getData('productos');

      expect(fetch).toHaveBeenCalledWith(
        `${API_URL}/productos`,
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      );
      expect(result).toEqual(mockData);
    });

    it('debe lanzar error cuando la respuesta no es ok', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Error del servidor' }),
      } as Response);

      await expect(Api.getData('productos')).rejects.toThrow('Error del servidor');
    });

    it('debe lanzar error genérico si no hay detail', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      } as Response);

      await expect(Api.getData('productos')).rejects.toThrow('GET error');
    });

    it('debe incluir Content-Type en headers', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await Api.getData('test');

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    it('debe construir la URL correctamente', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await Api.getData('menu/1');

      expect(fetch).toHaveBeenCalledWith(
        `${API_URL}/menu/1`,
        expect.any(Object)
      );
    });
  });

  describe('postData', () => {
    it('debe hacer una petición POST correctamente', async () => {
      const payload = { nombre: 'Pizza', precio: 10.99 };
      const mockResponse = { id: 1, ...payload };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await Api.postData('productos', payload);

      expect(fetch).toHaveBeenCalledWith(
        `${API_URL}/productos`,
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('debe enviar el payload como JSON', async () => {
      const payload = { email: 'test@test.com', password: '123456' };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await Api.postData('auth/login', payload);

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify(payload),
        })
      );
    });

    it('debe lanzar error cuando la respuesta no es ok', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Credenciales incorrectas' }),
      } as Response);

      await expect(Api.postData('auth/login', {})).rejects.toThrow('Credenciales incorrectas');
    });

    it('debe lanzar error genérico si no hay detail', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      } as Response);

      await expect(Api.postData('productos', {})).rejects.toThrow('POST error');
    });

    it('debe manejar diferentes tipos de payload', async () => {
      const payloads = [
        { string: 'test' },
        { number: 123 },
        { boolean: true },
        { array: [1, 2, 3] },
        { nested: { deep: { value: 'test' } } },
      ];

      for (const payload of payloads) {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: true,
          json: async () => payload,
        } as Response);

        const result = await Api.postData('test', payload);
        expect(result).toEqual(payload);
      }
    });
  });

  describe('putData', () => {
    it('debe hacer una petición PUT correctamente', async () => {
      const payload = { nombre: 'Pizza Actualizada', precio: 15.99 };
      const mockResponse = { id: 1, ...payload };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockResponse),
      } as Response);

      const result = await Api.putData('productos/1', payload);

      expect(fetch).toHaveBeenCalledWith(
        `${API_URL}/productos/1`,
        expect.objectContaining({
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('debe retornar null cuando la respuesta está vacía', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      } as Response);

      const result = await Api.putData('productos/1', {});

      expect(result).toBeNull();
    });

    it('debe lanzar error cuando la respuesta no es ok', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Producto no encontrado' }),
      } as Response);

      await expect(Api.putData('productos/999', {})).rejects.toThrow('Producto no encontrado');
    });

    it('debe lanzar error genérico si no hay detail', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      } as Response);

      await expect(Api.putData('productos/1', {})).rejects.toThrow('PUT error');
    });

    it('debe parsear JSON correctamente', async () => {
      const mockData = { id: 1, updated: true };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockData),
      } as Response);

      const result = await Api.putData('productos/1', {});

      expect(result).toEqual(mockData);
    });
  });

  describe('deleteData', () => {
    it('debe hacer una petición DELETE sin payload', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({ message: 'Eliminado' }),
      } as Response);

      const result = await Api.deleteData('productos/1');

      expect(fetch).toHaveBeenCalledWith(
        `${API_URL}/productos/1`,
        expect.objectContaining({
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: null,
        })
      );
      expect(result).toEqual({ message: 'Eliminado' });
    });

    it('debe hacer una petición DELETE con payload', async () => {
      const payload = { motivo: 'Producto descontinuado' };

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({ success: true }),
      } as Response);

      await Api.deleteData('productos/1', payload);

      expect(fetch).toHaveBeenCalledWith(
        `${API_URL}/productos/1`,
        expect.objectContaining({
          method: 'DELETE',
          body: JSON.stringify(payload),
        })
      );
    });

    it('debe retornar null cuando la respuesta está vacía', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      } as Response);

      const result = await Api.deleteData('productos/1');

      expect(result).toBeNull();
    });

    it('debe lanzar error cuando la respuesta no es ok', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'No se puede eliminar' }),
      } as Response);

      await expect(Api.deleteData('productos/1')).rejects.toThrow('No se puede eliminar');
    });

    it('debe lanzar error genérico si no hay detail', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      } as Response);

      await expect(Api.deleteData('productos/1')).rejects.toThrow('DELETE error');
    });

    it('debe manejar body null correctamente', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      } as Response);

      await Api.deleteData('productos/1');

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: null,
        })
      );
    });
  });

  describe('Manejo de Errores', () => {
    it('debe manejar errores de red', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network Error'));

      await expect(Api.getData('productos')).rejects.toThrow('Network Error');
    });

    it('debe manejar timeout', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Request timeout'));

      await expect(Api.postData('productos', {})).rejects.toThrow('Request timeout');
    });

    it('debe manejar respuestas JSON inválidas', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      } as unknown as Response);

      await expect(Api.getData('productos')).rejects.toThrow('Invalid JSON');
    });

    it('debe manejar errores al parsear text en PUT', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => 'invalid json{',
      } as Response);

      await expect(Api.putData('productos/1', {})).rejects.toThrow();
    });

    it('debe manejar errores al parsear text en DELETE', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => 'invalid json{',
      } as Response);

      await expect(Api.deleteData('productos/1')).rejects.toThrow();
    });
  });

  describe('Configuración de URL', () => {
    it('debe usar la URL base correcta', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      } as Response);

      await Api.getData('test');

      expect(fetch).toHaveBeenCalledWith(
        expect.stringMatching(/^http:\/\/localhost:8000/),
        expect.any(Object)
      );
    });

    it('debe concatenar endpoint correctamente', async () => {
      const endpoints = ['productos', 'menu/1', 'auth/login', 'locales'];

      for (const endpoint of endpoints) {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: true,
          json: async () => ({}),
        } as Response);

        await Api.getData(endpoint);

        expect(fetch).toHaveBeenCalledWith(
          `${API_URL}/${endpoint}`,
          expect.any(Object)
        );
      }
    });
  });

  describe('Headers', () => {
    it('debe incluir Content-Type en todas las peticiones', async () => {
      const methods = [
        { fn: Api.getData, args: ['test'] },
        { fn: Api.postData, args: ['test', {}] },
        { fn: Api.putData, args: ['test', {}] },
        { fn: Api.deleteData, args: ['test'] },
      ];

      for (const { fn, args } of methods) {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: true,
          json: async () => ({}),
          text: async () => '',
        } as Response);

        await (fn as (...args: any[]) => Promise<any>)(...args);

        expect(fetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
    });
  });

  describe('Respuestas Vacías', () => {
    it('PUT debe retornar null con respuesta vacía', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      } as Response);

      const result = await Api.putData('test', {});

      expect(result).toBeNull();
    });

    it('DELETE debe retornar null con respuesta vacía', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      } as Response);

      const result = await Api.deleteData('test');

      expect(result).toBeNull();
    });

    it('PUT debe parsear JSON cuando hay contenido', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => '{"id": 1}',
      } as Response);

      const result = await Api.putData('test', {});

      expect(result).toEqual({ id: 1 });
    });

    it('DELETE debe parsear JSON cuando hay contenido', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        text: async () => '{"deleted": true}',
      } as Response);

      const result = await Api.deleteData('test');

      expect(result).toEqual({ deleted: true });
    });
  });
});
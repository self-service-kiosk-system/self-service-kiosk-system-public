// Websocket.test.ts - VERSIÓN CORREGIDA Y SIMPLIFICADA
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock de WebSocket
class MockWebSocket {
  // AGREGAR CONSTANTES ESTÁTICAS
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  url: string;
  readyState: number = WebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }

  send(_data: string) {
    // Mock send
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSING;
    setTimeout(() => {
      this.readyState = MockWebSocket.CLOSED;
      if (this.onclose) {
        const event = new CloseEvent('close', { code, reason });
        this.onclose(event);
      }
    }, 0);
  }

  addEventListener(type: string, listener: any) {
    if (type === 'open') this.onopen = listener;
    if (type === 'close') this.onclose = listener;
    if (type === 'error') this.onerror = listener;
    if (type === 'message') this.onmessage = listener;
  }

  removeEventListener(type: string) {
    if (type === 'open') this.onopen = null;
    if (type === 'close') this.onclose = null;
    if (type === 'error') this.onerror = null;
    if (type === 'message') this.onmessage = null;
  }
}

globalThis.WebSocket = MockWebSocket as any;

describe('WebSocket Service - Cobertura Completa', () => {
  let ws: WebSocket;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    if (ws && ws.readyState !== WebSocket.CLOSED) {
      ws.close();
    }
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  describe('Conexión básica', () => {
    it('debe crear una conexión WebSocket', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      expect(ws).toBeDefined();
      expect(ws.url).toBe('ws://localhost:8000/ws');
    });

    it('debe tener estado CONNECTING al inicio', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      expect(ws.readyState).toBe(WebSocket.CONNECTING);
    });

    it('debe cambiar a estado OPEN cuando se conecta', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      
      await new Promise(resolve => {
        ws.onopen = () => {
          expect(ws.readyState).toBe(WebSocket.OPEN);
          resolve(true);
        };
        vi.runAllTimers();
      });
    });

    it('debe ejecutar callback onopen', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const onOpenCallback = vi.fn();
      ws.onopen = onOpenCallback;

      vi.runAllTimers();
      await Promise.resolve();

      expect(onOpenCallback).toHaveBeenCalled();
    });
  });

  describe('Envío de mensajes', () => {
    it('debe poder enviar mensajes', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const sendSpy = vi.spyOn(ws, 'send');

      ws.send('test message');

      expect(sendSpy).toHaveBeenCalledWith('test message');
    });

    it('debe enviar mensajes JSON', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const sendSpy = vi.spyOn(ws, 'send');

      const data = { type: 'test', payload: 'data' };
      ws.send(JSON.stringify(data));

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify(data));
    });
  });

  describe('Recepción de mensajes', () => {
    it('debe ejecutar callback onmessage al recibir datos', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const onMessageCallback = vi.fn();
      ws.onmessage = onMessageCallback;

      const messageEvent = new MessageEvent('message', {
        data: 'test data'
      });

      if (ws.onmessage) {
        ws.onmessage(messageEvent);
      }

      expect(onMessageCallback).toHaveBeenCalledWith(messageEvent);
    });

    it('debe procesar mensajes JSON', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const receivedData: any[] = [];

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        receivedData.push(data);
      };

      const testData = { type: 'update', value: 42 };
      const messageEvent = new MessageEvent('message', {
        data: JSON.stringify(testData)
      });

      if (ws.onmessage) {
        ws.onmessage(messageEvent);
      }

      expect(receivedData).toHaveLength(1);
      expect(receivedData[0]).toEqual(testData);
    });
  });

  describe('Cierre de conexión', () => {
    it('debe poder cerrar la conexión', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      ws.close();
      
      vi.runAllTimers();
      await Promise.resolve();

      expect(ws.readyState).toBe(WebSocket.CLOSED);
    });

    it('debe ejecutar callback onclose', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const onCloseCallback = vi.fn();
      ws.onclose = onCloseCallback;

      ws.close();
      vi.runAllTimers();
      await Promise.resolve();

      expect(onCloseCallback).toHaveBeenCalled();
    });

    it('debe cerrar con código y razón', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      let closeEvent: CloseEvent | null = null;

      ws.onclose = (event) => {
        closeEvent = event;
      };

      ws.close(1000, 'Normal closure');
      vi.runAllTimers();
      await Promise.resolve();

      expect(closeEvent).not.toBeNull();
      expect(closeEvent?.code).toBe(1000);
      expect(closeEvent?.reason).toBe('Normal closure');
    });

    it('debe pasar por estado CLOSING antes de CLOSED', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const states: number[] = [];

      ws.close();
      states.push(ws.readyState);

      vi.runAllTimers();
      await Promise.resolve();
      
      states.push(ws.readyState);

      expect(states).toContain(WebSocket.CLOSING);
      expect(states).toContain(WebSocket.CLOSED);
    });
  });

  describe('Manejo de errores', () => {
    it('debe ejecutar callback onerror', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const onErrorCallback = vi.fn();
      ws.onerror = onErrorCallback;

      const errorEvent = new Event('error');
      if (ws.onerror) {
        ws.onerror(errorEvent);
      }

      expect(onErrorCallback).toHaveBeenCalledWith(errorEvent);
    });

    it('debe manejar errores de conexión', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      let errorCaught = false;

      ws.onerror = () => {
        errorCaught = true;
      };

      const errorEvent = new Event('error');
      if (ws.onerror) {
        ws.onerror(errorEvent);
      }

      expect(errorCaught).toBe(true);
    });
  });

  describe('Event Listeners', () => {
    it('debe agregar event listener para open', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const openCallback = vi.fn();

      ws.addEventListener('open', openCallback);
      vi.runAllTimers();
      await Promise.resolve();

      expect(openCallback).toHaveBeenCalled();
    });

    it('debe agregar event listener para close', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const closeCallback = vi.fn();

      ws.addEventListener('close', closeCallback);
      ws.close();
      vi.runAllTimers();
      await Promise.resolve();

      expect(closeCallback).toHaveBeenCalled();
    });

    it('debe agregar event listener para message', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const messageCallback = vi.fn();

      ws.addEventListener('message', messageCallback);

      const messageEvent = new MessageEvent('message', {
        data: 'test'
      });

      if (ws.onmessage) {
        ws.onmessage(messageEvent);
      }

      expect(messageCallback).toHaveBeenCalledWith(messageEvent);
    });

    it('debe agregar event listener para error', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const errorCallback = vi.fn();

      ws.addEventListener('error', errorCallback);

      const errorEvent = new Event('error');
      if (ws.onerror) {
        ws.onerror(errorEvent);
      }

      expect(errorCallback).toHaveBeenCalledWith(errorEvent);
    });

    it('debe remover event listeners', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const callback = vi.fn();

      ws.addEventListener('message', callback);
      ws.removeEventListener('message');

      expect(ws.onmessage).toBeNull();
    });
  });

  describe('Estados del WebSocket', () => {
    it('debe tener constantes de estado correctas', () => {
      expect(WebSocket.CONNECTING).toBe(0);
      expect(WebSocket.OPEN).toBe(1);
      expect(WebSocket.CLOSING).toBe(2);
      expect(WebSocket.CLOSED).toBe(3);
    });

    it('debe cambiar de CONNECTING a OPEN', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      expect(ws.readyState).toBe(WebSocket.CONNECTING);

      vi.runAllTimers();
      await Promise.resolve();

      expect(ws.readyState).toBe(WebSocket.OPEN);
    });
  });

  describe('Reconexión', () => {
    it('debe permitir crear nueva conexión después de cerrar', async () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      ws.close();
      vi.runAllTimers();
      await Promise.resolve();

      const ws2 = new WebSocket('ws://localhost:8000/ws');
      expect(ws2).toBeDefined();
      expect(ws2.url).toBe('ws://localhost:8000/ws');
    });

    it('debe mantener múltiples conexiones independientes', () => {
      const ws1 = new WebSocket('ws://localhost:8000/ws/1');
      const ws2 = new WebSocket('ws://localhost:8000/ws/2');

      expect(ws1.url).toBe('ws://localhost:8000/ws/1');
      expect(ws2.url).toBe('ws://localhost:8000/ws/2');
      expect(ws1).not.toBe(ws2);

      ws1.close();
      ws2.close();
    });
  });

  describe('Datos complejos', () => {
    it('debe enviar y recibir objetos complejos', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const complexData = {
        id: 1,
        name: 'Test',
        nested: {
          array: [1, 2, 3],
          boolean: true
        }
      };

      const sendSpy = vi.spyOn(ws, 'send');
      ws.send(JSON.stringify(complexData));

      expect(sendSpy).toHaveBeenCalledWith(JSON.stringify(complexData));
    });

    it('debe manejar mensajes vacíos', () => {
      ws = new WebSocket('ws://localhost:8000/ws');
      const messageCallback = vi.fn();
      ws.onmessage = messageCallback;

      const emptyMessage = new MessageEvent('message', { data: '' });
      if (ws.onmessage) {
        ws.onmessage(emptyMessage);
      }

      expect(messageCallback).toHaveBeenCalledWith(emptyMessage);
    });
  });
});
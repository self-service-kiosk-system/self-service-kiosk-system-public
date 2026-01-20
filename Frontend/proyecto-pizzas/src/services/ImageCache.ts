// ============================================================================
// SERVICIO CENTRALIZADO DE CACHÉ DE IMÁGENES
// Reduce drásticamente el egress de Supabase almacenando imágenes localmente
// Usa Cache API del navegador + gestión de memoria para blob URLs
// ============================================================================

const IMAGE_CACHE_NAME = 'supabase-images-v1';
const MAX_BLOB_CACHE_SIZE = 100; // Máximo de blob URLs en memoria
const MAX_ACCESS_ORDER_SIZE = 150; // Límite para accessOrder

// Caché de blobs en memoria con orden de acceso (LRU)
const blobCache = new Map<string, string>();
const accessOrder: string[] = [];

/**
 * Limpia blob URLs antiguos cuando se excede el límite
 */
const cleanupOldBlobs = () => {
  // Agregar safeguard para evitar loops infinitos
  let iterations = 0;
  const maxIterations = blobCache.size + 10; // Safeguard
  
  while (blobCache.size > MAX_BLOB_CACHE_SIZE && iterations < maxIterations) {
  // Obtener la primera clave directamente del blobCache para garantizar consistencia
  const firstKey = blobCache.keys().next().value;
  
  if (firstKey !== undefined) {
    const blobUrl = blobCache.get(firstKey)!;
    URL.revokeObjectURL(blobUrl);
    blobCache.delete(firstKey);
    
    // Sincronizar accessOrder
    const idx = accessOrder.indexOf(firstKey);
    if (idx !== -1) {
      accessOrder.splice(idx, 1);
    }
  }
  
  iterations++;
}
  
  // Safeguard final - si aún excede, limpiar los más antiguos del Map
  if (blobCache.size > MAX_BLOB_CACHE_SIZE) {
    const keysToDelete = Array.from(blobCache.keys()).slice(0, blobCache.size - MAX_BLOB_CACHE_SIZE);
    keysToDelete.forEach(key => {
      const blobUrl = blobCache.get(key);
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      blobCache.delete(key);
    });
  }
};

/**
 * Limpia accessOrder si crece demasiado
 */
const cleanupAccessOrder = () => {
  if (accessOrder.length > MAX_ACCESS_ORDER_SIZE) {
    // Mantener solo las últimas MAX_BLOB_CACHE_SIZE entradas
    const toKeep = accessOrder.slice(-MAX_BLOB_CACHE_SIZE);
    accessOrder.length = 0;
    accessOrder.push(...toKeep);
  }
};

/**
 * Registra acceso a una URL para el algoritmo LRU
 */
const recordAccess = (src: string) => {
  const index = accessOrder.indexOf(src);
  if (index > -1) {
    accessOrder.splice(index, 1);
  }
  accessOrder.push(src);
  
  // Limpiar accessOrder periódicamente
  cleanupAccessOrder();
};

/**
 * Precarga y cachea una imagen
 * @param src URL de la imagen
 * @returns URL del blob cacheado o URL original como fallback
 */
export const preloadAndCacheImage = async (src: string): Promise<string> => {
  if (!src) return '';
  
  // Si ya tenemos un blob URL en memoria, usarlo
  if (blobCache.has(src)) {
    recordAccess(src);
    return blobCache.get(src)!;
  }
  
  try {
    // Intentar obtener de Cache API primero
    const cache = await caches.open(IMAGE_CACHE_NAME);
    const cachedResponse = await cache.match(src);
    
    if (cachedResponse) {
      // ¡Imagen ya está en caché local! No descarga de Supabase
      const blob = await cachedResponse.blob();
      const blobUrl = URL.createObjectURL(blob);
      
      // Limpiar blobs antiguos si es necesario
      cleanupOldBlobs();
      
      blobCache.set(src, blobUrl);
      recordAccess(src);
      return blobUrl;
    }
    
    // No está en caché, descargar y guardar
    const response = await fetch(src, { 
      mode: 'cors',
      credentials: 'omit'
    });
    
    if (response.ok) {
      // Clonar response para guardarlo en caché
      const responseClone = response.clone();
      await cache.put(src, responseClone);
      
      // Crear blob URL para uso inmediato
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      
      // Limpiar blobs antiguos si es necesario
      cleanupOldBlobs();
      
      blobCache.set(src, blobUrl);
      recordAccess(src);
      return blobUrl;
    }
  } catch (error) {
    console.warn('Error cacheando imagen:', error);
  }
  
  // Fallback: usar URL original
  return src;
};

/**
 * Revoca un blob URL específico (para cleanup en unmount)
 */
export const revokeBlobUrl = (src: string) => {
  if (blobCache.has(src)) {
    const blobUrl = blobCache.get(src)!;
    URL.revokeObjectURL(blobUrl);
    blobCache.delete(src);
    
    const index = accessOrder.indexOf(src);
    if (index > -1) {
      accessOrder.splice(index, 1);
    }
  }
};

/**
 * Limpia todo el caché de blobs (útil para logout o limpieza manual)
 */
export const clearBlobCache = () => {
  blobCache.forEach((blobUrl) => {
    URL.revokeObjectURL(blobUrl);
  });
  blobCache.clear();
  accessOrder.length = 0;
};

/**
 * Limpia el caché persistente del navegador
 */
export const clearPersistentCache = async () => {
  try {
    await caches.delete(IMAGE_CACHE_NAME);
    clearBlobCache();
  } catch (error) {
    console.warn('Error limpiando caché persistente:', error);
  }
};
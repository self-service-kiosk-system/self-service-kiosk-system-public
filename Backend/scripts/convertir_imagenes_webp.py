"""
Script para convertir imágenes de productos a formato WebP.
Funciona tanto con imágenes locales (filesystem) como con Supabase Storage.
"""
import os
import sys
import argparse
from pathlib import Path
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PIL import Image
from dotenv import load_dotenv
from sqlalchemy.orm import Session

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.config.database import SessionLocal
from app.models.models import Producto

CALIDAD_WEBP = 85
USE_LOCAL = os.getenv("USE_LOCAL_DB", "false").lower() == "true"

FRONTEND_PATH = Path(__file__).parent.parent.parent / "Frontend" / "proyecto-pizzas" / "public"
IMAGENES_PATH = FRONTEND_PATH / "imagenes"


def get_supabase_client():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL y SERVICE_ROLE_KEY son requeridos para modo nube")
    return create_client(url, key)


def convertir_a_webp(imagen_bytes: bytes, calidad: int = CALIDAD_WEBP) -> tuple[BytesIO, int, int]:
    tamaño_original = len(imagen_bytes)
    img = Image.open(BytesIO(imagen_bytes))
    
    if img.mode in ('RGBA', 'LA', 'P'):
        fondo = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode == 'RGBA':
            fondo.paste(img, mask=img.split()[-1])
        else:
            fondo.paste(img)
        img = fondo
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    output = BytesIO()
    img.save(output, format='WEBP', quality=calidad, method=6)
    output.seek(0)
    
    tamaño_nuevo = len(output.getvalue())
    output.seek(0)
    
    return output, tamaño_original, tamaño_nuevo


def extraer_nombre_archivo(url: str) -> str | None:
    """Extrae el nombre del archivo de una URL, limpiando query strings"""
    if not url:
        return None
    
    url_limpia = url.split('?')[0]
    
    if '/imagenes/' in url_limpia:
        return url_limpia.split('/imagenes/')[-1]
    
    return url_limpia.split('/')[-1]


def extraer_path_supabase(imagen_url: str, bucket_name: str) -> str | None:
    """
    Extrae el path completo del archivo en Supabase Storage.
    Ej: 'productos/0568a89d-570a-4f6a-bf2d-713f8fd5537c.jpg'
    """
    if not imagen_url:
        return None
    
    # Limpiar query string
    url_limpia = imagen_url.split('?')[0]
    
    # Buscar el path después del bucket
    # Formato: .../storage/v1/object/public/img/productos/uuid.jpg
    marcador = f"/storage/v1/object/public/{bucket_name}/"
    if marcador in url_limpia:
        return url_limpia.split(marcador)[-1]
    
    # Alternativa: buscar después de /img/
    marcador_alt = f"/{bucket_name}/"
    if marcador_alt in url_limpia:
        partes = url_limpia.split(marcador_alt)
        if len(partes) > 1:
            return partes[-1]
    
    return None


def procesar_local(db: Session, dry_run: bool, limit: int | None, calidad: int) -> dict:
    stats = {"convertidos": 0, "ya_webp": 0, "errores": 0, "ahorro_bytes": 0}
    
    print(f"\nCarpeta de imágenes: {IMAGENES_PATH}")
    
    if not IMAGENES_PATH.exists():
        print(f"La carpeta {IMAGENES_PATH} no existe")
        return stats
    
    archivos_disponibles = {f.name for f in IMAGENES_PATH.glob("*.*")}
    print(f" Archivos encontrados: {len(archivos_disponibles)}")
    
    query = db.query(Producto).filter(Producto.imagen_url.isnot(None))
    if limit:
        query = query.limit(limit)
    productos = query.all()
    
    print(f"\nEncontrados {len(productos)} productos con imagen\n")
    
    for idx, producto in enumerate(productos, 1):
        nombre_archivo = extraer_nombre_archivo(producto.imagen_url)
        
        if not nombre_archivo:
            print(f"  [{idx}/{len(productos)}] {producto.nombre}: URL inválida")
            stats["errores"] += 1
            continue
        
        if nombre_archivo.lower().endswith('.webp'):
            print(f"[{idx}/{len(productos)}] {producto.nombre}: Ya está en WebP")
            stats["ya_webp"] += 1
            continue
        
        if nombre_archivo not in archivos_disponibles:
            print(f" [{idx}/{len(productos)}] {producto.nombre}: Archivo no encontrado: {nombre_archivo}")
            stats["errores"] += 1
            continue
        
        archivo_path = IMAGENES_PATH / nombre_archivo
        
        try:
            if dry_run:
                print(f" [{idx}/{len(productos)}] {producto.nombre}: Se convertiría {nombre_archivo}")
                stats["convertidos"] += 1
                continue
            
            with open(archivo_path, 'rb') as f:
                imagen_bytes = f.read()
            
            webp_bytes, tam_original, tam_nuevo = convertir_a_webp(imagen_bytes, calidad)
            
            nuevo_nombre = nombre_archivo.rsplit('.', 1)[0] + '.webp'
            nuevo_path = IMAGENES_PATH / nuevo_nombre
            
            with open(nuevo_path, 'wb') as f:
                f.write(webp_bytes.read())
            
            url_base = producto.imagen_url.split('?')[0]
            nueva_url = url_base.rsplit('.', 1)[0] + '.webp'
            producto.imagen_url = nueva_url
            
            if archivo_path.exists():
                archivo_path.unlink()
            
            ahorro = tam_original - tam_nuevo
            stats["ahorro_bytes"] += ahorro
            stats["convertidos"] += 1
            
            print(f" [{idx}/{len(productos)}] {producto.nombre}: {nombre_archivo} → {nuevo_nombre} "
                  f"({tam_original//1024}KB → {tam_nuevo//1024}KB, -{ahorro//1024}KB)")
            
        except Exception as e:
            print(f" [{idx}/{len(productos)}] {producto.nombre}: Error - {e}")
            stats["errores"] += 1
    
    if not dry_run:
        db.commit()
    
    return stats


def procesar_supabase(db: Session, dry_run: bool, limit: int | None, calidad: int) -> dict:
    stats = {"convertidos": 0, "ya_webp": 0, "errores": 0, "ahorro_bytes": 0}
    
    supabase = get_supabase_client()
    bucket_name = os.getenv("SUPABASE_BUCKET", "img")
    supabase_url = os.getenv("SUPABASE_URL", "")
    
    print(f"\n Bucket: {bucket_name}")
    print(f" Supabase URL: {supabase_url}")
    
    query = db.query(Producto).filter(Producto.imagen_url.isnot(None))
    if limit:
        query = query.limit(limit)
    productos = query.all()
    
    print(f"\n Encontrados {len(productos)} productos con imagen\n")
    
    for idx, producto in enumerate(productos, 1):
        imagen_url = producto.imagen_url or ""
        
        # Verificar que sea URL de Supabase
        if supabase_url not in imagen_url:
            print(f"  [{idx}/{len(productos)}] {producto.nombre}: No es imagen de Supabase")
            stats["errores"] += 1
            continue
        
        # Limpiar URL
        imagen_url_limpia = imagen_url.split('?')[0]
        
        # Ya es WebP
        if imagen_url_limpia.lower().endswith('.webp'):
            print(f" [{idx}/{len(productos)}] {producto.nombre}: Ya está en WebP")
            stats["ya_webp"] += 1
            continue
        
        # Extraer path en storage (ej: productos/uuid.jpg)
        file_path = extraer_path_supabase(imagen_url, bucket_name)
        
        if not file_path:
            print(f"  [{idx}/{len(productos)}] {producto.nombre}: No se pudo extraer path de: {imagen_url[:80]}...")
            stats["errores"] += 1
            continue
        
        try:
            if dry_run:
                nuevo_path = file_path.rsplit('.', 1)[0] + '.webp'
                print(f" [{idx}/{len(productos)}] {producto.nombre}: {file_path} → {nuevo_path}")
                stats["convertidos"] += 1
                continue
            
            # Descargar imagen original
            print(f" [{idx}/{len(productos)}] {producto.nombre}: Descargando {file_path}...")
            response = supabase.storage.from_(bucket_name).download(file_path)
            
            # Convertir a WebP
            webp_bytes, tam_original, tam_nuevo = convertir_a_webp(response, calidad)
            
            # Nuevo path (misma carpeta, extensión .webp)
            nuevo_path = file_path.rsplit('.', 1)[0] + '.webp'
            
            # Subir WebP
            print(f"⬆  [{idx}/{len(productos)}] {producto.nombre}: Subiendo {nuevo_path}...")
            webp_content = webp_bytes.read()
            supabase.storage.from_(bucket_name).upload(
                nuevo_path,
                webp_content,
                {"content-type": "image/webp", "upsert": "true"}
            )
            
            # Obtener nueva URL pública
            nueva_url = supabase.storage.from_(bucket_name).get_public_url(nuevo_path)
            producto.imagen_url = nueva_url
            
            # Eliminar imagen original
            try:
                supabase.storage.from_(bucket_name).remove([file_path])
                print(f"  [{idx}/{len(productos)}] Eliminado original: {file_path}")
            except Exception as e:
                print(f" [{idx}/{len(productos)}] No se pudo eliminar original: {e}")
            
            ahorro = tam_original - tam_nuevo
            stats["ahorro_bytes"] += ahorro
            stats["convertidos"] += 1
            
            print(f"  [{idx}/{len(productos)}] {producto.nombre}: "
                  f"({tam_original//1024}KB → {tam_nuevo//1024}KB, -{ahorro//1024}KB)")
            
        except Exception as e:
            print(f"  [{idx}/{len(productos)}] {producto.nombre}: Error - {e}")
            stats["errores"] += 1
    
    if not dry_run:
        db.commit()
        print("\n Cambios guardados en base de datos")
    
    return stats


def formatear_bytes(bytes_val: int) -> str:
    for unidad in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unidad}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def main():
    parser = argparse.ArgumentParser(description='Convertir imágenes de productos a WebP')
    parser.add_argument('--dry-run', action='store_true', help='Solo mostrar qué se haría')
    parser.add_argument('--limit', type=int, help='Limitar a N productos')
    parser.add_argument('--quality', type=int, default=CALIDAD_WEBP, help=f'Calidad WebP (default: {CALIDAD_WEBP})')
    parser.add_argument('--force-cloud', action='store_true', help='Forzar modo Supabase (ignorar USE_LOCAL_DB)')
    args = parser.parse_args()
    
    # Permitir forzar modo nube
    use_local = USE_LOCAL and not args.force_cloud
    modo = "LOCAL (Filesystem)" if use_local else "NUBE (Supabase)"
    
    print("\n" + "═" * 60)
    print("  CONVERTIDOR DE IMÁGENES A WEBP")
    print("═" * 60)
    print(f"  Modo: {modo}")
    print(f"  Calidad WebP: {args.quality}%")
    if args.limit:
        print(f"  Límite: {args.limit} productos")
    if args.force_cloud:
        print(f"    Forzando modo NUBE (--force-cloud)")
    print("═" * 60)
    
    if args.dry_run:
        print("\n  MODO DRY-RUN: No se ejecutarán cambios reales")
    
    if not use_local and not args.dry_run:
        confirm = input("\n  ATENCIÓN: Vas a modificar imágenes en PRODUCCIÓN. ¿Continuar? (SI/NO): ")
        if confirm.strip().upper() != "SI":
            print(" Operación cancelada")
            return
    
    db = SessionLocal()
    try:
        if use_local:
            stats = procesar_local(db, args.dry_run, args.limit, args.quality)
        else:
            stats = procesar_supabase(db, args.dry_run, args.limit, args.quality)
        
        print("\n" + "═" * 60)
        print(" RESUMEN")
        print("═" * 60)
        print(f"   Convertidos:     {stats['convertidos']}")
        print(f"    Ya eran WebP:    {stats['ya_webp']}")
        print(f"   Errores:         {stats['errores']}")
        print(f"   Espacio ahorrado: {formatear_bytes(stats['ahorro_bytes'])}")
        print("═" * 60)
        
        if args.dry_run:
            print("\nℹ  Ejecuta sin --dry-run para aplicar los cambios")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
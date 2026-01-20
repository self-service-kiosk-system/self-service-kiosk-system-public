import os
import sys
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from supabase import create_client
from dotenv import load_dotenv

# Agregar el path del Backend para imports relativos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.models.models import Producto, Categoria, Local, Usuario, DispositivoAutorizado

# Cargar variables de entorno desde .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Usar variables del .env
LOCAL_DB_URL = os.getenv("DATABASE_LOCAL_URL")
SUPABASE_DB_URL = os.getenv("DATABASE_NUBE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SERVICE_ROLE_KEY")

# Conexiones SQLAlchemy
local_engine = create_engine(LOCAL_DB_URL)
LocalSession = sessionmaker(bind=local_engine)
supabase_engine = create_engine(SUPABASE_DB_URL)
SupabaseSession = sessionmaker(bind=supabase_engine)

# Supabase Storage
supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)


def traer_bdd():
    with LocalSession() as local_db, SupabaseSession() as supa_db:
        # Migrar locales
        locales = supa_db.query(Local).all()
        for loc in locales:
            existe = local_db.query(Local).filter_by(id=loc.id).first()
            if not existe:
                nuevo_local = Local(
                    id=loc.id,
                    nombre=loc.nombre,
                    direccion=loc.direccion,
                    telefono=loc.telefono,
                    email=loc.email,
                    timezone=getattr(loc, 'timezone', 'America/Argentina/Buenos_Aires'),
                    esta_activo=loc.esta_activo
                )
                local_db.add(nuevo_local)
            else:
                existe.nombre = loc.nombre
                existe.direccion = loc.direccion
                existe.telefono = loc.telefono
                existe.email = loc.email
                existe.timezone = getattr(loc, 'timezone', 'America/Argentina/Buenos_Aires')
                existe.esta_activo = loc.esta_activo
        local_db.commit()

        # Migrar categorías
        categorias = supa_db.query(Categoria).all()
        for cat in categorias:
            existe = local_db.query(Categoria).filter_by(id=cat.id).first()
            if not existe:
                nueva_cat = Categoria(
                    id=cat.id,
                    nombre=cat.nombre,
                    local_id=cat.local_id,
                    descripcion=getattr(cat, 'descripcion', None),
                    orden=getattr(cat, 'orden', 0),
                    esta_activo=cat.esta_activo
                )
                local_db.add(nueva_cat)
            else:
                existe.nombre = cat.nombre
                existe.local_id = cat.local_id
                existe.descripcion = getattr(cat, 'descripcion', None)
                existe.orden = getattr(cat, 'orden', 0)
                existe.esta_activo = cat.esta_activo
        local_db.commit()

        # Migrar productos
        productos = supa_db.query(Producto).all()
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        imagenes_dir = os.path.join(base_dir, 'Frontend', 'proyecto-pizzas', 'public', 'imagenes')
        os.makedirs(imagenes_dir, exist_ok=True)
        for prod in productos:
            nueva_url = prod.imagen_url
            if nueva_url and SUPABASE_URL in nueva_url:
                nombre_archivo = nueva_url.split("/")[-1].split("?")[0]
                ruta_local = os.path.join(imagenes_dir, nombre_archivo)
                if not os.path.isfile(ruta_local):
                    try:
                        r = requests.get(nueva_url)
                        if r.status_code == 200:
                            with open(ruta_local, "wb") as f:
                                f.write(r.content)
                            print(f"[INFO] Imagen descargada: {ruta_local}")
                        else:
                            print(f"[ERROR] No se pudo descargar imagen: {nueva_url}")
                    except Exception as e:
                        print(f"[ERROR] Fallo al descargar imagen {nueva_url}: {e}")
                nueva_url = f"http://localhost:8000/imagenes/{nombre_archivo}"

            existe = local_db.query(Producto).filter_by(id=prod.id).first()
            if not existe:
                nuevo = Producto(
                    id=prod.id,
                    local_id=prod.local_id,
                    categoria_id=prod.categoria_id,
                    nombre=prod.nombre,
                    descripcion=prod.descripcion,
                    precio=prod.precio,
                    disponible=prod.disponible,
                    destacado=prod.destacado,
                    imagen_url=nueva_url
                )
                local_db.add(nuevo)
            else:
                existe.local_id = prod.local_id
                existe.categoria_id = prod.categoria_id
                existe.nombre = prod.nombre
                existe.descripcion = prod.descripcion
                existe.precio = prod.precio
                existe.disponible = prod.disponible
                existe.destacado = prod.destacado
                existe.imagen_url = nueva_url
        local_db.commit()

        # Migrar usuarios
        usuarios = supa_db.query(Usuario).all()
        for user in usuarios:
            existe = local_db.query(Usuario).filter_by(id=user.id).first()
            if not existe:
                nuevo_user = Usuario(
                    id=user.id,
                    local_id=user.local_id,
                    nombre=user.nombre,
                    email=user.email,
                    password_hash=user.password_hash,
                    rol=user.rol,
                    esta_activo=user.esta_activo,
                    fecha_creacion=user.fecha_creacion,
                    ultimo_acceso=user.ultimo_acceso
                )
                local_db.add(nuevo_user)
            else:
                existe.local_id = user.local_id
                existe.nombre = user.nombre
                existe.email = user.email
                existe.password_hash = user.password_hash
                existe.rol = user.rol
                existe.esta_activo = user.esta_activo
                existe.fecha_creacion = user.fecha_creacion
                existe.ultimo_acceso = user.ultimo_acceso
        local_db.commit()

        # Migrar dispositivos autorizados
        dispositivos = supa_db.query(DispositivoAutorizado).all()
        for disp in dispositivos:
            existe = local_db.query(DispositivoAutorizado).filter_by(id=disp.id).first()
            if not existe:
                nuevo_disp = DispositivoAutorizado(
                    id=disp.id,
                    local_id=disp.local_id,
                    device_id=disp.device_id,
                    secret_key=disp.secret_key,
                    nombre=disp.nombre,
                    tipo=disp.tipo,
                    esta_activo=disp.esta_activo,
                    fecha_creacion=disp.fecha_creacion,
                    ultimo_acceso=disp.ultimo_acceso
                )
                local_db.add(nuevo_disp)
            else:
                existe.local_id = disp.local_id
                existe.device_id = disp.device_id
                existe.secret_key = disp.secret_key
                existe.nombre = disp.nombre
                existe.tipo = disp.tipo
                existe.esta_activo = disp.esta_activo
                existe.fecha_creacion = disp.fecha_creacion
                existe.ultimo_acceso = disp.ultimo_acceso
        local_db.commit()
    print("Migración inversa completada.")

if __name__ == "__main__":
    traer_bdd()

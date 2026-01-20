from fastapi import UploadFile, HTTPException, status
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import jwt
import os
from uuid import uuid4
from pathlib import Path
from pydantic import BaseModel
from app.config.database import SessionLocal
from app.models.models import Producto, Categoria, Local, Usuario
from passlib.context import CryptContext
from app.api.websocket.manager import manager


class AdminService:
    def __init__(self):
        self.admin_user = os.getenv("ADMIN_USER")
        self.admin_password = os.getenv("ADMIN_PASSWORD")
        self.secret_key = os.getenv("SECRET_JWT")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        
        use_local = os.getenv("USE_LOCAL_DB", "false").lower() == "true"
        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.service_role_key = os.getenv("SERVICE_ROLE_KEY")
        self.usar_supabase_storage = not use_local and bool(self.supabase_url and self.service_role_key)
        
        if self.usar_supabase_storage:
            from supabase import create_client
            self.supabase = create_client(self.supabase_url, self.service_role_key)
        
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # ========================================================================
    # AUTENTICACIÓN
    # ========================================================================

    def autenticar_admin(self, usuario: str, contrasena: str) -> str:
        if usuario == self.admin_user and contrasena == self.admin_password:
            return self.crear_token(usuario)
        
        db = SessionLocal()
        try:
            user = db.query(Usuario).filter(Usuario.nombre == usuario).first()
            
            if user and user.esta_activo:
                if self.pwd_context.verify(contrasena, user.password_hash):
                    return self.crear_token(usuario)
        finally:
            db.close()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    def crear_token(self, usuario: str) -> str:
        payload = {
            "sub": usuario,
            "exp": datetime.utcnow() + timedelta(hours=8)
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verificar_token(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return bool(payload.get("sub"))
        except:
            return False
        
    
    # ========================================================================
    # GESTIÓN DE IMÁGENES (SUPABASE O LOCAL)
    # ========================================================================

    async def subir_imagen(self, imagen: UploadFile) -> str:
        if self.usar_supabase_storage:
            return await self._subir_imagen_supabase(imagen)
        else:
            return await self._guardar_imagen_local(imagen)

    async def _subir_imagen_supabase(self, imagen: UploadFile) -> str:
        nombre_archivo = f"productos/{uuid4()}.{imagen.filename.split('.')[-1]}"
        contenido = await imagen.read()
        
        resultado = self.supabase.storage.from_("img").upload(
            nombre_archivo,
            contenido,
            {"content-type": imagen.content_type}
        )
        
        url_publica = self.supabase.storage.from_("img").get_public_url(nombre_archivo)
        return url_publica

    async def _guardar_imagen_local(self, imagen: UploadFile) -> str:
        from pathlib import Path
        import os
        
        backend_dir = Path(__file__).resolve().parent.parent.parent
        proyecto_root = backend_dir.parent
        carpeta_destino = proyecto_root / "Frontend" / "proyecto-pizzas" / "public" / "imagenes"
        
        carpeta_destino.mkdir(parents=True, exist_ok=True)
        
        extension = imagen.filename.split(".")[-1]
        nombre_archivo = f"producto_{os.urandom(8).hex()}.{extension}"
        ruta_completa = carpeta_destino / nombre_archivo
        
        with open(ruta_completa, "wb") as archivo:
            contenido = await imagen.read()
            archivo.write(contenido)
        
        return f"{self.backend_url}/imagenes/{nombre_archivo}"

    async def eliminar_imagen(self, imagen_url: str) -> bool:
        """Elimina una imagen del storage (Supabase o local)"""
        if not imagen_url:
            return False
        
        try:
            if self.usar_supabase_storage:
                return await self._eliminar_imagen_supabase(imagen_url)
            else:
                return await self._eliminar_imagen_local(imagen_url)
        except Exception as e:
            print(f"Error eliminando imagen: {e}")
            return False

    async def _eliminar_imagen_supabase(self, imagen_url: str) -> bool:
        """Elimina una imagen del bucket de Supabase Storage"""
        try:
            # Extraer el path del archivo desde la URL pública
            if "/storage/v1/object/public/img/" in imagen_url:
                file_path = imagen_url.split("/storage/v1/object/public/img/")[-1]
            elif "/img/" in imagen_url:
                # Formato alternativo
                file_path = imagen_url.split("/img/")[-1]
            else:
                print(f"No se pudo extraer el path de la imagen: {imagen_url}")
                return False
            
            # Eliminar del bucket "img"
            resultado = self.supabase.storage.from_("img").remove([file_path])
            print(f"Imagen eliminada de Supabase: {file_path}")
            return True
        except Exception as e:
            print(f"Error eliminando imagen de Supabase: {e}")
            return False

    async def _eliminar_imagen_local(self, imagen_url: str) -> bool:
        """Elimina una imagen del almacenamiento local"""
        try:
            from pathlib import Path
            backend_dir = Path(__file__).resolve().parent.parent.parent
            proyecto_root = backend_dir.parent
            
            # Extraer nombre del archivo de la URL
            nombre_archivo = imagen_url.split("/")[-1]
            ruta_imagen = proyecto_root / "Frontend" / "proyecto-pizzas" / "public" / "imagenes" / nombre_archivo
            
            if ruta_imagen.exists():
                ruta_imagen.unlink()
                print(f"Imagen local eliminada: {nombre_archivo}")
                return True
            return False
        except Exception as e:
            print(f"Error eliminando imagen local: {e}")
            return False

    # ========================================================================
    # GESTIÓN DE PRODUCTOS (CON FILTRADO POR local_id)
    # ========================================================================

    async def obtener_productos(self, local_id: int) -> List[Dict]:
        with SessionLocal() as db:
            productos = db.query(Producto).filter(
                Producto.local_id == local_id
            ).all()
            
            return [
                {
                    "id": p.id,
                    "local_id": p.local_id,
                    "categoria_id": p.categoria_id,
                    "nombre": p.nombre,
                    "descripcion": p.descripcion,
                    "precio": float(p.precio),
                    "disponible": p.disponible,
                    "destacado": p.destacado,
                    "imagen_url": p.imagen_url,
                    "categorias": {
                        "id": p.categoria.id,
                        "nombre": p.categoria.nombre
                    } if p.categoria else None
                }
                for p in productos
            ]

    async def crear_producto(
        self, 
        local_id: int,
        datos: BaseModel, 
        imagen: Optional[UploadFile] = None
    ) -> Dict:
        with SessionLocal() as db:
            categoria = db.query(Categoria).filter(
                Categoria.id == datos.categoria_id,
                Categoria.local_id == local_id
            ).first()
            
            if not categoria:
                raise HTTPException(
                    status_code=400, 
                    detail="La categoría no pertenece a tu local"
                )
            
            imagen_url = None
            if imagen:
                imagen_url = await self.subir_imagen(imagen)
            
            nuevo_producto = Producto(
                local_id=local_id,
                categoria_id=datos.categoria_id,
                nombre=datos.nombre,
                descripcion=datos.descripcion,
                precio=datos.precio,
                disponible=datos.disponible,
                destacado=datos.destacado,
                imagen_url=imagen_url
            )
            
            db.add(nuevo_producto)
            db.commit()
            db.refresh(nuevo_producto)
            
            await manager.broadcast(
                evento="producto_creado",
                datos={
                    "id": nuevo_producto.id,
                    "local_id": nuevo_producto.local_id,
                    "categoria_id": nuevo_producto.categoria_id,
                    "nombre": nuevo_producto.nombre,
                    "descripcion": nuevo_producto.descripcion,
                    "precio": float(nuevo_producto.precio),
                    "disponible": nuevo_producto.disponible,
                    "destacado": nuevo_producto.destacado,
                    "imagen_url": nuevo_producto.imagen_url,
                    "categorias": {
                        "id": categoria.id,
                        "nombre": categoria.nombre
                    }
                },
                local_id=str(local_id)
            )
            
            return {
                "message": "Producto creado exitosamente",
                "id": nuevo_producto.id
            }

    async def actualizar_producto(
        self,
        producto_id: int,
        local_id: int,
        datos: BaseModel,
        imagen: Optional[UploadFile] = None
    ) -> Dict:
        with SessionLocal() as db:
            producto = db.query(Producto).filter(
                Producto.id == producto_id,
                Producto.local_id == local_id
            ).first()
            
            if not producto:
                raise HTTPException(
                    status_code=404, 
                    detail="Producto no encontrado o no tienes permiso"
                )
            
            if datos.categoria_id and datos.categoria_id != producto.categoria_id:
                categoria = db.query(Categoria).filter(
                    Categoria.id == datos.categoria_id,
                    Categoria.local_id == local_id
                ).first()
                
                if not categoria:
                    raise HTTPException(
                        status_code=400,
                        detail="La categoría no pertenece a tu local"
                    )
            
            if datos.nombre:
                producto.nombre = datos.nombre
            if datos.descripcion:
                producto.descripcion = datos.descripcion
            if datos.precio:
                producto.precio = datos.precio
            if datos.categoria_id:
                producto.categoria_id = datos.categoria_id
            if datos.disponible is not None:
                producto.disponible = datos.disponible
            if datos.destacado is not None:
                producto.destacado = datos.destacado
            
            if imagen:
                # Eliminar imagen anterior del storage (Supabase o local)
                if producto.imagen_url:
                    await self.eliminar_imagen(producto.imagen_url)
                
                producto.imagen_url = await self.subir_imagen(imagen)
            
            db.commit()
            db.refresh(producto)
            
            await manager.broadcast(
                evento="producto_actualizado",
                datos={
                    "id": producto.id,
                    "local_id": producto.local_id,
                    "categoria_id": producto.categoria_id,
                    "nombre": producto.nombre,
                    "descripcion": producto.descripcion,
                    "precio": float(producto.precio),
                    "disponible": producto.disponible,
                    "destacado": producto.destacado,
                    "imagen_url": producto.imagen_url,
                    "categorias": {
                        "id": producto.categoria.id,
                        "nombre": producto.categoria.nombre
                    } if producto.categoria else None
                },
                local_id=str(local_id)
            )
            
            return {"message": "Producto actualizado exitosamente"}

    async def eliminar_producto(self, producto_id: int, local_id: int) -> Dict:
        with SessionLocal() as db:
            producto = db.query(Producto).filter(
                Producto.id == producto_id,
                Producto.local_id == local_id
            ).first()
            
            if not producto:
                raise HTTPException(
                    status_code=404,
                    detail="Producto no encontrado o no tienes permiso"
                )
            
            # Eliminar imagen del storage (Supabase o local)
            if producto.imagen_url:
                await self.eliminar_imagen(producto.imagen_url)
            
            db.delete(producto)
            db.commit()
            
            await manager.broadcast(
                evento="producto_eliminado",
                datos={
                    "id": producto_id
                },
                local_id=str(local_id)
            )
            
            return {
                "mensaje": "Producto eliminado correctamente",
                "producto_id": producto_id
            }

    # ========================================================================
    # CATEGORÍAS (CON WEBSOCKET BROADCAST)
    # ========================================================================

    async def obtener_categorias(self, local_id: int) -> List[Dict]:
        with SessionLocal() as db:
            categorias = db.query(Categoria).filter(
                Categoria.local_id == local_id,
                Categoria.esta_activo == True
            ).order_by(Categoria.orden).all()
            
            return [
                {
                    "id": c.id,
                    "nombre": c.nombre,
                    "descripcion": c.descripcion,
                    "orden": c.orden
                }
                for c in categorias
            ]

    async def crear_categoria(self, local_id: int, nombre: str, descripcion: str = "") -> Dict:
        with SessionLocal() as db:
            existe = db.query(Categoria).filter(
                Categoria.local_id == local_id,
                Categoria.nombre == nombre
            ).first()
            
            if existe:
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe una categoría con ese nombre"
                )
            
            ultimo_orden = db.query(Categoria).filter(
                Categoria.local_id == local_id
            ).count()
            
            nueva_categoria = Categoria(
                local_id=local_id,
                nombre=nombre,
                descripcion=descripcion,
                orden=ultimo_orden + 1,
                esta_activo=True
            )
            
            db.add(nueva_categoria)
            db.commit()
            db.refresh(nueva_categoria)
            
            # Broadcast WebSocket
            await manager.broadcast(
                evento="categoria_creada",
                datos={
                    "id": nueva_categoria.id,
                    "nombre": nueva_categoria.nombre,
                    "descripcion": nueva_categoria.descripcion,
                    "orden": nueva_categoria.orden
                },
                local_id=str(local_id)
            )
            
            return {
                "message": "Categoría creada exitosamente",
                "id": nueva_categoria.id,
                "nombre": nueva_categoria.nombre
            }

    async def actualizar_categoria(self, local_id: int, categoria_id: int, nombre: str, descripcion: str = "") -> Dict:
        """Actualiza una categoría existente"""
        with SessionLocal() as db:
            categoria = db.query(Categoria).filter(
                Categoria.id == categoria_id,
                Categoria.local_id == local_id
            ).first()
            
            if not categoria:
                raise HTTPException(
                    status_code=404,
                    detail="Categoría no encontrada o no tienes permiso"
                )
            
            # Verificar que no exista otra categoría con el mismo nombre
            existe = db.query(Categoria).filter(
                Categoria.local_id == local_id,
                Categoria.nombre == nombre,
                Categoria.id != categoria_id
            ).first()
            
            if existe:
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe otra categoría con ese nombre"
                )
            
            categoria.nombre = nombre
            if descripcion is not None:
                categoria.descripcion = descripcion
            
            db.commit()
            db.refresh(categoria)
            
            await manager.broadcast(
                evento="categoria_actualizada",
                datos={
                    "id": categoria.id,
                    "nombre": categoria.nombre,
                    "descripcion": categoria.descripcion,
                    "orden": categoria.orden
                },
                local_id=str(local_id)
            )
            
            return {
                "message": "Categoría actualizada exitosamente",
                "id": categoria.id,
                "nombre": categoria.nombre
            }

    async def eliminar_categoria(self, local_id: int, categoria_id: int) -> Dict:
        """Elimina una categoría y todos sus productos asociados"""
        with SessionLocal() as db:
            categoria = db.query(Categoria).filter(
                Categoria.id == categoria_id,
                Categoria.local_id == local_id
            ).first()
            
            if not categoria:
                raise HTTPException(
                    status_code=404,
                    detail="Categoría no encontrada o no tienes permiso"
                )
            
            # Obtener productos asociados para eliminar sus imágenes
            productos = db.query(Producto).filter(
                Producto.categoria_id == categoria_id
            ).all()
            
            productos_eliminados = len(productos)
            
            # Eliminar imágenes de los productos
            for producto in productos:
                if producto.imagen_url:
                    await self.eliminar_imagen(producto.imagen_url)
            
            # Eliminar todos los productos de la categoría
            db.query(Producto).filter(
                Producto.categoria_id == categoria_id
            ).delete()
            
            # Eliminar la categoría
            db.delete(categoria)
            db.commit()
            
            await manager.broadcast(
                evento="categoria_eliminada",
                datos={"id": categoria_id, "productos_eliminados": productos_eliminados},
                local_id=str(local_id)
            )
            
            return {
                "mensaje": "Categoría eliminada correctamente",
                "categoria_id": categoria_id,
                "productos_eliminados": productos_eliminados
            }

    async def reordenar_categorias(self, local_id: int, orden_ids: List[int]) -> Dict:
        """Reordena las categorías según el nuevo orden de IDs"""
        with SessionLocal() as db:
            # Verificar que todas las categorías pertenecen al local
            categorias = db.query(Categoria).filter(
                Categoria.local_id == local_id,
                Categoria.id.in_(orden_ids)
            ).all()
            
            if len(categorias) != len(orden_ids):
                raise HTTPException(
                    status_code=400,
                    detail="Algunas categorías no existen o no tienes permiso"
                )
            
            # Actualizar el orden
            for nuevo_orden, categoria_id in enumerate(orden_ids, start=1):
                categoria = next((c for c in categorias if c.id == categoria_id), None)
                if categoria:
                    categoria.orden = nuevo_orden
            
            db.commit()
            
            await manager.broadcast(
                evento="categorias_reordenadas",
                datos={"orden": orden_ids},
                local_id=str(local_id)
            )
            
            return {
                "message": "Categorías reordenadas exitosamente",
                "orden": orden_ids
            }

    # ========================================================================
    # LOCALES (sin cambios)
    # ========================================================================

    async def obtener_locales(self, local_id: int) -> List[Dict]:
        """Obtiene solo el local del usuario autenticado"""
        with SessionLocal() as db:
            local = db.query(Local).filter(
                Local.id == local_id,
                Local.esta_activo == True
            ).first()
            
            if not local:
                return []
            
            return [
                {
                    "id": local.id,
                    "nombre": local.nombre,
                    "direccion": local.direccion,
                    "telefono": local.telefono
                }
            ]
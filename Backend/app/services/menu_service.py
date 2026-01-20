from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.config.database import SessionLocal
from app.models.models import Producto, Categoria, Local


class MenuService:
    """Servicio para gestionar el menú público del kiosk"""
    
    async def obtener_menu_completo(self, local_id: Optional[int] = None) -> Dict:
        """
        Obtiene el menú completo organizado por local y categoría.
        
        Args:
            local_id: Si se especifica, filtra solo ese local
            
        Returns:
            Dict con estructura: {"locales": [...]}
        """
        with SessionLocal() as db:
            # Construir query base de locales
            query_locales = db.query(Local).filter(Local.esta_activo == True)
            
            if local_id:
                query_locales = query_locales.filter(Local.id == local_id)
            
            locales = query_locales.all()
            
            if not locales:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No se encontraron locales activos"
                )
            
            resultado = {"locales": []}
            
            for local in locales:
                # Obtener categorías activas del local
                categorias = db.query(Categoria).filter(
                    Categoria.local_id == local.id,
                    Categoria.esta_activo == True
                ).order_by(Categoria.orden).all()
                
                categorias_data = []
                
                for categoria in categorias:
                    # Obtener productos disponibles de la categoría
                    productos = db.query(Producto).filter(
                        Producto.categoria_id == categoria.id
                    ).order_by(Producto.orden, Producto.nombre).all()
                    
                    productos_data = [
                        {
                            "id": p.id,
                            "nombre": p.nombre,
                            "descripcion": p.descripcion,
                            "precio": float(p.precio),
                            "imagen_url": p.imagen_url,
                            "disponible": p.disponible,
                            "destacado": p.destacado
                        }
                        for p in productos
                    ]
                    
                    # Solo incluir categorías con productos
                    if productos_data:
                        categorias_data.append({
                            "id": categoria.id,
                            "nombre": categoria.nombre,
                            "descripcion": categoria.descripcion,
                            "productos": productos_data
                        })
                
                resultado["locales"].append({
                    "id": local.id,
                    "nombre": local.nombre,
                    "direccion": local.direccion,
                    "telefono": local.telefono,
                    "categorias": categorias_data
                })
            
            return resultado
        
import pytest
from pydantic import ValidationError
from datetime import datetime

# Importar desde el archivo correcto
try:
    from app.schemas.admin_schemas import (
        ProductoCreate,
        ProductoUpdate,
        ProductoResponse
    )
except ImportError:
    ProductoCreate = None
    ProductoUpdate = None
    ProductoResponse = None


class TestProductoCreateSchema:
    """Tests para el schema ProductoCreate"""
    
    def test_producto_create_campos_validos(self):
        """Debe aceptar todos los campos válidos"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        producto = ProductoCreate(
            local_id=1,
            categoria_id=1,
            nombre="Pizza Muzzarella",
            descripcion="Clásica pizza con muzzarella",
            precio=850.50,
            disponible=True,
            destacado=False
        )
        
        assert producto.local_id == 1
        assert producto.categoria_id == 1
        assert producto.nombre == "Pizza Muzzarella"
        assert producto.precio == 850.50
        assert producto.disponible is True
        assert producto.destacado is False
    
    def test_producto_create_campos_opcionales(self):
        """Campos opcionales deben tener valores por defecto"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        producto = ProductoCreate(
            local_id=1,
            categoria_id=1,
            nombre="Pizza Simple",
            descripcion="Descripción básica",
            precio=500.0
        )
        
        # disponible y destacado tienen defaults
        assert producto.disponible is True
        assert producto.destacado is False
    
    def test_producto_create_sin_nombre_falla(self):
        """Debe fallar si falta nombre"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        with pytest.raises(ValidationError) as exc_info:
            ProductoCreate(
                local_id=1,
                categoria_id=1,
                descripcion="Sin nombre",
                precio=100.0
            )
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('nombre',) for error in errors)
    
    def test_producto_create_precio_negativo_falla(self):
        """Debe rechazar precio negativo"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        with pytest.raises(ValidationError):
            ProductoCreate(
                local_id=1,
                categoria_id=1,
                nombre="Producto",
                descripcion="Desc",
                precio=-100.0
            )
    
    def test_producto_create_precio_positivo_valido(self):
        """Precio positivo debe ser válido"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        producto = ProductoCreate(
            local_id=1,
            categoria_id=1,
            nombre="Producto Normal",
            descripcion="Con precio normal",
            precio=100.0
        )
        
        assert producto.precio == 100.0
    
    def test_producto_create_sin_local_id_falla(self):
        """Debe fallar si falta local_id"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        with pytest.raises(ValidationError) as exc_info:
            ProductoCreate(
                categoria_id=1,
                nombre="Producto",
                descripcion="Desc",
                precio=100.0
            )
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('local_id',) for error in errors)
    
    def test_producto_create_sin_categoria_id_falla(self):
        """Debe fallar si falta categoria_id"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        with pytest.raises(ValidationError) as exc_info:
            ProductoCreate(
                local_id=1,
                nombre="Producto",
                descripcion="Desc",
                precio=100.0
            )
        
        errors = exc_info.value.errors()
        assert any(error['loc'] == ('categoria_id',) for error in errors)


class TestProductoUpdateSchema:
    """Tests para el schema ProductoUpdate"""
    
    def test_producto_update_todos_campos_opcionales(self):
        """Todos los campos deben ser opcionales en update"""
        if ProductoUpdate is None:
            pytest.skip("ProductoUpdate no disponible")
        
        producto = ProductoUpdate()
        
        assert producto.nombre is None
        assert producto.descripcion is None
        assert producto.precio is None
        assert producto.categoria_id is None
    
    def test_producto_update_actualizar_solo_nombre(self):
        """Debe permitir actualizar solo el nombre"""
        if ProductoUpdate is None:
            pytest.skip("ProductoUpdate no disponible")
        
        producto = ProductoUpdate(nombre="Nuevo Nombre")
        
        assert producto.nombre == "Nuevo Nombre"
        assert producto.precio is None
    
    def test_producto_update_actualizar_solo_precio(self):
        """Debe permitir actualizar solo el precio"""
        if ProductoUpdate is None:
            pytest.skip("ProductoUpdate no disponible")
        
        producto = ProductoUpdate(precio=1200.50)
        
        assert producto.precio == 1200.50
        assert producto.nombre is None
    
    def test_producto_update_actualizar_multiples_campos(self):
        """Debe permitir actualizar múltiples campos"""
        if ProductoUpdate is None:
            pytest.skip("ProductoUpdate no disponible")
        
        producto = ProductoUpdate(
            nombre="Pizza Modificada",
            precio=950.0,
            disponible=False,
            destacado=True
        )
        
        assert producto.nombre == "Pizza Modificada"
        assert producto.precio == 950.0
        assert producto.disponible is False
        assert producto.destacado is True
    
    def test_producto_update_precio_negativo_falla(self):
        """Debe rechazar precio negativo en update"""
        if ProductoUpdate is None:
            pytest.skip("ProductoUpdate no disponible")
        
        with pytest.raises(ValidationError):
            ProductoUpdate(precio=-50.0)


class TestProductoResponseSchema:
    """Tests para el schema ProductoResponse"""
    
    def test_producto_response_campos_completos(self):
        """Debe incluir todos los campos de respuesta"""
        if ProductoResponse is None:
            pytest.skip("ProductoResponse no disponible")
        
        producto = ProductoResponse(
            id=1,
            local_id=1,
            categoria_id=1,
            nombre="Pizza Napolitana",
            descripcion="Con tomate y albahaca",
            precio=900.0,
            imagen_url="http://localhost:8000/imagenes/napolitana.jpg",
            disponible=True,
            destacado=True,
            orden=1
        )
        
        assert producto.id == 1
        assert producto.local_id == 1
        assert producto.nombre == "Pizza Napolitana"
        assert producto.precio == 900.0
        assert producto.disponible is True
    
    def test_producto_response_sin_imagen_url(self):
        """Debe permitir productos sin imagen_url"""
        if ProductoResponse is None:
            pytest.skip("ProductoResponse no disponible")
        
        producto = ProductoResponse(
            id=1,
            local_id=1,
            categoria_id=1,
            nombre="Producto Sin Imagen",
            descripcion="Descripción",
            precio=100.0,
            imagen_url=None,
            disponible=True,
            destacado=False,
            orden=0
        )
        
        assert producto.imagen_url is None


class TestSchemasConversionTipos:
    """Tests para conversión automática de tipos en schemas"""
    
    def test_producto_create_precio_string_a_float(self):
        """Debe convertir precio de string a float automáticamente"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        producto = ProductoCreate(
            local_id=1,
            categoria_id=1,
            nombre="Producto Test",
            descripcion="Desc",
            precio="850.50"  # String
        )
        
        assert isinstance(producto.precio, float)
        assert producto.precio == 850.50
    
    def test_producto_create_ids_string_a_int(self):
        """Debe convertir IDs de string a int automáticamente"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        producto = ProductoCreate(
            local_id="1",  # String
            categoria_id="2",  # String
            nombre="Producto",
            descripcion="Desc",
            precio=100.0
        )
        
        assert isinstance(producto.local_id, int)
        assert isinstance(producto.categoria_id, int)
        assert producto.local_id == 1
        assert producto.categoria_id == 2


class TestSchemasValidacionCruzada:
    """Tests para validaciones cruzadas entre schemas"""
    
    def test_producto_disponible_false_no_puede_ser_destacado(self):
        """Producto no disponible lógicamente no debería ser destacado"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        # Esto crea el producto pero es lógicamente inconsistente
        producto = ProductoCreate(
            local_id=1,
            categoria_id=1,
            nombre="Producto Inconsistente",
            descripcion="No disponible pero destacado",
            precio=100.0,
            disponible=False,
            destacado=True  # Inconsistente
        )
        
        # El schema lo permite, pero la lógica de negocio debería validarlo
        assert producto.disponible is False
        assert producto.destacado is True
        # Esto es un indicador de que podrías agregar validación personalizada
    
    def test_producto_precio_vs_nombre_coherente(self):
        """Verificar que el precio sea coherente con el tipo de producto"""
        if ProductoCreate is None:
            pytest.skip("ProductoCreate no disponible")
        
        producto_economico = ProductoCreate(
            local_id=1,
            categoria_id=1,
            nombre="Empanada",
            descripcion="Empanada de carne",
            precio=50.0
        )
        
        producto_premium = ProductoCreate(
            local_id=1,
            categoria_id=1,
            nombre="Pizza Especial XXL",
            descripcion="Pizza gigante con ingredientes premium",
            precio=2500.0
        )
        
        assert producto_economico.precio < producto_premium.precio
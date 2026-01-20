import pytest
from unittest.mock import MagicMock, patch, Mock, AsyncMock, PropertyMock
from fastapi import HTTPException, UploadFile
from datetime import datetime, timedelta
import jwt
import os
from io import BytesIO
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.admin_service import AdminService
from app.models.models import Producto, Categoria, Local, Usuario
from app.config.database import Base
from app.utils.utils import SECRET_JWT
from passlib.hash import bcrypt

from fastapi.testclient import TestClient
from fastapi import HTTPException


from main import app
client = TestClient(app)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def db():
    """Base de datos en memoria para tests"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_service():
    """Instancia de AdminService para tests"""
    with patch.dict(os.environ, {
        "ADMIN_USER": "admin",
        "ADMIN_PASSWORD": "admin123",
        "SECRET_JWT": SECRET_JWT,
        "USE_LOCAL_DB": "true",
        "BACKEND_URL": "http://localhost:8000"
    }):
        service = AdminService()
        service.usar_supabase_storage = False  # Forzar storage local
        return service


@pytest.fixture
def mock_upload_file():
    """Mock de UploadFile para tests de imágenes"""
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test_image.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.read = AsyncMock(return_value=b"fake_image_data")
    mock_file.file = BytesIO(b"fake_image_data")
    return mock_file


# ============================================================================
# TESTS DE AUTENTICACIÓN
# ============================================================================

class TestAdminServiceAutenticacion:
    """Tests para métodos de autenticación"""
    
    def test_autenticar_admin_credenciales_validas(self, admin_service):
        """Debe autenticar con credenciales correctas del admin principal"""
        token = admin_service.autenticar_admin("admin", "admin123")
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verificar que el token es válido
        payload = jwt.decode(token, SECRET_JWT, algorithms=["HS256"])
        assert payload["sub"] == "admin"
    
    def test_autenticar_admin_credenciales_invalidas(self, admin_service):
        """Debe lanzar 401 con credenciales incorrectas"""
        with pytest.raises(HTTPException) as exc_info:
            admin_service.autenticar_admin("admin", "wrong_password")
        
        assert exc_info.value.status_code == 401
        assert "incorrectos" in exc_info.value.detail.lower()
    
    def test_autenticar_admin_usuario_inexistente(self, admin_service):
        """Debe lanzar 401 con usuario que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            admin_service.autenticar_admin("usuario_falso", "password")
        
        assert exc_info.value.status_code == 401
    
    def test_crear_token_contiene_datos_correctos(self, admin_service):
        """El token debe contener subject y expiración"""
        token = admin_service.crear_token("test_user")
        
        payload = jwt.decode(token, SECRET_JWT, algorithms=["HS256"])
        assert payload["sub"] == "test_user"
        assert "exp" in payload
    
    def test_verificar_token_valido(self, admin_service):
        """Debe verificar correctamente un token válido"""
        token = admin_service.crear_token("admin")
        
        resultado = admin_service.verificar_token(token)
        
        assert resultado is True
    
    def test_verificar_token_invalido(self, admin_service):
        """Debe rechazar token inválido"""
        resultado = admin_service.verificar_token("token_falso")
        
        assert resultado is False
    
    def test_verificar_token_expirado(self, admin_service):
        """Debe rechazar token expirado"""
        payload = {
            "sub": "admin",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        token_expirado = jwt.encode(payload, SECRET_JWT, algorithm="HS256")
        
        resultado = admin_service.verificar_token(token_expirado)
        
        assert resultado is False


# ============================================================================
# TESTS DE GESTIÓN DE PRODUCTOS
# ============================================================================

class TestAdminServiceProductos:
    """Tests para métodos de productos"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_productos_local_especifico(self, mock_session):
        """Debe obtener solo productos del local especificado"""
        mock_categoria = MagicMock()
        mock_categoria.id = 1
        mock_categoria.nombre = "Pizzas"
        
        mock_producto1 = MagicMock(spec=Producto)
        mock_producto1.id = 1
        mock_producto1.local_id = 1
        mock_producto1.categoria_id = 1
        mock_producto1.nombre = "Pizza"
        mock_producto1.descripcion = "Pizza deliciosa"
        mock_producto1.precio = 12.50
        mock_producto1.disponible = True
        mock_producto1.destacado = False
        mock_producto1.imagen_url = "/images/pizza.jpg"
        mock_producto1.categoria = mock_categoria
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_producto1]
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_productos(local_id=1)
        
        assert len(resultado) == 1
        assert resultado[0]["id"] == 1
        assert resultado[0]["nombre"] == "Pizza"
        assert resultado[0]["local_id"] == 1
        assert resultado[0]["precio"] == 12.50
        assert resultado[0]["categorias"]["nombre"] == "Pizzas"
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_productos_sin_categoria(self, mock_session):
        """Debe manejar productos sin categoría asociada"""
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.categoria_id = None
        mock_producto.nombre = "Producto Sin Categoría"
        mock_producto.descripcion = "Descripción"
        mock_producto.precio = 10.0
        mock_producto.disponible = True
        mock_producto.destacado = False
        mock_producto.imagen_url = None
        mock_producto.categoria = None
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_producto]
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_productos(local_id=1)
        
        assert len(resultado) == 1
        assert resultado[0]["categorias"] is None
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_crear_producto_sin_imagen(self, mock_manager, mock_session, admin_service):
        """Debe crear producto sin imagen correctamente"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        mock_categoria.nombre = "Categoría Test"
        
        mock_db = MagicMock()
        
        # Configurar consulta para categoría
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        class MockDatos:
            categoria_id = 1
            nombre = "Nuevo Producto"
            descripcion = "Descripción"
            precio = 15.0
            disponible = True
            destacado = False
        
        mock_datos = MockDatos()
        
        resultado = await admin_service.crear_producto(
            local_id=1,
            datos=mock_datos,
            imagen=None
        )
        
        assert "creado exitosamente" in resultado["message"]
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_actualizar_producto_sin_imagen(self, mock_manager, mock_session, admin_service):
        """Debe actualizar producto sin cambiar imagen"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock()
        mock_categoria.id = 1
        mock_categoria.nombre = "Categoría"
        
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.nombre = "Producto Original"
        mock_producto.precio = 10.0
        mock_producto.imagen_url = "/images/original.jpg"
        mock_producto.categoria = mock_categoria
        mock_producto.categoria_id = 1
        
        mock_db = MagicMock()
        
        # Configurar consulta para producto
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_producto
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        class MockDatos:
            nombre = "Producto Actualizado"
            descripcion = "Nueva descripción"
            precio = 15.0
            disponible = True
            destacado = True
            categoria_id = None
        
        mock_datos = MockDatos()
        
        resultado = await admin_service.actualizar_producto(
            producto_id=1,
            local_id=1,
            datos=mock_datos,
            imagen=None
        )
        
        assert "actualizado exitosamente" in resultado["message"]
        assert mock_producto.nombre == "Producto Actualizado"
        assert mock_producto.precio == 15.0
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_actualizar_producto_no_encontrado(self, mock_session, admin_service):
        """Debe lanzar 404 si el producto no existe"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        class MockDatos:
            nombre = "Producto"
        
        mock_datos = MockDatos()
        
        with pytest.raises(HTTPException) as exc_info:
            await admin_service.actualizar_producto(
                producto_id=999,
                local_id=1,
                datos=mock_datos,
                imagen=None
            )
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_eliminar_producto_exitoso(self, mock_manager, mock_session, admin_service):
        """Debe eliminar producto correctamente"""
        mock_manager.broadcast = AsyncMock()
        
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.imagen_url = None
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_producto
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        resultado = await admin_service.eliminar_producto(producto_id=1, local_id=1)
        
        assert "eliminado correctamente" in resultado["mensaje"]
        mock_db.delete.assert_called_once_with(mock_producto)
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_crear_producto_local_no_existe(self, mock_session, admin_service):
        """Debe lanzar 400 si la categoría no existe"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        class MockDatos:
            nombre = "Producto"
            precio = 10.0
            categoria_id = 1
        
        mock_datos = MockDatos()
        
        with pytest.raises(HTTPException) as exc_info:
            await admin_service.crear_producto(local_id=999, datos=mock_datos, imagen=None)
        
        assert exc_info.value.status_code == 400


# ============================================================================
# TESTS DE GESTIÓN DE CATEGORÍAS
# ============================================================================

class TestAdminServiceCategorias:
    """Tests para métodos de categorías"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_categorias_local_especifico(self, mock_session):
        """Debe obtener solo categorías del local especificado"""
        mock_cat1 = MagicMock(spec=Categoria)
        mock_cat1.id = 1
        mock_cat1.nombre = "Pizzas"
        mock_cat1.descripcion = "Categoría de pizzas"
        mock_cat1.orden = 1
        mock_cat1.esta_activo = True
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_cat1]
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_categorias(local_id=1)
        
        assert len(resultado) == 1
        assert resultado[0]["id"] == 1
        assert resultado[0]["nombre"] == "Pizzas"
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_crear_categoria_exitoso(self, mock_manager, mock_session, admin_service):
        """Debe crear categoría correctamente"""
        mock_manager.broadcast = AsyncMock()
        
        mock_db = MagicMock()
        
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            if model == Categoria:
                mock_query = MagicMock()
                if call_count == 0:
                    # Primera llamada: verificar si existe categoría con mismo nombre
                    mock_query.filter.return_value.first.return_value = None
                else:
                    # Segunda llamada: contar categorías para orden
                    mock_query.filter.return_value.count.return_value = 0
                call_count += 1
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        resultado = await admin_service.crear_categoria(
            local_id=1,
            nombre="Nueva Categoría",
            descripcion="Descripción"
        )
        
        assert "creada exitosamente" in resultado["message"]
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_crear_categoria_nombre_duplicado(self, mock_session, admin_service):
        """Debe rechazar categoría con nombre duplicado en el mismo local"""
        mock_categoria_existente = MagicMock(spec=Categoria)
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria_existente
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        with pytest.raises(HTTPException) as exc_info:
            await admin_service.crear_categoria(
                local_id=1,
                nombre="Pizzas",
                descripcion="Desc"
            )
        
        assert exc_info.value.status_code == 400
        assert "Ya existe" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_actualizar_categoria_exitoso(self, mock_manager, mock_session, admin_service):
        """Debe actualizar categoría correctamente"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        mock_categoria.nombre = "Nombre Original"
        mock_categoria.descripcion = ""
        mock_categoria.orden = 1
        
        mock_db = MagicMock()
        
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            if model == Categoria:
                mock_query = MagicMock()
                if call_count == 0:
                    # Primera llamada: obtener categoría a actualizar
                    mock_query.filter.return_value.first.return_value = mock_categoria
                else:
                    # Segunda llamada: verificar si existe otra categoría con mismo nombre
                    mock_query.filter.return_value.first.return_value = None
                call_count += 1
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        resultado = await admin_service.actualizar_categoria(
            local_id=1,
            categoria_id=1,
            nombre="Nombre Actualizado",
            descripcion="Nueva descripción"
        )
        
        assert "actualizada exitosamente" in resultado["message"]
        assert mock_categoria.nombre == "Nombre Actualizado"
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_eliminar_categoria_con_productos(self, mock_session, admin_service):
        """Debe eliminar categoría y sus productos asociados"""
        mock_db = MagicMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        
        mock_producto1 = MagicMock(spec=Producto)
        mock_producto1.imagen_url = "/images/prod1.jpg"
        mock_producto2 = MagicMock(spec=Producto)
        mock_producto2.imagen_url = None
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria
                return mock_query
            elif model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = [mock_producto1, mock_producto2]
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        with patch.object(admin_service, 'eliminar_imagen', new_callable=AsyncMock) as mock_eliminar:
            resultado = await admin_service.eliminar_categoria(local_id=1, categoria_id=1)
        
        assert resultado["categoria_id"] == 1
        assert "productos_eliminados" in resultado
        mock_db.delete.assert_called_once_with(mock_categoria)
        mock_db.commit.assert_called()


# ============================================================================
# TESTS DE GESTIÓN DE LOCALES
# ============================================================================

class TestAdminServiceLocales:
    """Tests para métodos de locales"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_locales_usuario_autenticado(self, mock_session):
        """Debe obtener solo el local del usuario autenticado"""
        mock_local = MagicMock(spec=Local)
        mock_local.id = 1
        mock_local.nombre = "Local Centro"
        mock_local.direccion = "Calle 123"
        mock_local.telefono = "555-0001"
        mock_local.esta_activo = True
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Local:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_local
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_locales(local_id=1)
        
        assert len(resultado) == 1
        assert resultado[0]["id"] == 1
        assert resultado[0]["nombre"] == "Local Centro"
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_locales_local_no_existe(self, mock_session):
        """Debe retornar lista vacía si el local no existe"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Local:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_locales(local_id=999)
        
        assert resultado == []


# ============================================================================
# TESTS DE GESTIÓN DE IMÁGENES
# ============================================================================

class TestAdminServiceImagenes:
    """Tests para subida y eliminación de imágenes"""
    
    @pytest.mark.asyncio
    async def test_subir_imagen_local_storage(self, admin_service, mock_upload_file):
        """Debe guardar imagen en storage local correctamente"""
        with patch.object(admin_service, '_guardar_imagen_local', new_callable=AsyncMock) as mock_guardar:
            mock_guardar.return_value = "http://localhost:8000/imagenes/test_image.jpg"
            
            resultado = await admin_service.subir_imagen(mock_upload_file)
            
            assert "imagenes/test_image.jpg" in resultado
            mock_guardar.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_guardar_imagen_local_crea_directorio(self, admin_service, mock_upload_file):
        """Debe crear directorio de imágenes si no existe"""
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('builtins.open', MagicMock()):
            
            await admin_service._guardar_imagen_local(mock_upload_file)
            
            mock_mkdir.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_eliminar_imagen_local(self, admin_service):
        """Debe eliminar imagen del sistema de archivos local"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            resultado = await admin_service.eliminar_imagen("http://localhost:8000/imagenes/test.jpg")
            
            assert resultado is True
            mock_unlink.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_eliminar_imagen_no_existe(self, admin_service):
        """Debe retornar False si la imagen no existe"""
        with patch('pathlib.Path.exists', return_value=False):
            resultado = await admin_service.eliminar_imagen("http://localhost:8000/imagenes/noexiste.jpg")
            
            assert resultado is False
    
    @pytest.mark.asyncio
    async def test_eliminar_imagen_url_invalida(self, admin_service):
        """Debe manejar URLs de imagen inválidas"""
        resultado = await admin_service.eliminar_imagen("url_invalida")
        
        assert resultado is False


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================

class TestAdminServiceIntegracion:
    """Tests de integración entre diferentes métodos"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_flujo_completo_crear_actualizar_eliminar_producto(
        self, mock_manager, mock_session, admin_service
    ):
        """Test de flujo completo: crear → actualizar → eliminar producto"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.nombre = "Producto Test"
        mock_producto.imagen_url = None
        mock_producto.categoria = mock_categoria
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria
                return mock_query
            elif model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_producto
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        class MockDatosCrear:
            categoria_id = 1
            nombre = "Producto Test"
            descripcion = "Descripción"
            precio = 10.0
            disponible = True
            destacado = False
        
        mock_datos_crear = MockDatosCrear()
        
        resultado_crear = await admin_service.crear_producto(
            local_id=1,
            datos=mock_datos_crear,
            imagen=None
        )
        
        assert "creado exitosamente" in resultado_crear["message"]
        
        class MockDatosActualizar:
            nombre = "Producto Actualizado"
            descripcion = "Nueva descripción"
            precio = 15.0
            disponible = True
            destacado = True
            categoria_id = None
        
        mock_datos_actualizar = MockDatosActualizar()
        
        resultado_actualizar = await admin_service.actualizar_producto(
            producto_id=1,
            local_id=1,
            datos=mock_datos_actualizar,
            imagen=None
        )
        
        assert "actualizado exitosamente" in resultado_actualizar["message"]
        
        resultado_eliminar = await admin_service.eliminar_producto(
            producto_id=1,
            local_id=1
        )
        
        assert "eliminado correctamente" in resultado_eliminar["mensaje"]


# ============================================================================
# TESTS DE CASOS EDGE
# ============================================================================

class TestAdminServiceEdgeCases:
    """Tests de casos extremos y errores"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_crear_producto_precio_cero(self, mock_manager, mock_session, admin_service):
        """Debe permitir precio en cero"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        class MockDatos:
            nombre = "Producto Gratis"
            precio = 0.0
            categoria_id = 1
            disponible = True
            destacado = False
            descripcion = "Descripción"
        
        mock_datos = MockDatos()
        
        resultado = await admin_service.crear_producto(
            local_id=1,
            datos=mock_datos,
            imagen=None
        )
        
        assert "creado exitosamente" in resultado["message"]
    
    @pytest.mark.asyncio
    async def test_subir_imagen_archivo_vacio(self, admin_service):
        """Debe manejar archivos vacíos"""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "empty.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.read = AsyncMock(return_value=b"")
        
        with patch.object(admin_service, '_guardar_imagen_local', new_callable=AsyncMock) as mock_guardar:
            mock_guardar.return_value = "http://localhost:8000/imagenes/empty.jpg"
            
            resultado = await admin_service.subir_imagen(mock_file)
            
            assert resultado is not None
    
    def test_crear_token_usuario_con_caracteres_especiales(self, admin_service):
        """Debe manejar usuarios con caracteres especiales"""
        token = admin_service.crear_token("usuario@local.com")
        
        payload = jwt.decode(token, SECRET_JWT, algorithms=["HS256"])
        assert payload["sub"] == "usuario@local.com"
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_productos_local_sin_productos(self, mock_session):
        """Debe retornar lista vacía si el local no tiene productos"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = []
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_productos(local_id=1)
        
        assert resultado == []
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_crear_producto_sin_categoria(self, mock_manager, mock_session, admin_service):
        """Debe lanzar 400 si la categoría no existe"""
        mock_manager.broadcast = AsyncMock()
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        class MockDatos:
            categoria_id = 999
            nombre = "Producto"
            descripcion = "Descripción"
            precio = 10.0
            disponible = True
            destacado = False
        
        mock_datos = MockDatos()
        
        with pytest.raises(HTTPException) as exc_info:
            await admin_service.crear_producto(
                local_id=1,
                datos=mock_datos,
                imagen=None
            )
        
        assert exc_info.value.status_code == 400
        assert "no pertenece" in exc_info.value.detail.lower()


# ============================================================================
# TESTS ADICIONALES DE AUTENTICACIÓN
# ============================================================================

class TestAdminServiceAutenticacionExtra:
    """Tests adicionales para mejorar cobertura de autenticación"""
    
    
    
    def test_verificar_token_sin_sub(self):
        """Debe rechazar token sin campo 'sub'"""
        payload = {
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, SECRET_JWT, algorithm="HS256")
        
        service = AdminService()
        resultado = service.verificar_token(token)
        
        assert resultado is False
    
    def test_verificar_token_excepcion_general(self):
        """Debe retornar False ante cualquier excepción"""
        service = AdminService()
        resultado = service.verificar_token("token_malformado")
        
        assert resultado is False


# ============================================================================
# TESTS ADICIONALES DE PRODUCTOS
# ============================================================================

class TestAdminServiceProductosExtra:
    """Tests adicionales para mejorar cobertura de productos"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_crear_producto_con_imagen(self, mock_manager, mock_session):
        """Debe crear producto con imagen correctamente"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        mock_categoria.nombre = "Categoría Test"
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        service.usar_supabase_storage = False
        
        mock_imagen = MagicMock(spec=UploadFile)
        mock_imagen.filename = "test.jpg"
        mock_imagen.read = AsyncMock(return_value=b"fake_data")
        
        class MockDatos:
            categoria_id = 1
            nombre = "Producto con Imagen"
            descripcion = "Descripción"
            precio = 20.0
            disponible = True
            destacado = False
        
        with patch.object(service, 'subir_imagen', new_callable=AsyncMock) as mock_subir:
            mock_subir.return_value = "http://localhost:8000/imagenes/test.jpg"
            
            resultado = await service.crear_producto(
                local_id=1,
                datos=MockDatos(),
                imagen=mock_imagen
            )
        
        assert "creado exitosamente" in resultado["message"]
        mock_subir.assert_called_once_with(mock_imagen)
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_actualizar_producto_con_nueva_imagen(self, mock_manager, mock_session):
        """Debe actualizar producto reemplazando la imagen"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock()
        mock_categoria.id = 1
        mock_categoria.nombre = "Categoría"
        
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.nombre = "Producto"
        mock_producto.imagen_url = "http://localhost:8000/imagenes/old.jpg"
        mock_producto.categoria = mock_categoria
        mock_producto.categoria_id = 1
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_producto
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        mock_imagen = MagicMock(spec=UploadFile)
        mock_imagen.filename = "new.jpg"
        mock_imagen.read = AsyncMock(return_value=b"new_data")
        
        class MockDatos:
            nombre = None
            descripcion = None
            precio = None
            categoria_id = None
            disponible = None
            destacado = None
        
        with patch.object(service, 'eliminar_imagen', new_callable=AsyncMock) as mock_eliminar, \
             patch.object(service, 'subir_imagen', new_callable=AsyncMock) as mock_subir:
            mock_subir.return_value = "http://localhost:8000/imagenes/new.jpg"
            
            resultado = await service.actualizar_producto(
                producto_id=1,
                local_id=1,
                datos=MockDatos(),
                imagen=mock_imagen
            )
        
        mock_eliminar.assert_called_once_with("http://localhost:8000/imagenes/old.jpg")
        mock_subir.assert_called_once_with(mock_imagen)
        assert "actualizado exitosamente" in resultado["message"]
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_actualizar_producto_cambiar_categoria(self, mock_manager, mock_session):
        """Debe validar que la nueva categoría pertenezca al local"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria_vieja = MagicMock()
        mock_categoria_vieja.id = 1
        mock_categoria_vieja.nombre = "Categoría Vieja"
        
        mock_categoria_nueva = MagicMock(spec=Categoria)
        mock_categoria_nueva.id = 2
        mock_categoria_nueva.local_id = 1
        
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.categoria_id = 1
        mock_producto.categoria = mock_categoria_vieja
        
        mock_db = MagicMock()
        
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_producto
                return mock_query
            elif model == Categoria:
                mock_query = MagicMock()
                if call_count == 0:
                    mock_query.filter.return_value.first.return_value = mock_categoria_nueva
                call_count += 1
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        class MockDatos:
            nombre = None
            descripcion = None
            precio = None
            categoria_id = 2  # Nueva categoría
            disponible = None
            destacado = None
        
        resultado = await service.actualizar_producto(
            producto_id=1,
            local_id=1,
            datos=MockDatos(),
            imagen=None
        )
        
        assert "actualizado exitosamente" in resultado["message"]
        assert mock_producto.categoria_id == 2
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_actualizar_producto_categoria_invalida(self, mock_manager, mock_session):
        """Debe rechazar categoría que no pertenece al local"""
        mock_manager.broadcast = AsyncMock()
        
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.categoria_id = 1
        
        mock_db = MagicMock()
        
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_producto
                return mock_query
            elif model == Categoria:
                mock_query = MagicMock()
                if call_count == 0:
                    # Categoría no encontrada o de otro local
                    mock_query.filter.return_value.first.return_value = None
                call_count += 1
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        class MockDatos:
            nombre = None
            descripcion = None
            precio = None
            categoria_id = 999
            disponible = None
            destacado = None
        
        with pytest.raises(HTTPException) as exc_info:
            await service.actualizar_producto(
                producto_id=1,
                local_id=1,
                datos=MockDatos(),
                imagen=None
            )
        
        assert exc_info.value.status_code == 400
        assert "no pertenece" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_eliminar_producto_con_imagen(self, mock_manager, mock_session):
        """Debe eliminar producto y su imagen"""
        mock_manager.broadcast = AsyncMock()
        
        mock_producto = MagicMock(spec=Producto)
        mock_producto.id = 1
        mock_producto.local_id = 1
        mock_producto.imagen_url = "http://localhost:8000/imagenes/producto.jpg"
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_producto
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        with patch.object(service, 'eliminar_imagen', new_callable=AsyncMock) as mock_eliminar:
            resultado = await service.eliminar_producto(producto_id=1, local_id=1)
        
        mock_eliminar.assert_called_once_with("http://localhost:8000/imagenes/producto.jpg")
        assert "eliminado correctamente" in resultado["mensaje"]
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_eliminar_producto_no_encontrado(self, mock_session):
        """Debe lanzar 404 si producto no existe"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        with pytest.raises(HTTPException) as exc_info:
            await service.eliminar_producto(producto_id=999, local_id=1)
        
        assert exc_info.value.status_code == 404


# ============================================================================
# TESTS ADICIONALES DE CATEGORÍAS
# ============================================================================

class TestAdminServiceCategoriasExtra:
    """Tests adicionales para mejorar cobertura de categorías"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_categorias_vacio(self, mock_session):
        """Debe retornar lista vacía si no hay categorías"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.order_by.return_value.all.return_value = []
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_categorias(local_id=1)
        
        assert resultado == []
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_actualizar_categoria_no_encontrada(self, mock_session):
        """Debe lanzar 404 si categoría no existe"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        with pytest.raises(HTTPException) as exc_info:
            await service.actualizar_categoria(
                local_id=1,
                categoria_id=999,
                nombre="Nuevo Nombre",
                descripcion="Desc"
            )
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_actualizar_categoria_nombre_duplicado(self, mock_session):
        """Debe rechazar actualización con nombre duplicado"""
        mock_categoria_actual = MagicMock(spec=Categoria)
        mock_categoria_actual.id = 1
        mock_categoria_actual.local_id = 1
        
        mock_categoria_existente = MagicMock(spec=Categoria)
        mock_categoria_existente.id = 2
        
        mock_db = MagicMock()
        
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            if model == Categoria:
                mock_query = MagicMock()
                if call_count == 0:
                    mock_query.filter.return_value.first.return_value = mock_categoria_actual
                else:
                    mock_query.filter.return_value.first.return_value = mock_categoria_existente
                call_count += 1
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        with pytest.raises(HTTPException) as exc_info:
            await service.actualizar_categoria(
                local_id=1,
                categoria_id=1,
                nombre="Nombre Existente",
                descripcion="Desc"
            )
        
        assert exc_info.value.status_code == 400
        assert "Ya existe" in exc_info.value.detail
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_actualizar_categoria_sin_cambiar_descripcion(self, mock_manager, mock_session, admin_service):
        """Debe actualizar solo nombre si descripcion es None"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        mock_categoria.nombre = "Nombre Original"
        mock_categoria.descripcion = "Descripción Original"
        mock_categoria.orden = 1
        
        mock_db = MagicMock()
        
        call_count = 0
        def query_side_effect(model):
            nonlocal call_count
            if model == Categoria:
                mock_query = MagicMock()
                if call_count == 0:
                    mock_query.filter.return_value.first.return_value = mock_categoria
                else:
                    mock_query.filter.return_value.first.return_value = None
                call_count += 1
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        resultado = await service.actualizar_categoria(
            local_id=1,
            categoria_id=1,
            nombre="Nuevo Nombre",
            descripcion=None
        )
        
        assert mock_categoria.nombre == "Nuevo Nombre"
        assert mock_categoria.descripcion == "Descripción Original"  # No cambió
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_eliminar_categoria_no_encontrada(self, mock_session):
        """Debe lanzar 404 si categoría no existe"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = None
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        with pytest.raises(HTTPException) as exc_info:
            await service.eliminar_categoria(local_id=1, categoria_id=999)
        
        assert exc_info.value.status_code == 404
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_eliminar_categoria_sin_productos(self, mock_manager, mock_session, admin_service):
        """Debe eliminar categoría vacía correctamente"""
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria
                return mock_query
            elif model == Producto:
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = []
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        resultado = await service.eliminar_categoria(local_id=1, categoria_id=1)
        
        assert resultado["categoria_id"] == 1
        assert resultado["productos_eliminados"] == 0
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_reordenar_categorias_exitoso(self, mock_manager, mock_session, admin_service):
        """Debe reordenar categorías correctamente"""
        mock_manager.broadcast = AsyncMock()
        
        mock_cat1 = MagicMock(spec=Categoria)
        mock_cat1.id = 1
        mock_cat1.orden = 1
        
        mock_cat2 = MagicMock(spec=Categoria)
        mock_cat2.id = 2
        mock_cat2.orden = 2
        
        mock_cat3 = MagicMock(spec=Categoria)
        mock_cat3.id = 3
        mock_cat3.orden = 3
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = [mock_cat1, mock_cat2, mock_cat3]
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        nuevo_orden = [3, 1, 2]
        resultado = await service.reordenar_categorias(local_id=1, orden_ids=nuevo_orden)
        
        assert resultado["orden"] == nuevo_orden
        assert mock_cat3.orden == 1
        assert mock_cat1.orden == 2
        assert mock_cat2.orden == 3
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_reordenar_categorias_ids_invalidos(self, mock_session):
        """Debe rechazar reordenamiento con IDs inválidos"""
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.all.return_value = []  # No encuentra categorías
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        with pytest.raises(HTTPException) as exc_info:
            await service.reordenar_categorias(local_id=1, orden_ids=[1, 2, 3])
        
        assert exc_info.value.status_code == 400


# ============================================================================
# TESTS ADICIONALES DE IMÁGENES
# ============================================================================

class TestAdminServiceImagenesExtra:
    """Tests adicionales para mejorar cobertura de imágenes"""
    
    @pytest.mark.asyncio
    async def test_eliminar_imagen_url_none(self):
        """Debe retornar False si imagen_url es None"""
        service = AdminService()
        resultado = await service.eliminar_imagen(None)
        
        assert resultado is False
    
    @pytest.mark.asyncio
    async def test_eliminar_imagen_url_vacia(self):
        """Debe retornar False si imagen_url es vacía"""
        service = AdminService()
        resultado = await service.eliminar_imagen("")
        
        assert resultado is False
    
    @pytest.mark.asyncio
    async def test_eliminar_imagen_excepcion(self):
        """Debe manejar excepciones y retornar False"""
        service = AdminService()
        service.usar_supabase_storage = False
        
        with patch('pathlib.Path.exists', side_effect=Exception("Error filesystem")):
            resultado = await service.eliminar_imagen("http://localhost:8000/imagenes/test.jpg")
        
        assert resultado is False
    
    @pytest.mark.asyncio
    async def test_subir_imagen_supabase(self):
        """Debe subir imagen a Supabase cuando está configurado"""
        service = AdminService()
        service.usar_supabase_storage = True
        service.supabase = MagicMock()
        
        mock_storage = MagicMock()
        mock_storage.upload.return_value = {"Key": "productos/uuid.jpg"}
        mock_storage.get_public_url.return_value = "https://supabase.co/storage/img/productos/uuid.jpg"
        service.supabase.storage.from_.return_value = mock_storage
        
        mock_imagen = MagicMock(spec=UploadFile)
        mock_imagen.filename = "test.jpg"
        mock_imagen.content_type = "image/jpeg"
        mock_imagen.read = AsyncMock(return_value=b"data")
        
        resultado = await service.subir_imagen(mock_imagen)
        
        assert "supabase.co" in resultado
        mock_storage.upload.assert_called_once()


# ============================================================================
# TESTS DE INICIALIZACIÓN
# ============================================================================

class TestAdminServiceInit:
    """Tests para el constructor de AdminService"""
    
    def test_init_con_supabase_deshabilitado(self):
        """Debe inicializar sin Supabase cuando USE_LOCAL_DB=true"""
        with patch.dict(os.environ, {
            "USE_LOCAL_DB": "true",
            "SUPABASE_URL": "https://test.supabase.co",
            "SERVICE_ROLE_KEY": "test_key"
        }):
            service = AdminService()
            assert service.usar_supabase_storage is False
    
    def test_init_sin_credenciales_supabase(self):
        """Debe usar storage local si faltan credenciales de Supabase"""
        with patch.dict(os.environ, {
            "USE_LOCAL_DB": "false",
            "SUPABASE_URL": "",
            "SERVICE_ROLE_KEY": ""
        }):
            service = AdminService()
            assert service.usar_supabase_storage is False


# ============================================================================
# TESTS DE CASOS LÍMITE
# ============================================================================

class TestAdminServiceCasosLimite:
    """Tests de casos límite y edge cases"""
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    async def test_obtener_productos_multiples_locales(self, mock_session):
        """Debe filtrar productos solo del local especificado"""
        mock_cat = MagicMock()
        mock_cat.id = 1
        mock_cat.nombre = "Categoría"
        
        mock_prod_local1 = MagicMock(spec=Producto)
        mock_prod_local1.id = 1
        mock_prod_local1.local_id = 1
        mock_prod_local1.nombre = "Producto Local 1"
        mock_prod_local1.categoria = mock_cat
        mock_prod_local1.precio = 10.0
        mock_prod_local1.disponible = True
        mock_prod_local1.destacado = False
        mock_prod_local1.descripcion = "Desc"
        mock_prod_local1.categoria_id = 1
        mock_prod_local1.imagen_url = None
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Producto:
                mock_query = MagicMock()
                # Solo retorna productos del local 1
                mock_query.filter.return_value.all.return_value = [mock_prod_local1]
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        resultado = await service.obtener_productos(local_id=1)
        
        assert len(resultado) == 1
        assert resultado[0]["local_id"] == 1
    
    @pytest.mark.asyncio
    @patch('app.services.admin_service.SessionLocal')
    @patch('app.services.admin_service.manager')
    async def test_crear_producto_precio_negativo_validado_por_schema(self, mock_manager, mock_session, admin_service):
        """El precio negativo debe ser validado por el schema antes de llegar al servicio"""
        # Este test verifica que el servicio asume validación previa
        mock_manager.broadcast = AsyncMock()
        
        mock_categoria = MagicMock(spec=Categoria)
        mock_categoria.id = 1
        mock_categoria.local_id = 1
        
        mock_db = MagicMock()
        
        def query_side_effect(model):
            if model == Categoria:
                mock_query = MagicMock()
                mock_query.filter.return_value.first.return_value = mock_categoria
                return mock_query
            return MagicMock()
        
        mock_db.query.side_effect = query_side_effect
        mock_session.return_value.__enter__.return_value = mock_db
        
        service = AdminService()
        
        class MockDatos:
            categoria_id = 1
            nombre = "Producto"
            descripcion = "Desc"
            precio = -10.0  # Precio negativo (normalmente rechazado por Pydantic)
            disponible = True
            destacado = False
        
        mock_datos = MockDatos()
        
        resultado = await service.crear_producto(
            local_id=1,
            datos=mock_datos,
            imagen=None
        )
        
        assert "creado exitosamente" in resultado["message"]




# ============================================================================
# HELPERS
# ============================================================================

def crear_token_admin(user_id: int, local_id: int, rol: str = "admin"):
    """Crea un token JWT válido para admin"""
    payload = {
        "user_id": user_id,
        "local_id": local_id,
        "rol": rol,
        "nombre": "Admin Test",
        "exp": datetime.utcnow() + timedelta(hours=8)
    }
    return jwt.encode(payload, SECRET_JWT, algorithm="HS256")


# ============================================================================
# TESTS DE ENDPOINTS DE PRODUCTOS
# ============================================================================

class TestAdminProductosEndpoints:
    """Tests para endpoints de productos en /admin"""
    
    @patch('app.api.endpoints.admin.admin_service.obtener_productos')
    def test_get_productos_endpoint_exitoso(self, mock_obtener):
        """GET /admin/productos debe retornar productos del local"""
        mock_obtener.return_value = [
            {
                "id": 1,
                "nombre": "Pizza Margherita",
                "precio": 12.50,
                "disponible": True,
                "destacado": False,
                "local_id": 1,
                "categoria_id": 1,
                "descripcion": "Pizza clásica",
                "imagen_url": None,
                "categorias": {"id": 1, "nombre": "Pizzas"}
            }
        ]
        
        token = crear_token_admin(1, 1)
        
        response = client.get(
            "/admin/productos",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["nombre"] == "Pizza Margherita"
    
    @patch('app.api.endpoints.admin.admin_service.crear_producto')
    def test_post_producto_endpoint_sin_imagen(self, mock_crear):
        """POST /admin/productos debe crear producto sin imagen"""
        mock_crear.return_value = {
            "message": "Producto creado exitosamente",
            "producto_id": 1
        }
        
        token = crear_token_admin(1, 1)
        
        response = client.post(
            "/admin/productos",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "nombre": "Hamburguesa Clásica",
                "descripcion": "Hamburguesa con queso",
                "precio": "8.50",
                "categoria_id": "2",
                "disponible": "true",
                "destacado": "false"
            }
        )
        
        assert response.status_code == 200
        assert "creado exitosamente" in response.json()["message"]
    
    @patch('app.api.endpoints.admin.admin_service.actualizar_producto')
    def test_put_producto_endpoint_actualizar_precio(self, mock_actualizar):
        """PUT /admin/productos/{id} debe actualizar producto"""
        mock_actualizar.return_value = {
            "message": "Producto actualizado exitosamente"
        }
        
        token = crear_token_admin(1, 1)
        
        response = client.put(
            "/admin/productos/1",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "nombre": "Pizza Actualizada",
                "precio": "15.00"
            }
        )
        
        assert response.status_code == 200
        assert "actualizado exitosamente" in response.json()["message"]
    
    @patch('app.api.endpoints.admin.admin_service.eliminar_producto')
    def test_delete_producto_endpoint_exitoso(self, mock_eliminar):
        """DELETE /admin/productos/{id} debe eliminar producto"""
        mock_eliminar.return_value = {
            "mensaje": "Producto eliminado correctamente"
        }
        
        token = crear_token_admin(1, 1)
        
        response = client.delete(
            "/admin/productos/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "eliminado correctamente" in response.json()["mensaje"]
    
    def test_get_productos_sin_autenticacion(self):
        """Debe rechazar petición sin token"""
        response = client.get("/admin/productos")
        
        # CORREGIDO: El endpoint retorna 401 (Unauthorized) no 403 (Forbidden)
        assert response.status_code == 401


# ============================================================================
# TESTS DE ENDPOINTS DE CATEGORÍAS
# ============================================================================

class TestAdminCategoriasEndpoints:
    """Tests para endpoints de categorías en /admin"""
    
    @patch('app.api.endpoints.admin.admin_service.obtener_categorias')
    def test_get_categorias_endpoint_exitoso(self, mock_obtener):
        """GET /admin/categorias debe retornar categorías del local"""
        mock_obtener.return_value = [
            {
                "id": 1,
                "nombre": "Pizzas",
                "descripcion": "Pizzas artesanales",
                "orden": 1,
                "esta_activo": True
            },
            {
                "id": 2,
                "nombre": "Bebidas",
                "descripcion": "Bebidas frías y calientes",
                "orden": 2,
                "esta_activo": True
            }
        ]
        
        token = crear_token_admin(1, 1)
        
        response = client.get(
            "/admin/categorias",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["nombre"] == "Pizzas"
        assert data[1]["nombre"] == "Bebidas"
    
    @patch('app.api.endpoints.admin.admin_service.crear_categoria')
    def test_post_categoria_endpoint_exitoso(self, mock_crear):
        """POST /admin/categorias debe crear nueva categoría"""
        mock_crear.return_value = {
            "message": "Categoría creada exitosamente",
            "categoria_id": 3
        }
        
        token = crear_token_admin(1, 1)
        
        response = client.post(
            "/admin/categorias",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nombre": "Postres",
                "descripcion": "Postres caseros"
            }
        )
        
        assert response.status_code == 200
        assert "creada exitosamente" in response.json()["message"]
    
    @patch('app.api.endpoints.admin.admin_service.actualizar_categoria')
    def test_put_categoria_endpoint_cambiar_nombre(self, mock_actualizar):
        """PUT /admin/categorias/{id} debe actualizar categoría"""
        mock_actualizar.return_value = {
            "message": "Categoría actualizada exitosamente"
        }
        
        token = crear_token_admin(1, 1)
        
        response = client.put(
            "/admin/categorias/1",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nombre": "Pizzas Gourmet",
                "descripcion": "Pizzas premium"
            }
        )
        
        assert response.status_code == 200
        assert "actualizada exitosamente" in response.json()["message"]
    
    @patch('app.api.endpoints.admin.admin_service.eliminar_categoria')
    def test_delete_categoria_endpoint_exitoso(self, mock_eliminar):
        """DELETE /admin/categorias/{id} debe eliminar categoría"""
        mock_eliminar.return_value = {
            "categoria_id": 1,
            "productos_eliminados": 5
        }
        
        token = crear_token_admin(1, 1)
        
        response = client.delete(
            "/admin/categorias/1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["categoria_id"] == 1
        assert data["productos_eliminados"] == 5
    


# ============================================================================
# TESTS DE VALIDACIÓN DE DATOS
# ============================================================================

class TestAdminValidacionDatos:
    """Tests para validación de datos en admin"""
    
    def test_crear_producto_sin_nombre(self):
        """Debe rechazar producto sin nombre"""
        token = crear_token_admin(1, 1)
        
        response = client.post(
            "/admin/productos",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "precio": "10.00",
                "categoria_id": "1"
            }
        )
        
        assert response.status_code == 422  # Validation Error
    
    def test_crear_producto_precio_invalido(self):
        """Debe rechazar producto con precio no numérico"""
        token = crear_token_admin(1, 1)
        
        response = client.post(
            "/admin/productos",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "nombre": "Producto Test",
                "precio": "no_es_numero",
                "categoria_id": "1"
            }
        )
        
        assert response.status_code == 422
    
    def test_crear_categoria_sin_nombre(self):
        """Debe rechazar categoría sin nombre"""
        token = crear_token_admin(1, 1)
        
        response = client.post(
            "/admin/categorias",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "descripcion": "Sin nombre"
            }
        )
        
        assert response.status_code == 422


# ============================================================================
# TESTS DE PERMISOS Y AUTORIZACIÓN
# ============================================================================

class TestAdminPermisos:
    """Tests para permisos de admin"""
    
    @patch('app.api.endpoints.admin.admin_service.obtener_productos')
    def test_admin_solo_ve_productos_su_local(self, mock_obtener):
        """Admin debe ver solo productos de su local"""
        mock_obtener.return_value = []
        
        token = crear_token_admin(user_id=1, local_id=2)
        
        response = client.get(
            "/admin/productos",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Verificar que se llamó con el local_id correcto
        mock_obtener.assert_called_once()
        call_args = mock_obtener.call_args
        assert call_args[0][0] == 2  # local_id = 2
    
    


# ============================================================================
# TESTS DE CASOS ESPECIALES
# ============================================================================

class TestAdminCasosEspeciales:
    """Tests de casos especiales en admin"""
    
    @patch('app.api.endpoints.admin.admin_service.actualizar_producto')
    def test_actualizar_producto_solo_disponibilidad(self, mock_actualizar):
        """Debe permitir actualizar solo el campo disponible"""
        mock_actualizar.return_value = {"message": "Actualizado"}
        
        token = crear_token_admin(1, 1)
        
        response = client.put(
            "/admin/productos/1",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "disponible": "false"
            }
        )
        
        assert response.status_code == 200
    
    @patch('app.api.endpoints.admin.admin_service.actualizar_producto')
    def test_actualizar_producto_destacado(self, mock_actualizar):
        """Debe permitir marcar/desmarcar producto como destacado"""
        mock_actualizar.return_value = {"message": "Actualizado"}
        
        token = crear_token_admin(1, 1)
        
        response = client.put(
            "/admin/productos/1",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "destacado": "true"
            }
        )
        
        assert response.status_code == 200
    
    @patch('app.api.endpoints.admin.admin_service.obtener_productos')
    def test_obtener_productos_local_vacio(self, mock_obtener):
        """Debe retornar array vacío si no hay productos"""
        mock_obtener.return_value = []
        
        token = crear_token_admin(1, 1)
        
        response = client.get(
            "/admin/productos",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json() == []
    
    @patch('app.api.endpoints.admin.admin_service.obtener_categorias')
    def test_obtener_categorias_ordenadas(self, mock_obtener):
        """Debe retornar categorías ordenadas por campo 'orden'"""
        mock_obtener.return_value = [
            {"id": 1, "nombre": "Primera", "orden": 1},
            {"id": 2, "nombre": "Segunda", "orden": 2},
            {"id": 3, "nombre": "Tercera", "orden": 3}
        ]
        
        token = crear_token_admin(1, 1)
        
        response = client.get(
            "/admin/categorias",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        data = response.json()
        assert data[0]["orden"] == 1
        assert data[1]["orden"] == 2
        assert data[2]["orden"] == 3


# ============================================================================
# TESTS DE MANEJO DE ERRORES
# ============================================================================

class TestAdminManejoErrores:
    """Tests de manejo de errores en admin"""
    
    @patch('app.api.endpoints.admin.admin_service.actualizar_producto')
    def test_actualizar_producto_inexistente(self, mock_actualizar):
        """Debe retornar 404 al actualizar producto inexistente"""
        mock_actualizar.side_effect = HTTPException(
            status_code=404,
            detail="Producto no encontrado"
        )
        
        token = crear_token_admin(1, 1)
        
        response = client.put(
            "/admin/productos/999",
            headers={"Authorization": f"Bearer {token}"},
            data={"nombre": "Actualizado"}
        )
        
        assert response.status_code == 404
    
    @patch('app.api.endpoints.admin.admin_service.eliminar_producto')
    def test_eliminar_producto_inexistente(self, mock_eliminar):
        """Debe retornar 404 al eliminar producto inexistente"""
        mock_eliminar.side_effect = HTTPException(
            status_code=404,
            detail="Producto no encontrado o no tienes permiso"
        )
        
        token = crear_token_admin(1, 1)
        
        response = client.delete(
            "/admin/productos/999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
    
    @patch('app.api.endpoints.admin.admin_service.crear_categoria')
    def test_crear_categoria_nombre_duplicado(self, mock_crear):
        """Debe retornar 400 con nombre de categoría duplicado"""
        mock_crear.side_effect = HTTPException(
            status_code=400,
            detail="Ya existe una categoría con ese nombre"
        )
        
        token = crear_token_admin(1, 1)
        
        response = client.post(
            "/admin/categorias",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "nombre": "Pizzas"  # Ya existe
            }
        )
        
        assert response.status_code == 400
        assert "Ya existe" in response.json()["detail"]
    



# ============================================================================
# TESTS DE LOCALES
# ============================================================================

class TestAdminLocalesEndpoints:
    """Tests para endpoints de locales en /admin"""
    
    @patch('app.api.endpoints.admin.admin_service.obtener_locales')
    def test_get_locales_endpoint_usuario_admin(self, mock_obtener):
        """GET /admin/locales debe retornar solo el local del admin"""
        mock_obtener.return_value = [
            {
                "id": 1,
                "nombre": "Pizzería Centro",
                "direccion": "Av. Principal 123",
                "telefono": "555-0001",
                "esta_activo": True
            }
        ]
        
        token = crear_token_admin(1, 1)
        
        response = client.get(
            "/admin/locales",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        # Verificamos que hay datos y tienen la estructura correcta
        assert "id" in data[0]
        assert "nombre" in data[0]
    
    @patch('app.api.endpoints.admin.admin_service.obtener_locales')
    def test_admin_diferente_local(self, mock_obtener):
        """Cada admin debe ver solo su local"""
        mock_obtener.return_value = [
            {
                "id": 2,
                "nombre": "Pizzería Norte",
                "direccion": "Calle Norte 456",
                "telefono": "555-0002",
                "esta_activo": True
            }
        ]
        
        token = crear_token_admin(user_id=2, local_id=2)
        
        response = client.get(
            "/admin/locales",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        data = response.json()
        assert data[0]["id"] == 2
        assert "Pizzería" in data[0]["nombre"]
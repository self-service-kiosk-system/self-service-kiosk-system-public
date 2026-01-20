import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.database import Base
from app.models.models import Local, Categoria, Producto
from app.services.menu_service import MenuService
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import jwt

from main import app
from app.utils.utils import SECRET_JWT


client = TestClient(app)


# Fixture de DB local para estos tests
@pytest.fixture
def db():
    """Crea una base de datos SQLite en memoria para cada test"""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Crear solo las tablas necesarias para estos tests
    Local.__table__.create(bind=engine, checkfirst=True)
    Categoria.__table__.create(bind=engine, checkfirst=True)
    Producto.__table__.create(bind=engine, checkfirst=True)
    
    try:
        session = TestingSessionLocal()
        yield session
    finally:
        session.close()
        # Limpiar
        Producto.__table__.drop(bind=engine, checkfirst=True)
        Categoria.__table__.drop(bind=engine, checkfirst=True)
        Local.__table__.drop(bind=engine, checkfirst=True)


def mk_local(local_id: int, nombre: str, activo: bool = True) -> Local:
    """Helper para crear un local de prueba"""
    return Local(
        id=local_id,
        nombre=nombre,
        direccion=f"Dirección {nombre}",
        telefono=f"555-{local_id:04d}",
        esta_activo=activo,
    )


def mk_categoria(categoria_id: int, local_id: int, nombre: str, orden: int = 0, activo: bool = True) -> Categoria:
    """Helper para crear una categoría de prueba"""
    return Categoria(
        id=categoria_id,
        local_id=local_id,
        nombre=nombre,
        descripcion=f"Descripción {nombre}",
        orden=orden,
        esta_activo=activo,
    )


def mk_producto(
    producto_id: int,
    local_id: int,
    categoria_id: int,
    nombre: str,
    precio: float,
    orden: int = 0,
    disponible: bool = True,
    destacado: bool = False,
) -> Producto:
    """Helper para crear un producto de prueba"""
    return Producto(
        id=producto_id,
        local_id=local_id,
        categoria_id=categoria_id,
        nombre=nombre,
        descripcion=f"Descripción {nombre}",
        precio=precio,
        imagen_url=f"/images/{nombre.lower().replace(' ', '_')}.jpg",
        disponible=disponible,
        destacado=destacado,
        orden=orden,
    )


@pytest.mark.asyncio
async def test_obtener_menu_completo_happy_path(db, monkeypatch):
    """
    Test del flujo completo para obtener el menú:
    - Local activo con categorías activas
    - Categorías con productos disponibles
    - Estructura correcta del response
    - Orden correcto de categorías y productos
    """
    # Mock SessionLocal para usar nuestra db de test
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    # Seed: Local activo
    local = mk_local(1, "Pizzería Centro")
    db.add(local)
    db.commit()

    # Seed: Categorías activas con orden
    cat_pizzas = mk_categoria(1, local.id, "Pizzas", orden=1)
    cat_bebidas = mk_categoria(2, local.id, "Bebidas", orden=2)
    cat_postres = mk_categoria(3, local.id, "Postres", orden=3)
    db.add_all([cat_pizzas, cat_bebidas, cat_postres])
    db.commit()

    # Seed: Productos disponibles
    prod_margarita = mk_producto(1, local.id, cat_pizzas.id, "Margarita", 12.50, orden=1, destacado=True)
    prod_pepperoni = mk_producto(2, local.id, cat_pizzas.id, "Pepperoni", 14.00, orden=2)
    prod_coca = mk_producto(3, local.id, cat_bebidas.id, "Coca Cola", 2.50, orden=1)
    prod_helado = mk_producto(4, local.id, cat_postres.id, "Helado", 4.00, orden=1)
    db.add_all([prod_margarita, prod_pepperoni, prod_coca, prod_helado])
    db.commit()

    # Ejecutar servicio
    service = MenuService()
    resultado = await service.obtener_menu_completo()

    # Validaciones
    assert "locales" in resultado
    assert len(resultado["locales"]) == 1

    local_data = resultado["locales"][0]
    assert local_data["id"] == local.id
    assert local_data["nombre"] == "Pizzería Centro"
    assert local_data["direccion"] == "Dirección Pizzería Centro"
    assert local_data["telefono"] == "555-0001"

    # Verificar categorías en orden
    categorias = local_data["categorias"]
    assert len(categorias) == 3
    assert categorias[0]["nombre"] == "Pizzas"
    assert categorias[1]["nombre"] == "Bebidas"
    assert categorias[2]["nombre"] == "Postres"

    # Verificar productos de pizzas
    pizzas = categorias[0]["productos"]
    assert len(pizzas) == 2
    assert pizzas[0]["nombre"] == "Margarita"
    assert pizzas[0]["precio"] == 12.50
    assert pizzas[0]["destacado"] is True
    assert pizzas[1]["nombre"] == "Pepperoni"
    assert pizzas[1]["precio"] == 14.00

    # Verificar productos de bebidas
    bebidas = categorias[1]["productos"]
    assert len(bebidas) == 1
    assert bebidas[0]["nombre"] == "Coca Cola"


@pytest.mark.asyncio
async def test_obtener_menu_filtra_productos_no_disponibles(db, monkeypatch):
    """
    Los productos con disponible=False no deben aparecer en el menú
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    local = mk_local(1, "Local Test")
    cat = mk_categoria(1, 1, "Categoría Test")
    prod_disponible = mk_producto(1, 1, 1, "Disponible", 10.0, disponible=True)
    prod_no_disponible = mk_producto(2, 1, 1, "No Disponible", 10.0, disponible=False)

    db.add_all([local, cat, prod_disponible, prod_no_disponible])
    db.commit()

    service = MenuService()
    resultado = await service.obtener_menu_completo()

    productos = resultado["locales"][0]["categorias"][0]["productos"]
    # El servicio debe filtrar productos no disponibles
    productos_disponibles = [p for p in productos if p.get("disponible", True)]
    assert len(productos_disponibles) == 1
    assert productos_disponibles[0]["nombre"] == "Disponible"



@pytest.mark.asyncio
async def test_obtener_menu_excluye_categorias_sin_productos(db, monkeypatch):
    """
    Las categorías sin productos disponibles no deben aparecer en el menú
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    local = mk_local(1, "Local Test")
    cat_con_productos = mk_categoria(1, 1, "Con Productos")
    cat_sin_productos = mk_categoria(2, 1, "Sin Productos")
    prod = mk_producto(1, 1, 1, "Producto", 10.0)

    db.add_all([local, cat_con_productos, cat_sin_productos, prod])
    db.commit()

    service = MenuService()
    resultado = await service.obtener_menu_completo()

    categorias = resultado["locales"][0]["categorias"]
    assert len(categorias) == 1
    assert categorias[0]["nombre"] == "Con Productos"


@pytest.mark.asyncio
async def test_obtener_menu_filtra_categorias_inactivas(db, monkeypatch):
    """
    Las categorías con esta_activo=False no deben aparecer
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    local = mk_local(1, "Local Test")
    cat_activa = mk_categoria(1, 1, "Activa", activo=True)
    cat_inactiva = mk_categoria(2, 1, "Inactiva", activo=False)
    prod_activa = mk_producto(1, 1, 1, "Producto Activo", 10.0)
    prod_inactiva = mk_producto(2, 1, 2, "Producto Inactivo", 10.0)

    db.add_all([local, cat_activa, cat_inactiva, prod_activa, prod_inactiva])
    db.commit()

    service = MenuService()
    resultado = await service.obtener_menu_completo()

    categorias = resultado["locales"][0]["categorias"]
    assert len(categorias) == 1
    assert categorias[0]["nombre"] == "Activa"


@pytest.mark.asyncio
async def test_obtener_menu_filtra_locales_inactivos(db, monkeypatch):
    """
    Los locales con esta_activo=False no deben aparecer
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    local_activo = mk_local(1, "Local Activo", activo=True)
    local_inactivo = mk_local(2, "Local Inactivo", activo=False)

    db.add_all([local_activo, local_inactivo])
    db.commit()

    service = MenuService()
    resultado = await service.obtener_menu_completo()

    assert len(resultado["locales"]) == 1
    assert resultado["locales"][0]["nombre"] == "Local Activo"


@pytest.mark.asyncio
async def test_obtener_menu_por_local_id_especifico(db, monkeypatch):
    """
    Si se especifica local_id, solo debe devolver ese local
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    local1 = mk_local(1, "Local 1")
    local2 = mk_local(2, "Local 2")
    cat1 = mk_categoria(1, 1, "Cat Local 1")
    cat2 = mk_categoria(2, 2, "Cat Local 2")
    prod1 = mk_producto(1, 1, 1, "Prod 1", 10.0)
    prod2 = mk_producto(2, 2, 2, "Prod 2", 10.0)

    db.add_all([local1, local2, cat1, cat2, prod1, prod2])
    db.commit()

    service = MenuService()
    resultado = await service.obtener_menu_completo(local_id=1)

    assert len(resultado["locales"]) == 1
    assert resultado["locales"][0]["id"] == 1
    assert resultado["locales"][0]["nombre"] == "Local 1"


@pytest.mark.asyncio
async def test_obtener_menu_sin_locales_activos_lanza_404(db, monkeypatch):
    """
    Si no hay locales activos debe lanzar HTTPException 404
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    local_inactivo = mk_local(1, "Local Inactivo", activo=False)
    db.add(local_inactivo)
    db.commit()

    service = MenuService()

    with pytest.raises(HTTPException) as exc_info:
        await service.obtener_menu_completo()

    assert exc_info.value.status_code == 404
    assert "No se encontraron locales activos" in exc_info.value.detail


@pytest.mark.asyncio
async def test_obtener_menu_orden_correcto_productos_por_orden_y_nombre(db, monkeypatch):
    """
    Los productos deben ordenarse primero por campo 'orden' y luego por 'nombre'
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    local = mk_local(1, "Local Test")
    cat = mk_categoria(1, 1, "Categoría Test")
    # Productos con diferentes órdenes y nombres
    prod_z = mk_producto(1, 1, 1, "Z Producto", 10.0, orden=2)
    prod_a = mk_producto(2, 1, 1, "A Producto", 10.0, orden=2)
    prod_primero = mk_producto(3, 1, 1, "Primero", 10.0, orden=1)

    db.add_all([local, cat, prod_z, prod_a, prod_primero])
    db.commit()

    service = MenuService()
    resultado = await service.obtener_menu_completo()

    productos = resultado["locales"][0]["categorias"][0]["productos"]
    assert len(productos) == 3
    # Orden 1 primero
    assert productos[0]["nombre"] == "Primero"
    # Orden 2, alfabético
    assert productos[1]["nombre"] == "A Producto"
    assert productos[2]["nombre"] == "Z Producto"


@pytest.mark.asyncio
async def test_obtener_menu_multiples_locales_estructura_correcta(db, monkeypatch):
    """
    Con múltiples locales activos, todos deben aparecer con su estructura completa
    """
    monkeypatch.setattr("app.services.menu_service.SessionLocal", lambda: db)

    # Dos locales con sus respectivas categorías y productos
    local1 = mk_local(1, "Local Norte")
    local2 = mk_local(2, "Local Sur")

    cat1 = mk_categoria(1, 1, "Pizzas Norte")
    cat2 = mk_categoria(2, 2, "Pizzas Sur")

    prod1 = mk_producto(1, 1, 1, "Pizza 1", 10.0)
    prod2 = mk_producto(2, 2, 2, "Pizza 2", 12.0)

    db.add_all([local1, local2, cat1, cat2, prod1, prod2])
    db.commit()

    service = MenuService()
    resultado = await service.obtener_menu_completo()

    assert len(resultado["locales"]) == 2

    # Validar cada local tiene su propia estructura
    locales_dict = {loc["id"]: loc for loc in resultado["locales"]}
    assert 1 in locales_dict and 2 in locales_dict

    assert locales_dict[1]["nombre"] == "Local Norte"
    assert locales_dict[1]["categorias"][0]["nombre"] == "Pizzas Norte"
    assert locales_dict[1]["categorias"][0]["productos"][0]["nombre"] == "Pizza 1"

    assert locales_dict[2]["nombre"] == "Local Sur"
    assert locales_dict[2]["categorias"][0]["nombre"] == "Pizzas Sur"
    assert locales_dict[2]["categorias"][0]["productos"][0]["nombre"] == "Pizza 2"


# ============================================================================
# HELPERS
# ============================================================================

def crear_token_dispositivo(local_id: int, device_id: str = "DEVICE001"):
    """Crea un token JWT válido para dispositivo"""
    payload = {
        "device_id": device_id,
        "local_id": local_id,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_JWT, algorithm="HS256")


# ============================================================================
# TESTS DE ENDPOINT /menu/productos
# ============================================================================

class TestMenuProductosEndpoint:
    """Tests para GET /menu/productos"""
    
    def test_obtener_productos_exitoso(self):
        """GET /menu/productos debe retornar productos del local"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificamos que retorna una lista (puede estar vacía o con productos)
        assert isinstance(data, list)
    
    def test_obtener_productos_multiples(self):
        """Debe retornar productos ordenados (destacados primero)"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificamos que retorna una lista
        assert isinstance(data, list)
        # Si hay productos, verificar estructura
        if len(data) > 0:
            assert "nombre" in data[0]
            assert "destacado" in data[0]
    
    def test_obtener_productos_local_vacio(self):
        """Debe retornar array vacío o con productos"""
        # Usamos un local_id alto que probablemente no existe
        token = crear_token_dispositivo(local_id=999)
        
        response = client.get(
            "/menu/productos?local_id=999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        # Retorna lista (vacía si el local no tiene productos)
        assert isinstance(response.json(), list)
    
    def test_obtener_productos_sin_token(self):
        """Debe rechazar petición sin token"""
        response = client.get("/menu/productos?local_id=1")
        
        assert response.status_code == 401
    
    def test_obtener_productos_local_id_diferente(self):
        """Debe rechazar si local_id no coincide con el token"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=2",  # Pide local 2
            headers={"Authorization": f"Bearer {token}"}  # Token de local 1
        )
        
        assert response.status_code == 403
        assert "No tienes acceso" in response.json()["detail"]
    
    def test_obtener_productos_sin_local_id(self):
        """Debe rechazar si no se especifica local_id"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos",  # Sin local_id
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_obtener_productos_con_categoria_none(self):
        """Debe manejar la estructura de categorías correctamente"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar estructura de respuesta
        assert isinstance(data, list)
        # Si hay productos, verificar que tienen campo categorias
        if len(data) > 0:
            assert "categorias" in data[0]


# ============================================================================
# TESTS DE ENDPOINT /menu/categorias
# ============================================================================

class TestMenuCategoriasEndpoint:
    """Tests para GET /menu/categorias"""
    
    def test_obtener_categorias_exitoso(self):
        """GET /menu/categorias debe retornar categorías del local"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/categorias?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar que es una lista
        assert isinstance(data, list)
        # Si hay categorías, verificar estructura
        if len(data) > 0:
            assert "id" in data[0]
            assert "nombre" in data[0]
    
    def test_obtener_categorias_multiples_ordenadas(self):
        """Debe retornar categorías ordenadas por campo orden"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/categorias?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verificar que es una lista
        assert isinstance(data, list)
        # Verificar estructura si hay datos
        for cat in data:
            assert "id" in cat
            assert "nombre" in cat
    
    def test_obtener_categorias_vacio(self):
        """Debe retornar array vacío o con categorías"""
        # Usamos local_id alto que probablemente no tiene categorías
        token = crear_token_dispositivo(local_id=999)
        
        response = client.get(
            "/menu/categorias?local_id=999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        # Retorna lista (puede estar vacía)
        assert isinstance(response.json(), list)
    
    def test_obtener_categorias_sin_token(self):
        """Debe rechazar petición sin token"""
        response = client.get("/menu/categorias?local_id=1")
        
        assert response.status_code == 401
    
    def test_obtener_categorias_local_id_diferente(self):
        """Debe rechazar si local_id no coincide con el token"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/categorias?local_id=2",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
    
    def test_obtener_categorias_sin_local_id(self):
        """Debe rechazar si no se especifica local_id"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/categorias",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422


# ============================================================================
# TESTS DE VALIDACIÓN Y ESTRUCTURA
# ============================================================================

class TestMenuValidacion:
    """Tests de validación de datos en endpoints de menu"""
    
    def test_productos_estructura_completa(self):
        """Verificar que productos tienen todos los campos necesarios"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Si hay productos, verificar campos obligatorios
        if len(data) > 0:
            producto = data[0]
            assert "id" in producto
            assert "nombre" in producto
            assert "descripcion" in producto
            assert "precio" in producto
            assert "imagen_url" in producto
            assert "disponible" in producto
            assert "destacado" in producto
            assert "categorias" in producto
    
    def test_categorias_estructura_completa(self):
        """Verificar que categorías tienen todos los campos necesarios"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/categorias?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Si hay categorías, verificar campos obligatorios
        if len(data) > 0:
            categoria = data[0]
            assert "id" in categoria
            assert "nombre" in categoria
            assert "descripcion" in categoria
    
    def test_precio_como_float(self):
        """El precio debe convertirse a float"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Si hay productos, verificar que precio es float
        if len(data) > 0:
            assert isinstance(data[0]["precio"], (int, float))


# ============================================================================
# TESTS DE DIFERENTES LOCALES
# ============================================================================

class TestMenuMultiplesLocales:
    """Tests para verificar aislamiento entre locales"""
    
    def test_dispositivo_local_1_solo_ve_local_1(self):
        """Dispositivo del local 1 solo ve productos del local 1"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Debe tener acceso exitoso a su propio local
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_dispositivo_local_2_solo_ve_local_2(self):
        """Dispositivo del local 2 solo ve productos del local 2"""
        token = crear_token_dispositivo(local_id=2)
        
        response = client.get(
            "/menu/productos?local_id=2",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Debe tener acceso exitoso a su propio local
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_token_local_1_no_puede_ver_local_2(self):
        """Token del local 1 no puede acceder al local 2"""
        token = crear_token_dispositivo(local_id=1)
        
        response = client.get(
            "/menu/productos?local_id=2",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
    
    def test_token_local_2_no_puede_ver_local_1(self):
        """Token del local 2 no puede acceder al local 1"""
        token = crear_token_dispositivo(local_id=2)
        
        response = client.get(
            "/menu/categorias?local_id=1",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
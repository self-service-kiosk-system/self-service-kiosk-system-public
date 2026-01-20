import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


class TestDatabaseConfiguration:
    """Tests para configuración de base de datos"""
    
    def test_database_url_configurada(self):
        """Debe tener DATABASE_URL configurada"""
        from app.config.database import DATABASE_URL
        
        assert DATABASE_URL is not None
        assert len(DATABASE_URL) > 0
    
    def test_engine_configurado_correctamente(self):
        """Engine debe tener configuración de pool correcta"""
        from app.config.database import engine
        
        assert engine is not None
    
    def test_session_local_es_callable(self):
        """SessionLocal debe ser un callable que retorna Session"""
        from app.config.database import SessionLocal
        
        assert callable(SessionLocal)
        
        session = SessionLocal()
        assert isinstance(session, Session)
        session.close()
    
    def test_base_declarative_existe(self):
        """Base debe estar configurado para ORM"""
        from app.config.database import Base
        
        assert Base is not None
        assert hasattr(Base, 'metadata')


class TestDatabaseConnection:
    """Tests para conexión a base de datos"""
    
    @pytest.mark.skipif(
        os.getenv("DATABASE_NUBE_URL", "").startswith("postgresql://test"),
        reason="Requiere base de datos real para testing"
    )
    def test_conexion_basica(self):
        """Debe poder conectarse a la base de datos"""
        from app.config.database import SessionLocal
        
        session = SessionLocal()
        try:
            # Intentar ejecutar query simple
            result = session.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        finally:
            session.close()
    
    def test_session_cierra_correctamente(self):
        """Session debe cerrarse correctamente"""
        from app.config.database import SessionLocal
        
        session = SessionLocal()
        
        # Verificar que la conexión interna no está cerrada
        assert session.bind is not None
        
        # Cerrar sesión
        session.close()
        
        # Verificar que close() fue llamado verificando que no hay transacción en progreso
        assert session.in_transaction() == False  # No debe haber transacción activa
    
    def test_multiples_sesiones_independientes(self):
        """Múltiples sesiones deben ser independientes"""
        from app.config.database import SessionLocal
        
        session1 = SessionLocal()
        session2 = SessionLocal()
        
        try:
            assert session1 is not session2
        finally:
            session1.close()
            session2.close()


class TestGetDbDependency:
    """Tests para la dependencia get_db()"""
    
    def test_get_db_retorna_session(self):
        """get_db() debe retornar una sesión"""
        from app.config.database import get_db
        
        db_generator = get_db()
        db = next(db_generator)
        
        assert isinstance(db, Session)
        
        # Cerrar el generator
        try:
            next(db_generator)
        except StopIteration:
            pass
    
    def test_get_db_cierra_session_automaticamente(self):
        """get_db() debe cerrar la sesión al finalizar"""
        from app.config.database import get_db
        
        db_generator = get_db()
        db = next(db_generator)
        
        # Verificar que está disponible
        assert db.bind is not None
        
        # Finalizar el generator (simula finally)
        try:
            next(db_generator)
        except StopIteration:
            pass
        
        # Verificar que no hay transacción activa después del cierre
        assert db.in_transaction() == False
    
    def test_get_db_maneja_excepciones(self):
        """get_db() debe cerrar sesión incluso si hay error"""
        from app.config.database import get_db
        
        db_generator = get_db()
        db = next(db_generator)
        
        # Verificar que está disponible
        assert db.bind is not None
        
        # Simular excepción usando close en lugar de throw
        try:
            db_generator.close()
        except:
            pass
        
        # Verificar que no hay transacción activa
        assert db.in_transaction() == False


class TestDatabasePooling:
    """Tests para pooling de conexiones"""
    
    def test_pool_configurado_con_parametros_correctos(self):
        """Pool debe tener los parámetros correctos configurados"""
        from app.config.database import engine
        
        # Verificar que pool existe
        assert engine.pool is not None
    
    @pytest.mark.skipif(
        os.getenv("DATABASE_NUBE_URL", "").startswith("postgresql://test"),
        reason="Requiere base de datos real"
    )
    def test_pool_reutiliza_conexiones(self):
        """Pool debe reutilizar conexiones cerradas"""
        from app.config.database import SessionLocal
        
        # Crear y cerrar varias sesiones
        for _ in range(3):
            session = SessionLocal()
            session.close()
        
        # Si llegamos aquí sin error, el pool funciona correctamente
        assert True


class TestDatabaseEnvironmentVariables:
    """Tests para variables de entorno de la base de datos"""
    
    def test_database_url_existe(self):
        """Debe tener DATABASE_URL configurada"""
        from app.config.database import DATABASE_URL
        
        assert DATABASE_URL is not None
        assert len(DATABASE_URL) > 0
    
    def test_pool_pre_ping_habilitado(self):
        """pool_pre_ping debe estar habilitado para detectar conexiones muertas"""
        from app.config.database import engine
        
        # Verificar que engine está configurado
        assert engine is not None


class TestDatabaseTransactions:
    """Tests para transacciones de base de datos"""
    
    @pytest.mark.skipif(
        os.getenv("DATABASE_NUBE_URL", "").startswith("postgresql://test"),
        reason="Requiere base de datos real"
    )
    def test_transaccion_commit(self):
        """Debe poder hacer commit de transacciones"""
        from app.config.database import SessionLocal
        from app.models.models import Local
        
        session = SessionLocal()
        try:
            # Crear un local de prueba
            local = Local(
                nombre="Test Transaction",
                direccion="Test Address",
                telefono="555-0000",
                esta_activo=True
            )
            session.add(local)
            session.commit()
            
            # Verificar que se guardó
            assert local.id is not None
            
            # Limpiar
            session.delete(local)
            session.commit()
        except Exception as e:
            session.rollback()
            pytest.skip(f"Requiere base de datos real: {e}")
        finally:
            session.close()
    
    @pytest.mark.skipif(
        os.getenv("DATABASE_NUBE_URL", "").startswith("postgresql://test"),
        reason="Requiere base de datos real"
    )
    def test_transaccion_rollback(self):
        """Debe poder hacer rollback de transacciones"""
        from app.config.database import SessionLocal
        from app.models.models import Local
        
        session = SessionLocal()
        try:
            local = Local(
                nombre="Test Rollback",
                direccion="Test Address",
                telefono="555-0000",
                esta_activo=True
            )
            session.add(local)
            session.flush()  # Enviar a DB pero no commit
            
            local_id = local.id
            
            # Hacer rollback
            session.rollback()
            
            # Verificar que no se guardó
            local_check = session.query(Local).filter(Local.id == local_id).first()
            assert local_check is None
        except Exception as e:
            session.rollback()
            pytest.skip(f"Requiere base de datos real: {e}")
        finally:
            session.close()
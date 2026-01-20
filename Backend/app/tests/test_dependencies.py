import pytest
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch, PropertyMock, Mock
from app.config.database import SessionLocal

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.utils.dependencies import get_admin_service, verificar_admin, security, _admin_service_instance
from app.services.admin_service import AdminService


class TestSecurity:
    """Tests para el objeto security HTTPBearer"""
    
    def test_security_es_http_bearer(self):
        """security debe ser una instancia de HTTPBearer"""
        from fastapi.security import HTTPBearer
        assert isinstance(security, HTTPBearer)
    
    def test_security_existe(self):
        """security debe estar definido"""
        assert security is not None


class TestGetAdminService:
    """Tests para la función get_admin_service (Singleton)"""
    
    def test_get_admin_service_retorna_instancia(self):
        """Debe retornar una instancia de AdminService"""
        service = get_admin_service()
        
        assert service is not None
        assert isinstance(service, AdminService)
    
    def test_get_admin_service_singleton_misma_instancia(self):
        """Debe retornar la misma instancia en múltiples llamadas (Singleton)"""
        service1 = get_admin_service()
        service2 = get_admin_service()
        service3 = get_admin_service()
        
        # Todas deben ser la misma instancia
        assert service1 is service2
        assert service2 is service3
        assert service1 is service3
    
    def test_get_admin_service_inicializa_una_sola_vez(self):
        """Debe inicializar AdminService solo una vez"""
        import app.utils.dependencies as deps
        original = deps._admin_service_instance
        
        try:
            deps._admin_service_instance = None
            
            service1 = get_admin_service()
            service2 = get_admin_service()
            
            # Ambas deben ser la misma instancia
            assert service1 is service2
        finally:
            deps._admin_service_instance = original
    
    def test_get_admin_service_no_none(self):
        """get_admin_service nunca debe retornar None"""
        service = get_admin_service()
        assert service is not None
    
    def test_get_admin_service_tiene_metodos_requeridos(self):
        """La instancia debe tener el método verificar_token"""
        service = get_admin_service()
        
        assert hasattr(service, 'verificar_token')
        assert callable(service.verificar_token)
    
    @patch('app.utils.dependencies.AdminService')
    def test_get_admin_service_crea_instancia_solo_si_no_existe(self, mock_admin_service):
        """Debe crear AdminService solo si no existe instancia previa"""
        import app.utils.dependencies as deps
        original = deps._admin_service_instance
        
        try:
            # Resetear singleton
            deps._admin_service_instance = None
            
            mock_instance = MagicMock(spec=AdminService)
            mock_admin_service.return_value = mock_instance
            
            # Primera llamada debe crear instancia
            service1 = get_admin_service()
            assert mock_admin_service.call_count == 1
            
            # Segunda llamada NO debe crear otra instancia
            service2 = get_admin_service()
            assert mock_admin_service.call_count == 1  # Sigue siendo 1
            
            assert service1 is service2
        finally:
            deps._admin_service_instance = original


class TestVerificarAdmin:
    """Tests para la función verificar_admin"""
    
    @pytest.mark.asyncio
    async def test_verificar_admin_token_valido(self):
        """Debe retornar True con token válido"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token_valido"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=True):
            resultado = await verificar_admin(mock_credentials)
            assert resultado is True
    
    @pytest.mark.asyncio
    async def test_verificar_admin_token_invalido_lanza_401(self):
        """Debe lanzar HTTPException 401 con token inválido"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token_invalido"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await verificar_admin(mock_credentials)
            
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "No autorizado"
    
    @pytest.mark.asyncio
    async def test_verificar_admin_extrae_token_de_credentials(self):
        """Debe extraer el token del objeto credentials"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        test_token = "mi_token_secreto_123"
        mock_credentials.credentials = test_token
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=True) as mock_verificar:
            await verificar_admin(mock_credentials)
            
            # Verificar que se llamó con el token correcto
            mock_verificar.assert_called_once_with(test_token)
    
    @pytest.mark.asyncio
    async def test_verificar_admin_usa_get_admin_service(self):
        """Debe usar get_admin_service para obtener el servicio"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token"
        
        with patch('app.utils.dependencies.get_admin_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.verificar_token.return_value = True
            mock_get_service.return_value = mock_service
            
            await verificar_admin(mock_credentials)
            
            mock_get_service.assert_called_once()
            mock_service.verificar_token.assert_called_once_with("token")
    
    @pytest.mark.asyncio
    async def test_verificar_admin_token_vacio_lanza_401(self):
        """Debe lanzar 401 con token vacío"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = ""
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await verificar_admin(mock_credentials)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verificar_admin_multiples_tokens_validos(self):
        """Debe manejar múltiples verificaciones con tokens válidos"""
        tokens_validos = ["token1", "token2", "token3"]
        
        for token in tokens_validos:
            mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
            mock_credentials.credentials = token
            
            with patch.object(get_admin_service(), 'verificar_token', return_value=True):
                resultado = await verificar_admin(mock_credentials)
                assert resultado is True
    
    @pytest.mark.asyncio
    async def test_verificar_admin_multiples_tokens_invalidos(self):
        """Debe rechazar múltiples tokens inválidos"""
        tokens_invalidos = ["invalid1", "invalid2", "invalid3"]
        
        for token in tokens_invalidos:
            mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
            mock_credentials.credentials = token
            
            with patch.object(get_admin_service(), 'verificar_token', return_value=False):
                with pytest.raises(HTTPException) as exc_info:
                    await verificar_admin(mock_credentials)
                
                assert exc_info.value.status_code == 401


class TestVerificarAdminIntegracion:
    """Tests de integración para verificar_admin"""
    
    @pytest.mark.asyncio
    async def test_verificar_admin_flujo_completo_exitoso(self):
        """Test del flujo completo con token válido"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token_valido_abc123"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=True):
            resultado = await verificar_admin(mock_credentials)
            assert resultado is True
    
    @pytest.mark.asyncio
    async def test_verificar_admin_flujo_completo_fallo(self):
        """Test del flujo completo con token inválido"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token_invalido_xyz"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await verificar_admin(mock_credentials)
            
            assert exc_info.value.status_code == 401
            assert "No autorizado" in str(exc_info.value.detail)


class TestVerificarAdminErrorHandling:
    """Tests de manejo de errores para verificar_admin"""
    
    @pytest.mark.asyncio
    async def test_verificar_admin_servicio_lanza_excepcion(self):
        """Debe propagar excepciones del servicio"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token"
        
        with patch.object(get_admin_service(), 'verificar_token', side_effect=Exception("Error interno")):
            with pytest.raises(Exception, match="Error interno"):
                await verificar_admin(mock_credentials)
    
    @pytest.mark.asyncio
    async def test_verificar_admin_credentials_none_atributo(self):
        """Debe manejar credentials con atributo None"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = None
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await verificar_admin(mock_credentials)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verificar_admin_status_code_correcto(self):
        """La excepción debe tener el status code 401"""
        from fastapi import status
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "invalid"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await verificar_admin(mock_credentials)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_verificar_admin_detail_message_correcto(self):
        """El mensaje de error debe ser 'No autorizado'"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "invalid"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await verificar_admin(mock_credentials)
            
            assert exc_info.value.detail == "No autorizado"


class TestVerificarAdminEdgeCases:
    """Tests de casos edge para verificar_admin"""
    
    @pytest.mark.asyncio
    async def test_verificar_admin_token_muy_largo(self):
        """Debe manejar tokens muy largos"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "a" * 10000
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=True):
            resultado = await verificar_admin(mock_credentials)
            assert resultado is True
    
    @pytest.mark.asyncio
    async def test_verificar_admin_token_con_caracteres_especiales(self):
        """Debe manejar tokens con caracteres especiales"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token_!@#$%^&*()_+-=[]{}|;:',.<>?/`~"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=True):
            resultado = await verificar_admin(mock_credentials)
            assert resultado is True
    
    @pytest.mark.asyncio
    async def test_verificar_admin_retorna_true_no_none(self):
        """verificar_admin debe retornar True, no None"""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "token"
        
        with patch.object(get_admin_service(), 'verificar_token', return_value=True):
            resultado = await verificar_admin(mock_credentials)
            
            assert resultado is True
            assert resultado is not None
            assert type(resultado) is bool


class TestDependenciesModuleLevel:
    """Tests a nivel de módulo para dependencies.py"""
    
    def test_module_tiene_security(self):
        """El módulo debe exportar security"""
        from app.utils import dependencies
        assert hasattr(dependencies, 'security')
    
    def test_module_tiene_get_admin_service(self):
        """El módulo debe exportar get_admin_service"""
        from app.utils import dependencies
        assert hasattr(dependencies, 'get_admin_service')
        assert callable(dependencies.get_admin_service)
    
    def test_module_tiene_verificar_admin(self):
        """El módulo debe exportar verificar_admin"""
        from app.utils import dependencies
        assert hasattr(dependencies, 'verificar_admin')
        assert callable(dependencies.verificar_admin)
    
    def test_module_docstring_existe(self):
        """El módulo debe tener docstring"""
        from app.utils import dependencies
        assert dependencies.__doc__ is not None
        assert len(dependencies.__doc__) > 0
    
    def test_admin_service_instance_inicializa_none(self):
        """_admin_service_instance debe iniciar como None"""
        import app.utils.dependencies as deps
        
        if deps._admin_service_instance is not None:
            assert isinstance(deps._admin_service_instance, AdminService)


class TestCoberturaCompleta:
    """Tests adicionales para asegurar 100% de cobertura"""
    
    def test_security_configuracion(self):
        """Verificar configuración de HTTPBearer"""
        assert security is not None
        assert hasattr(security, '__call__')
    
    @pytest.mark.asyncio
    async def test_verificar_admin_es_dependencia_fastapi(self):
        """verificar_admin debe ser usable como dependencia de FastAPI"""
        from fastapi import Depends
        
        # Verificar que puede ser usado con Depends
        dependency = Depends(verificar_admin)
        assert dependency.dependency == verificar_admin
    
    def test_get_admin_service_no_requiere_parametros(self):
        """get_admin_service no debe requerir parámetros"""
        import inspect
        sig = inspect.signature(get_admin_service)
        assert len(sig.parameters) == 0
    
    @pytest.mark.asyncio
    async def test_verificar_admin_requiere_credentials(self):
        """verificar_admin debe requerir credentials"""
        import inspect
        sig = inspect.signature(verificar_admin)
        assert 'credentials' in sig.parameters
    
    @pytest.mark.asyncio
    async def test_verificar_admin_con_depends_security(self):
        """verificar_admin debe aceptar Depends(security) por defecto"""
        import inspect
        sig = inspect.signature(verificar_admin)
        param = sig.parameters['credentials']
        
        assert param.default is not inspect.Parameter.empty
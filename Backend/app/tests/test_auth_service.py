import pytest
import jwt
from fastapi import HTTPException
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.services import verify_token
from app.utils.utils import SECRET_JWT, AUTHORIZED_DEVICES


class TestVerifyTokenService:
    """Tests para el servicio verify_token"""
    
    @pytest.mark.asyncio
    async def test_verify_valid_token(self):
        """Test: Verificar token válido"""
        # Crear token válido
        token_data = {"device_id": "raspberry_1"}
        token = jwt.encode(token_data, SECRET_JWT, algorithm="HS256")
        
        result = await verify_token(f"Bearer {token}")
        
        assert result["device_id"] == "raspberry_1"
    
    @pytest.mark.asyncio
    async def test_verify_token_without_bearer(self):
        """Test: Falla sin prefijo Bearer"""
        token_data = {"device_id": "raspberry_1"}
        token = jwt.encode(token_data, SECRET_JWT, algorithm="HS256")
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(token)  # Sin "Bearer"
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_invalid_jwt(self):
        """Test: Token JWT malformado"""
        with pytest.raises(HTTPException) as exc_info:
            await verify_token("Bearer token_invalido_123")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_wrong_secret(self):
        """Test: Token firmado con secreto incorrecto"""
        token_data = {"device_id": "raspberry_1"}
        token = jwt.encode(token_data, "secreto_incorrecto", algorithm="HS256")
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(f"Bearer {token}")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_verify_token_missing_device_id(self):
        """Test: Token sin device_id"""
        token_data = {"other_field": "value"}
        token = jwt.encode(token_data, SECRET_JWT, algorithm="HS256")
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(f"Bearer {token}")
        
        assert exc_info.value.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
from typing import Optional
from fastapi import Header, HTTPException
import jwt
from app.utils.utils import SECRET_JWT


async def verify_token(authorization: Optional[str] = Header(None)):
    """Verifica tokens JWT tanto de dispositivos como de administradores"""
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    
    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(token, SECRET_JWT, algorithms=["HS256"])
        
        #Validar que sea un token de dispositivo O de admin
        es_dispositivo = "device_id" in payload
        es_admin = "user_id" in payload and "local_id" in payload
        
        if not es_dispositivo and not es_admin:
            raise HTTPException(
                status_code=401, 
                detail="Token inválido: no es de dispositivo ni de admin"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
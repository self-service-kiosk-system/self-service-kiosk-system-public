import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch
from app.utils.utils import ejecutar_servicio, SECRET_JWT, AUTHORIZED_DEVICES


class TestEjecutarServicio:
    """Tests para la función ejecutar_servicio"""
    
    @pytest.mark.asyncio
    async def test_ejecutar_servicio_exitoso(self):
        """Debe ejecutar operación exitosa y retornar resultado"""
        async def operacion_exitosa():
            return {"status": "success", "data": "test"}
        
        resultado = await ejecutar_servicio(operacion_exitosa())
        
        assert resultado == {"status": "success", "data": "test"}
    
    @pytest.mark.asyncio
    async def test_ejecutar_servicio_con_valor_simple(self):
        """Debe retornar valores simples correctamente"""
        async def operacion_simple():
            return 42
        
        resultado = await ejecutar_servicio(operacion_simple())
        
        assert resultado == 42
    
    @pytest.mark.asyncio
    async def test_ejecutar_servicio_con_none(self):
        """Debe manejar retorno None correctamente"""
        async def operacion_none():
            return None
        
        resultado = await ejecutar_servicio(operacion_none())
        
        assert resultado is None
    
    @pytest.mark.asyncio
    async def test_ejecutar_servicio_con_lista(self):
        """Debe retornar listas correctamente"""
        async def operacion_lista():
            return [1, 2, 3, 4, 5]
        
        resultado = await ejecutar_servicio(operacion_lista())
        
        assert resultado == [1, 2, 3, 4, 5]
    
    @pytest.mark.asyncio
    async def test_ejecutar_servicio_con_diccionario_complejo(self):
        """Debe retornar diccionarios complejos correctamente"""
        async def operacion_compleja():
            return {
                "id": 1,
                "nombre": "Test",
                "items": [{"id": 1}, {"id": 2}],
                "metadata": {"created": "2024-01-01"}
            }
        
        resultado = await ejecutar_servicio(operacion_compleja())
        
        assert resultado["id"] == 1
        assert len(resultado["items"]) == 2
        assert resultado["metadata"]["created"] == "2024-01-01"


class TestEjecutarServicioHTTPException:
    """Tests para manejo de HTTPException en ejecutar_servicio"""
    
    @pytest.mark.asyncio
    async def test_reelanza_http_exception_401(self):
        """Debe re-lanzar HTTPException 401 sin modificar"""
        async def operacion_con_error_401():
            raise HTTPException(status_code=401, detail="No autorizado")
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_error_401())
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "No autorizado"
    
    @pytest.mark.asyncio
    async def test_reelanza_http_exception_404(self):
        """Debe re-lanzar HTTPException 404 sin modificar"""
        async def operacion_con_error_404():
            raise HTTPException(status_code=404, detail="No encontrado")
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_error_404())
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "No encontrado"
    
    @pytest.mark.asyncio
    async def test_reelanza_http_exception_403(self):
        """Debe re-lanzar HTTPException 403 sin modificar"""
        async def operacion_con_error_403():
            raise HTTPException(status_code=403, detail="Acceso denegado")
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_error_403())
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Acceso denegado"
    
    @pytest.mark.asyncio
    async def test_reelanza_http_exception_con_headers(self):
        """Debe preservar headers en HTTPException"""
        async def operacion_con_headers():
            raise HTTPException(
                status_code=401,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_headers())
        
        assert exc_info.value.status_code == 401
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    
    @pytest.mark.asyncio
    async def test_reelanza_http_exception_500(self):
        """Debe re-lanzar HTTPException 500 directamente"""
        async def operacion_con_error_500():
            raise HTTPException(status_code=500, detail="Error interno")
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_error_500())
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Error interno"


class TestEjecutarServicioExcepcionGenerica:
    """Tests para manejo de excepciones genéricas en ejecutar_servicio"""
    
    @pytest.mark.asyncio
    async def test_convierte_exception_generica_a_500(self):
        """Debe convertir Exception genérica a HTTPException 500"""
        async def operacion_con_error_generico():
            raise Exception("Error inesperado")
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_error_generico())
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Error inesperado"
    
    @pytest.mark.asyncio
    async def test_convierte_value_error_a_500(self):
        """Debe convertir ValueError a HTTPException 500"""
        async def operacion_con_value_error():
            raise ValueError("Valor inválido")
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_value_error())
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Valor inválido"
    
    @pytest.mark.asyncio
    async def test_convierte_key_error_a_500(self):
        """Debe convertir KeyError a HTTPException 500"""
        async def operacion_con_key_error():
            data = {}
            return data["clave_inexistente"]
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_key_error())
        
        assert exc_info.value.status_code == 500
        assert "'clave_inexistente'" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_convierte_type_error_a_500(self):
        """Debe convertir TypeError a HTTPException 500"""
        async def operacion_con_type_error():
            return "string" + 123
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_type_error())
        
        assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_convierte_attribute_error_a_500(self):
        """Debe convertir AttributeError a HTTPException 500"""
        async def operacion_con_attribute_error():
            obj = None
            return obj.atributo_inexistente
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_attribute_error())
        
        assert exc_info.value.status_code == 500
        assert "NoneType" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_preserva_mensaje_error_original(self):
        """Debe preservar el mensaje de error original"""
        mensaje_error = "Este es un mensaje de error muy específico"
        
        async def operacion_con_mensaje_especifico():
            raise RuntimeError(mensaje_error)
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_mensaje_especifico())
        
        assert exc_info.value.detail == mensaje_error
    
    @pytest.mark.asyncio
    async def test_maneja_excepcion_sin_mensaje(self):
        """Debe manejar excepciones sin mensaje"""
        async def operacion_con_excepcion_vacia():
            raise Exception()
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_con_excepcion_vacia())
        
        assert exc_info.value.status_code == 500


class TestEjecutarServicioCasosEspeciales:
    """Tests para casos especiales de ejecutar_servicio"""
    
    @pytest.mark.asyncio
    async def test_operacion_con_await_interno(self):
        """Debe manejar operaciones con await interno"""
        async def operacion_interna():
            return "resultado interno"
        
        async def operacion_externa():
            resultado = await operacion_interna()
            return f"Procesado: {resultado}"
        
        resultado = await ejecutar_servicio(operacion_externa())
        
        assert resultado == "Procesado: resultado interno"
    
    @pytest.mark.asyncio
    async def test_operacion_con_sleep(self):
        """Debe manejar operaciones con sleep"""
        import asyncio
        
        async def operacion_con_delay():
            await asyncio.sleep(0.001)
            return "completado"
        
        resultado = await ejecutar_servicio(operacion_con_delay())
        
        assert resultado == "completado"
    
    @pytest.mark.asyncio
    async def test_operacion_con_multiples_awaits(self):
        """Debe manejar operaciones con múltiples awaits"""
        async def paso1():
            return 10
        
        async def paso2(valor):
            return valor * 2
        
        async def operacion_completa():
            r1 = await paso1()
            r2 = await paso2(r1)
            return r2
        
        resultado = await ejecutar_servicio(operacion_completa())
        
        assert resultado == 20
    
    @pytest.mark.asyncio
    async def test_operacion_con_try_except_interno(self):
        """Debe manejar operaciones con try-except interno"""
        async def operacion_con_manejo_error():
            try:
                raise ValueError("Error interno")
            except ValueError:
                return "Error manejado internamente"
        
        resultado = await ejecutar_servicio(operacion_con_manejo_error())
        
        assert resultado == "Error manejado internamente"
    
    @pytest.mark.asyncio
    async def test_operacion_con_contexto_complejo(self):
        """Debe manejar operaciones con contexto complejo"""
        contador = {"valor": 0}
        
        async def operacion_con_estado():
            contador["valor"] += 1
            return contador["valor"]
        
        resultado1 = await ejecutar_servicio(operacion_con_estado())
        resultado2 = await ejecutar_servicio(operacion_con_estado())
        
        assert resultado1 == 1
        assert resultado2 == 2


class TestConstantesUtils:
    """Tests para constantes definidas en utils"""
    
    def test_secret_jwt_existe(self):
        """Debe tener SECRET_JWT definido"""
        assert SECRET_JWT is not None
        assert isinstance(SECRET_JWT, str)
        assert len(SECRET_JWT) > 0
    
    def test_authorized_devices_existe(self):
        """Debe tener AUTHORIZED_DEVICES definido"""
        assert AUTHORIZED_DEVICES is not None
        assert isinstance(AUTHORIZED_DEVICES, dict)
    
    def test_authorized_devices_contiene_dispositivos(self):
        """AUTHORIZED_DEVICES debe contener dispositivos configurados"""
        assert "raspberry_1" in AUTHORIZED_DEVICES
        assert "raspberry_2" in AUTHORIZED_DEVICES
        assert "admin_pc" in AUTHORIZED_DEVICES
    
    def test_authorized_devices_tiene_tokens(self):
        """Cada dispositivo debe tener un token"""
        for device, token in AUTHORIZED_DEVICES.items():
            assert isinstance(token, str)
            assert len(token) > 0
    
    def test_tokens_son_unicos(self):
        """Cada dispositivo debe tener un token único"""
        tokens = list(AUTHORIZED_DEVICES.values())
        assert len(tokens) == len(set(tokens))


class TestEjecutarServicioIntegracion:
    """Tests de integración para ejecutar_servicio"""
    
    @pytest.mark.asyncio
    async def test_multiples_operaciones_secuenciales(self):
        """Debe ejecutar múltiples operaciones secuencialmente"""
        async def op1():
            return 1
        
        async def op2():
            return 2
        
        async def op3():
            return 3
        
        r1 = await ejecutar_servicio(op1())
        r2 = await ejecutar_servicio(op2())
        r3 = await ejecutar_servicio(op3())
        
        assert r1 == 1
        assert r2 == 2
        assert r3 == 3
    
    @pytest.mark.asyncio
    async def test_mezcla_exitos_y_errores(self):
        """Debe manejar mezcla de operaciones exitosas y con error"""
        async def op_exitosa():
            return "éxito"
        
        async def op_con_error():
            raise HTTPException(status_code=400, detail="Error")
        
        resultado = await ejecutar_servicio(op_exitosa())
        assert resultado == "éxito"
        
        with pytest.raises(HTTPException):
            await ejecutar_servicio(op_con_error())
    
    @pytest.mark.asyncio
    async def test_operacion_con_operaciones_anidadas(self):
        """Debe manejar operaciones anidadas correctamente"""
        async def operacion_nivel_3():
            return "nivel 3"
        
        async def operacion_nivel_2():
            resultado = await ejecutar_servicio(operacion_nivel_3())
            return f"nivel 2 -> {resultado}"
        
        async def operacion_nivel_1():
            resultado = await ejecutar_servicio(operacion_nivel_2())
            return f"nivel 1 -> {resultado}"
        
        resultado_final = await ejecutar_servicio(operacion_nivel_1())
        
        assert resultado_final == "nivel 1 -> nivel 2 -> nivel 3"
    
    @pytest.mark.asyncio
    async def test_error_en_operacion_anidada_se_propaga(self):
        """Errores en operaciones anidadas deben propagarse"""
        async def operacion_que_falla():
            raise ValueError("Error en nivel profundo")
        
        async def operacion_intermedia():
            return await ejecutar_servicio(operacion_que_falla())
        
        with pytest.raises(HTTPException) as exc_info:
            await ejecutar_servicio(operacion_intermedia())
        
        assert exc_info.value.status_code == 500
        assert "Error en nivel profundo" in str(exc_info.value.detail)
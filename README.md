# Sistema de Gestión de Pizzería - Kiosk System

Sistema completo de gestión para pizzerías con interfaz de autoservicio (kiosk), panel administrativo y sincronización en tiempo real mediante WebSockets.

> **NOTA IMPORTANTE**: Esta es una versión pública del proyecto destinada exclusivamente para **demostración de código y portfolio**. Por razones de seguridad, el código carece de elementos críticos necesarios para su funcionamiento completo (credenciales de base de datos, tokens de seguridad, claves secretas, etc.). 
> 
> **Para ver una versión completamente funcional en vivo, puede solicitar un link de acceso publico al mail martin.binaghi01@gmail.com:**  

   Mientras tanto puede revisar las imagenes que dejamos de muestra en el repositorio.

---

## Tabla de Contenidos

- [Descripción](#descripción)
- [Características Principales](#características-principales)
- [Stack Tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Seguridad](#seguridad)
- [Licencia](#licencia)

---

## Descripción

Sistema integral diseñado para modernizar la experiencia de pedidos en pizzerías mediante dispositivos de autoservicio (kiosks). El sistema permite a los clientes realizar pedidos de forma autónoma mientras que el personal administrativo gestiona el menú, productos y monitorea pedidos en tiempo real.

### Casos de Uso Principales

1. **Kiosk de Autoservicio**: Los clientes visualizan el menú en una pantalla interactiva y realizan sus pedidos
2. **Panel Administrativo**: Gestión completa de productos, categorías, precios e imágenes
3. **Sincronización en Tiempo Real**: Actualización instantánea del menú en todos los dispositivos cuando se realizan cambios
4. **Multi-Local**: Soporte para múltiples sucursales con gestión independiente

---

## Características Principales

### Para Clientes (Kiosk)
- **Carrusel interactivo** con imágenes optimizadas de productos destacados
- **Visualización de menú** organizado por categorías
- **Actualización automática** sin recarga de página mediante WebSockets
- **Interfaz responsive** adaptada a pantallas touch
- **Caché inteligente** de imágenes para mejor rendimiento

### Para Administradores
- **Sistema de autenticación** con JWT y roles (admin/empleado/super_admin)
- **CRUD completo** de productos y categorías
- **Gestión de imágenes** con conversión automática a WebP
- **Actualización en tiempo real** del menú en todos los kiosks
- **Monitoreo de dispositivos** conectados
- **Gestión multi-local** para cadenas de pizzerías

### Técnicas
- **WebSockets bidireccionales** para comunicación en tiempo real
- **Base de datos PostgreSQL** con SQLAlchemy ORM
- **Autenticación por dispositivos** con tokens únicos
- **Test coverage** con pytest y vitest
- **API RESTful** documentada con OpenAPI/Swagger
- **Deployment-ready** para producción

---

## Stack Tecnológico

### Backend
- **FastAPI** (v0.123.5) - Framework web asíncrono de alto rendimiento
- **SQLAlchemy** - ORM para PostgreSQL
- **Pydantic** - Validación de datos y schemas
- **PyJWT** - Autenticación con JSON Web Tokens
- **Passlib + Bcrypt** - Hashing seguro de contraseñas
- **Python-multipart** - Manejo de uploads de archivos
- **PostgreSQL** - Base de datos relacional
- **WebSockets** - Comunicación en tiempo real
- **Pytest** - Testing framework

### Frontend
- **React** (v19.2.1) - Biblioteca UI
- **TypeScript** - Tipado estático
- **Vite** (v7.2.4) - Build tool y dev server
- **React Router DOM** (v7.10.1) - Enrutamiento
- **Axios** - Cliente HTTP
- **WebSocket API** - Conexiones en tiempo real
- **Vitest** - Testing framework
- **Testing Library** - Tests de componentes React

### DevOps & Herramientas
- **Git** - Control de versiones
- **dotenv** - Gestión de variables de entorno
- **ESLint** - Linting de código
- **Render** - Hosting y deployment

---

## Arquitectura

### Diagrama de Componentes

```
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Kiosk UI   │  │  Admin Panel │  │   Carrusel   │        │
│  └──────┬───────┘  └───────┬──────┘  └────────┬─────┘        │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   API Gateway   │
                    │   (FastAPI)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐         ┌─────▼─────┐      ┌──────▼──────┐
   │  Auth   │         │ WebSocket │      │   Admin     │
   │ Service │         │  Manager  │      │  Service    │
   └────┬────┘         └─────┬─────┘      └───────┬─────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │
                    │    Database     │
                    └─────────────────┘
```

### Flujo de Datos en Tiempo Real

1. **Admin** actualiza un producto en el panel
2. **Backend** procesa el cambio y lo guarda en la base de datos
3. **WebSocket Manager** notifica a todos los kiosks conectados
4. **Kiosks** reciben el update y actualizan la UI automáticamente

---

## Estructura del Proyecto

```
proyecto-pizzeria/
│
├── Backend/
│   ├── main.py                      # Punto de entrada de FastAPI
│   ├── requirements.txt             # Dependencias Python
│   │
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py         # Autenticación y login
│   │   │   │   ├── admin.py        # Endpoints administrativos
│   │   │   │   ├── menu.py         # Endpoints del menú
│   │   │   │   └── health.py       # Health checks
│   │   │   │
│   │   │   └── websocket/
│   │   │       ├── manager.py      # Gestor de conexiones WS
│   │   │       └── endpoints.py    # Endpoints WebSocket
│   │   │
│   │   ├── config/
│   │   │   └── database.py         # Configuración de BD
│   │   │
│   │   ├── models/
│   │   │   └── models.py           # Modelos SQLAlchemy
│   │   │
│   │   ├── schemas/
│   │   │   ├── schemas.py          # Schemas Pydantic
│   │   │   ├── admin_schemas.py    # Schemas admin
│   │   │   └── menu_schemas.py     # Schemas menú
│   │   │
│   │   ├── services/
│   │   │   ├── services.py         # Lógica de negocio
│   │   │   ├── admin_service.py    # Servicios admin
│   │   │   └── menu_service.py     # Servicios menú
│   │   │
│   │   ├── utils/
│   │   │   ├── utils.py            # Utilidades generales
│   │   │   └── dependencies.py     # Dependencias FastAPI
│   │   │
│   │   └── tests/                  # Tests pytest
│   │
│   └── scripts/                    # Scripts de utilidad
│       ├── init_db.py              # Inicializar BD
│       ├── create_user.py          # Crear usuarios
│       └── convertir_imagenes_webp.py
│
├── Frontend/
│   └── proyecto-pizzas/
│       ├── package.json            # Dependencias Node
│       ├── vite.config.js          # Configuración Vite
│       │
│       ├── src/
│       │   ├── App.tsx             # Componente principal
│       │   ├── main.jsx            # Punto de entrada
│       │   ├── config.js           # Configuración API
│       │   │
│       │   ├── components/
│       │   │   ├── Admin/          # Panel administrativo
│       │   │   │   ├── LoginAdmin.tsx
│       │   │   │   ├── PanelAdmin.tsx
│       │   │   │   ├── AgregarProducto.tsx
│       │   │   │   └── EditarProducto.tsx
│       │   │   │
│       │   │   ├── Menu/           # Interfaz kiosk
│       │   │   │
│       │   │   └── Carrusel/       # Carrusel de productos
│       │   │
│       │   ├── services/
│       │   │   ├── Api.ts          # Cliente API
│       │   │   ├── Websocket.ts    # Cliente WebSocket
│       │   │   └── ImageCache.ts   # Cache de imágenes
│       │   │
│       │   └── tests/              # Tests Vitest
│       │
│       └── public/
│           └── imagenes/           # Imágenes de productos
│
└── README.md
```

---

## API Endpoints

### Autenticación

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `POST` | `/login` | Login de administradores | No |
| `POST` | `/login/dispositivo` | Login de dispositivos kiosk | No |
| `GET` | `/verify` | Verificar token JWT | Sí |

### Menú (Kiosk)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/menu` | Obtener menú completo | Token dispositivo |
| `GET` | `/api/carrusel` | Obtener configuración carrusel | Token dispositivo |

### Administración

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/admin/productos` | Listar productos | Token admin |
| `POST` | `/api/admin/productos` | Crear producto | Token admin |
| `PUT` | `/api/admin/productos/{id}` | Actualizar producto | Token admin |
| `DELETE` | `/api/admin/productos/{id}` | Eliminar producto | Token admin |
| `GET` | `/api/admin/categorias` | Listar categorías | Token admin |
| `POST` | `/api/admin/categorias` | Crear categoría | Token admin |
| `POST` | `/api/admin/imagenes` | Subir imagen | Token admin |
| `DELETE` | `/api/admin/imagenes` | Eliminar imagen | Token admin |

### WebSocket

| Endpoint | Descripción | Parámetros |
|----------|-------------|------------|
| `/ws/kiosk` | Conexión kiosk en tiempo real | `token` (query param) |
| `/ws/admin` | Conexión admin en tiempo real | `token` (query param) |

### Eventos WebSocket

```typescript
// Eventos que puede recibir el kiosk
{
  "event": "menu_actualizado",
  "data": { /* datos del menú */ }
}

{
  "event": "producto_actualizado",
  "data": { /* datos del producto */ }
}

{
  "event": "carrusel_actualizado",
  "data": { /* configuración carrusel */ }
}
```

---

## Testing

### Backend Tests

```bash
cd Backend

# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Tests específicos
pytest app/tests/test_auth.py -v
```

**Test Coverage Actual:**
- Modelos: 95%
- Servicios: 88%
- Endpoints: 82%
- WebSockets: 76%

### Frontend Tests

```bash
cd Frontend/proyecto-pizzas

# Ejecutar tests
npm test

# Con cobertura
npm run test:coverage

# Modo watch
npm test -- --watch
```

**Tests Implementados:**
- Componentes React
- Servicios API
- WebSocket manager
- Cache de imágenes
- Integración auth

---

## Seguridad

### Medidas Implementadas

1. **Autenticación JWT**
   - Tokens firmados con HS256
   - Expiración configurable
   - Refresh token support

2. **Autorización por Roles**
   - `super_admin`: Acceso total multi-local
   - `admin`: Gestión de su local
   - `empleado`: Permisos limitados

3. **Seguridad en Dispositivos**
   - Tokens únicos por dispositivo
   - Registro de último acceso
   - Capacidad de revocación

4. **Base de Datos**
   - Hashing de contraseñas con bcrypt
   - Prepared statements (SQLAlchemy ORM)
   - Validación de entrada con Pydantic

5. **CORS Configurado**
   - Whitelist de orígenes
   - Control de métodos y headers

6. **Rate Limiting**
   - Protección contra fuerza bruta
   - Throttling de requests

### Variables Sensibles

**NUNCA** commitear al repositorio:
- Claves secretas JWT
- Credenciales de base de datos
- Tokens de dispositivos
- URLs de producción con credenciales

---

## Licencia

Todos los derechos reservados. El código fuente, diseño y lógica de este sistema son propiedad de sus autores y no pueden ser utilizados, reproducidos ni distribuidos sin autorización expresa. El acceso público a este repositorio es únicamente con fines de demostración y portfolio.

No se concede ninguna licencia para uso comercial, copia, redistribución ni modificación sin permiso escrito de los titulares de los derechos.

---

<div align="center">

**Si este proyecto te resultó útil, considera darle una estrella**

</div>

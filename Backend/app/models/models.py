from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, Text, TIMESTAMP, ForeignKey, CheckConstraint, Index, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.config.database import Base

# ============================================
# MODELO: Local
# ============================================
class Local(Base):
    __tablename__ = "locales"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    direccion = Column(Text)
    telefono = Column(String(20))
    email = Column(String(100), unique=True, nullable=True, index=True)
    timezone = Column(String(50), default='America/Argentina/Buenos_Aires')
    esta_activo = Column(Boolean, default=True)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    fecha_actualizacion = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    usuarios = relationship("Usuario", back_populates="local", cascade="all, delete-orphan")
    dispositivos = relationship("DispositivoAutorizado", back_populates="local", cascade="all, delete-orphan")
    categorias = relationship("Categoria", back_populates="local", cascade="all, delete-orphan")
    productos = relationship("Producto", back_populates="local", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="local", cascade="all, delete-orphan")
    configuracion_carrusel = relationship("ConfiguracionCarrusel", back_populates="local", uselist=False)


# ============================================
# MODELO: Usuario
# ============================================
class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20), default='empleado')
    esta_activo = Column(Boolean, default=True)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    ultimo_acceso = Column(TIMESTAMP)
    
    __table_args__ = (
        CheckConstraint("rol IN ('admin', 'empleado', 'super_admin')", name='check_rol_usuario'),
    )
    
    # Relaciones
    local = relationship("Local", back_populates="usuarios")


# ============================================
# MODELO: DispositivoAutorizado
# ============================================
class DispositivoAutorizado(Base):
    __tablename__ = "dispositivos_autorizados"
    
    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(50), unique=True, nullable=False, index=True)
    secret_key = Column(String(255), nullable=False)
    nombre = Column(String(100))
    tipo = Column(String(20), default='kiosk')
    esta_activo = Column(Boolean, default=True)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    ultimo_acceso = Column(TIMESTAMP)
    
    __table_args__ = (
        CheckConstraint("tipo IN ('kiosk', 'admin_pc', 'tablet')", name='check_tipo_dispositivo'),
    )
    
    # Relaciones
    local = relationship("Local", back_populates="dispositivos")
    sesiones = relationship("SesionKiosk", back_populates="dispositivo", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="dispositivo")


# ============================================
# MODELO: Categoria
# ============================================
class Categoria(Base):
    __tablename__ = "categorias"
    
    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(Text)
    orden = Column(Integer, default=0)
    esta_activo = Column(Boolean, default=True)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    __table_args__ = (
        Index('idx_categoria_local_nombre', 'local_id', 'nombre', unique=True),
    )
    
    # Relaciones
    local = relationship("Local", back_populates="categorias")
    productos = relationship("Producto", back_populates="categoria")


# ============================================
# MODELO: Producto
# ============================================
class Producto(Base):
    __tablename__ = "productos"
    
    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id", ondelete="SET NULL"))
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    precio = Column(DECIMAL(10, 2), nullable=False)
    imagen_url = Column(Text)
    disponible = Column(Boolean, default=True)
    destacado = Column(Boolean, default=False)
    orden = Column(Integer, default=0)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    fecha_actualizacion = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    __table_args__ = (
        CheckConstraint('precio >= 0', name='check_precio_positivo'),
        Index('idx_productos_local_disponible', 'local_id', 'disponible'),
    )
    
    # Relaciones
    local = relationship("Local", back_populates="productos")
    categoria = relationship("Categoria", back_populates="productos")
    variantes = relationship("VarianteProducto", back_populates="producto", cascade="all, delete-orphan")
    items_pedido = relationship("ItemPedido", back_populates="producto")


# ============================================
# MODELO: VarianteProducto
# ============================================
class VarianteProducto(Base):
    __tablename__ = "variantes_producto"
    
    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(50), nullable=False)
    precio_adicional = Column(DECIMAL(10, 2), default=0)
    disponible = Column(Boolean, default=True)
    orden = Column(Integer, default=0)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    __table_args__ = (
        CheckConstraint('precio_adicional >= 0', name='check_precio_adicional_positivo'),
    )
    
    # Relaciones
    producto = relationship("Producto", back_populates="variantes")
    items_pedido = relationship("ItemPedido", back_populates="variante")


# ============================================
# MODELO: Pedido
# ============================================
class Pedido(Base):
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id", ondelete="CASCADE"), nullable=False)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos_autorizados.id", ondelete="SET NULL"))
    numero_orden = Column(String(20), unique=True, nullable=False)
    estado = Column(String(20), default='pendiente')
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    impuestos = Column(DECIMAL(10, 2), default=0)
    descuento = Column(DECIMAL(10, 2), default=0)
    total = Column(DECIMAL(10, 2), nullable=False)
    metodo_pago = Column(String(20))
    estado_pago = Column(String(20), default='pendiente')
    notas = Column(Text)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    fecha_completado = Column(TIMESTAMP)
    
    __table_args__ = (
        CheckConstraint("estado IN ('pendiente', 'preparando', 'listo', 'entregado', 'cancelado')", name='check_estado_pedido'),
        CheckConstraint("metodo_pago IN ('efectivo', 'tarjeta', 'qr', 'mercadopago')", name='check_metodo_pago'),
        CheckConstraint("estado_pago IN ('pendiente', 'pagado', 'rechazado', 'reembolsado')", name='check_estado_pago'),
        CheckConstraint('subtotal >= 0 AND total >= 0', name='check_montos_positivos'),
        Index('idx_pedidos_local_fecha', 'local_id', 'fecha_creacion'),
        Index('idx_pedidos_estado', 'estado', 'fecha_creacion'),
    )
    
    # Relaciones
    local = relationship("Local", back_populates="pedidos")
    dispositivo = relationship("DispositivoAutorizado", back_populates="pedidos")
    items = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    transacciones = relationship("TransaccionPago", back_populates="pedido", cascade="all, delete-orphan")


# ============================================
# MODELO: ItemPedido
# ============================================
class ItemPedido(Base):
    __tablename__ = "items_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id", ondelete="SET NULL"))
    variante_id = Column(Integer, ForeignKey("variantes_producto.id", ondelete="SET NULL"))
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(DECIMAL(10, 2), nullable=False)
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    notas = Column(Text)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    __table_args__ = (
        CheckConstraint('cantidad > 0', name='check_cantidad_positiva'),
    )
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="items")
    producto = relationship("Producto", back_populates="items_pedido")
    variante = relationship("VarianteProducto", back_populates="items_pedido")


# ============================================
# MODELO: TransaccionPago
# ============================================
class TransaccionPago(Base):
    __tablename__ = "transacciones_pago"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    metodo = Column(String(20), nullable=False)
    monto = Column(DECIMAL(10, 2), nullable=False)
    estado = Column(String(20), default='pendiente')
    id_externo = Column(String(100))
    datos_transaccion = Column(JSONB)
    fecha_creacion = Column(TIMESTAMP, server_default=func.current_timestamp())
    
    __table_args__ = (
        CheckConstraint("estado IN ('pendiente', 'aprobado', 'rechazado', 'reembolsado')", name='check_estado_transaccion'),
    )
    
    # Relaciones
    pedido = relationship("Pedido", back_populates="transacciones")


# ============================================
# MODELO: SesionKiosk
# ============================================
class SesionKiosk(Base):
    __tablename__ = "sesiones_kiosk"
    
    id = Column(Integer, primary_key=True, index=True)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos_autorizados.id", ondelete="CASCADE"), nullable=False)
    token_jwt = Column(Text, nullable=False)
    fecha_inicio = Column(TIMESTAMP, server_default=func.current_timestamp())
    fecha_expiracion = Column(TIMESTAMP)
    ip_address = Column(String(45))
    esta_activa = Column(Boolean, default=True)
    
    # Relaciones
    dispositivo = relationship("DispositivoAutorizado", back_populates="sesiones")
    
    
class ConfiguracionCarrusel(Base):
    __tablename__ = "configuracion_carrusel"
    
    id = Column(Integer, primary_key=True, index=True)
    local_id = Column(Integer, ForeignKey("locales.id"), unique=True, nullable=False)
    modo = Column(String(50), default="all")
    categorias_seleccionadas = Column(JSON, default=[])
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    local = relationship("Local", back_populates="configuracion_carrusel")
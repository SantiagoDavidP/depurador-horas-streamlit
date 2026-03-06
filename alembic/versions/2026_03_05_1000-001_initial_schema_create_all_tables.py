"""initial_schema_create_all_tables

Revision ID: 001
Revises:
Create Date: 2026-03-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre_completo', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('rol', sa.String(50), nullable=False, server_default='Vendedor'),
        sa.Column('entra_id', sa.String(255), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('ultimo_acceso', sa.DateTime(timezone=True), nullable=True),
        sa.Column('remember_token', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_entra_id', 'users', ['entra_id'], unique=True)

    # Create productos table
    op.create_table(
        'productos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo_sap', sa.String(50), nullable=False),
        sa.Column('nombre', sa.String(255), nullable=False),
        sa.Column('molecula', sa.String(255), nullable=False, server_default=''),
        sa.Column('precio_vvf', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('precio_compra', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('distribuidor', sa.String(100), nullable=False),
        sa.Column('inafecto_devolucion', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('stock_disponible', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_productos_codigo_sap', 'productos', ['codigo_sap'], unique=True)
    op.create_index('ix_productos_distribuidor', 'productos', ['distribuidor'])

    # Create pedidos table
    op.create_table(
        'pedidos',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo_pedido', sa.String(20), nullable=False),
        sa.Column('fecha', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('cliente_ruc', sa.String(11), nullable=False),
        sa.Column('cliente_razon_social', sa.String(255), nullable=False, server_default=''),
        sa.Column('representante', sa.String(255), nullable=False, server_default=''),
        sa.Column('condicion_pago', sa.String(50), nullable=False, server_default='Contado'),
        sa.Column('estado', sa.String(20), nullable=False, server_default='Borrador'),
        sa.Column('subtotal', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('igv', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('total', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('vendedor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aprobador_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('fecha_aprobacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('motivo_rechazo', sa.Text(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['vendedor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['aprobador_id'], ['users.id'], ),
    )
    op.create_index('ix_pedidos_codigo_pedido', 'pedidos', ['codigo_pedido'], unique=True)
    op.create_index('ix_pedidos_cliente_ruc', 'pedidos', ['cliente_ruc'])
    op.create_index('ix_pedidos_estado', 'pedidos', ['estado'])
    op.create_index('ix_pedidos_vendedor_id', 'pedidos', ['vendedor_id'])

    # Create detalles_pedido table
    op.create_table(
        'detalles_pedido',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pedido_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('producto_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('precio_unitario', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('tipo', sa.String(20), nullable=False, server_default='Venta'),
        sa.Column('subtotal', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
    )
    op.create_index('ix_detalles_pedido_pedido_id', 'detalles_pedido', ['pedido_id'])
    op.create_index('ix_detalles_pedido_producto_id', 'detalles_pedido', ['producto_id'])

    # Create comentarios_pedido table
    op.create_table(
        'comentarios_pedido',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pedido_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contenido', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    op.create_index('ix_comentarios_pedido_pedido_id', 'comentarios_pedido', ['pedido_id'])

    # Create devoluciones table
    op.create_table(
        'devoluciones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo_devolucion', sa.String(20), nullable=False),
        sa.Column('pedido_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('numero_factura', sa.String(20), nullable=False),
        sa.Column('producto_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('lote', sa.String(100), nullable=False, server_default=''),
        sa.Column('razon', sa.String(255), nullable=False),
        sa.Column('estado', sa.String(20), nullable=False, server_default='En Proceso'),
        sa.Column('valorizado', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('solicitante_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aprobador_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('fecha_aprobacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('motivo_rechazo', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], ),
        sa.ForeignKeyConstraint(['solicitante_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['aprobador_id'], ['users.id'], ),
    )
    op.create_index('ix_devoluciones_codigo_devolucion', 'devoluciones', ['codigo_devolucion'], unique=True)
    op.create_index('ix_devoluciones_estado', 'devoluciones', ['estado'])

    # Create comisiones table
    op.create_table(
        'comisiones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('distribuidor', sa.String(100), nullable=False),
        sa.Column('mes', sa.Integer(), nullable=False),
        sa.Column('anio', sa.Integer(), nullable=False),
        sa.Column('ventas_totales', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('porcentaje', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('comision_bruta', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('recuperos', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('neto_a_pagar', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('estado', sa.String(20), nullable=False, server_default='Calculada'),
        sa.Column('detalle_pedidos', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('detalle_devoluciones', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('calculado_por_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aprobado_por_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('fecha_calculo', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('fecha_aprobacion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['calculado_por_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['aprobado_por_id'], ['users.id'], ),
    )
    op.create_index('ix_comisiones_distribuidor', 'comisiones', ['distribuidor'])
    op.create_index('ix_comisiones_mes_anio', 'comisiones', ['mes', 'anio'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entidad', sa.String(50), nullable=False),
        sa.Column('entidad_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('accion', sa.String(20), nullable=False),
        sa.Column('valores_anteriores', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('valores_nuevos', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False, server_default=''),
        sa.Column('user_agent', sa.String(500), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    op.create_index('ix_audit_logs_entidad', 'audit_logs', ['entidad'])
    op.create_index('ix_audit_logs_entidad_id', 'audit_logs', ['entidad_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])

    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tipo', sa.String(20), nullable=False, server_default='InApp'),
        sa.Column('titulo', sa.String(255), nullable=False),
        sa.Column('mensaje', sa.Text(), nullable=False),
        sa.Column('entidad', sa.String(50), nullable=True),
        sa.Column('entidad_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('leido', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('enviado', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('fecha_envio', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_leido', 'notifications', ['leido'])

    # Create distribuidor_config table
    op.create_table(
        'distribuidor_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('ruc', sa.String(11), nullable=False, server_default=''),
        sa.Column('porcentaje_comision', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('monto_minimo_pedido', sa.Float(), nullable=False, server_default=sa.text('0.0')),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_distribuidor_config_nombre', 'distribuidor_config', ['nombre'], unique=True)

    # Create condiciones_pago table
    op.create_table(
        'condiciones_pago',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('dias_credito', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_condiciones_pago_nombre', 'condiciones_pago', ['nombre'], unique=True)

    # Create razones_devolucion table
    op.create_table(
        'razones_devolucion',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('nombre', sa.String(255), nullable=False),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_razones_devolucion_nombre', 'razones_devolucion', ['nombre'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order to respect foreign key constraints
    op.drop_table('razones_devolucion')
    op.drop_table('condiciones_pago')
    op.drop_table('distribuidor_config')
    op.drop_table('notifications')
    op.drop_table('audit_logs')
    op.drop_table('comisiones')
    op.drop_table('devoluciones')
    op.drop_table('comentarios_pedido')
    op.drop_table('detalles_pedido')
    op.drop_table('pedidos')
    op.drop_table('productos')
    op.drop_table('users')

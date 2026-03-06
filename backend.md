# Backend - Automatización de Pedidos y Devoluciones BONAPHARM

---

## AUTENTICACIÓN Y SEGURIDAD

### Autenticación
- POST /api/auth/login - Autenticación con credenciales locales (email/contraseña), retorna JWT token
- POST /api/auth/login/microsoft - Inicio de sesión SSO con Microsoft Entra ID (OAuth2.0), retorna JWT token
- POST /api/auth/logout - Invalidación de token y cierre de sesión
- POST /api/auth/forgot-password - Solicitud de recuperación de contraseña, envía email con token temporal
- POST /api/auth/reset-password - Reseteo de contraseña con token de validación
- GET /api/auth/me - Obtener información del usuario autenticado actual (id, nombre, email, rol, permisos)
- POST /api/auth/refresh-token - Renovación de token JWT antes de expiración

### Usuarios y Roles
- GET /api/users - Listar usuarios con paginación y filtros (rol, estado, búsqueda por nombre/email)
- GET /api/users/{id} - Obtener detalles de un usuario específico
- POST /api/users - Crear nuevo usuario (solo para administradores)
- PUT /api/users/{id} - Actualizar información de usuario
- DELETE /api/users/{id} - Desactivar usuario (soft delete)
- GET /api/roles - Listar roles disponibles (Vendedor, AdminComercial, Finanzas, GerenteGeneral)
- GET /api/roles/{id}/permissions - Obtener permisos asociados a un rol

---

## PORTAL VENDEDOR

### Dashboard
- GET /api/dashboard/vendor/{vendorId} - Métricas personalizadas del vendedor: pedidos totales, en aprobación, devoluciones, comisiones del mes
- GET /api/dashboard/vendor/{vendorId}/orders-by-status - Distribución de pedidos por estado con contadores y porcentajes
- GET /api/dashboard/vendor/{vendorId}/top-products - Top 5 productos vendidos del mes con cantidades
- GET /api/dashboard/vendor/{vendorId}/recent-activity - Timeline de últimos 10 eventos del vendedor

### Registro de Pedidos
- POST /api/orders - Crear nuevo pedido con estado 'Borrador' o 'Enviado'
  - Request: `{ cliente_ruc, representante, condicion_pago, detalles: [{ producto_id, cantidad, tipo }] }`
  - Response: `{ id, codigo_pedido, estado, total, fecha }`
- GET /api/orders/draft - Listar borradores del vendedor autenticado
- PUT /api/orders/{id}/draft - Actualizar pedido en borrador
- POST /api/orders/{id}/submit - Enviar pedido (cambiar de 'Borrador' a 'Enviado'), valida mínimos y dispara workflow
- GET /api/clients/search?ruc={ruc} - Buscar cliente por RUC en SAP, retorna razón social y datos
- GET /api/products - Listar catálogo de productos con filtros (distribuidor, molécula, búsqueda por nombre/código SAP)
- GET /api/products/{id} - Detalle de producto con precio VVF, stock disponible, distribuidor
- POST /api/orders/{id}/validate - Validar pedido antes de envío (mínimos, stock, datos completos)

### Consulta de Pedidos
- GET /api/orders - Listar pedidos del vendedor autenticado con filtros (estado, rango de fechas, búsqueda por código/cliente), paginación y ordenamiento
- GET /api/orders/{id} - Detalle completo de un pedido con productos, cliente, totales, historial de estados
- GET /api/orders/{id}/pdf - Generar y descargar PDF del pedido
- PUT /api/orders/{id} - Editar pedido (solo si estado es 'Enviado')
- POST /api/orders/{id}/resubmit - Reenviar pedido rechazado (crea nueva versión con estado 'Enviado')
- GET /api/orders/export - Exportar pedidos filtrados a Excel

---

## PORTAL DISTRIBUIDOR/COMERCIAL

### Aprobación de Pedidos
- GET /api/orders/pending - Listar pedidos con estado 'Enviado' pendientes de aprobación, con filtros (vendedor, ordenamiento)
- GET /api/orders/{id}/approval-detail - Detalle completo para revisión de aprobación (productos, cliente, vendedor, totales, bonificaciones)
- POST /api/orders/{id}/approve - Aprobar pedido, cambia estado a 'Aprobado', dispara workflow de notificación y sincronización con SAP
  - Request: `{ aprobador_id, comentarios? }`
  - Response: `{ success: true, order_id, new_status: 'Aprobado', notification_sent: true }`
- POST /api/orders/{id}/reject - Rechazar pedido, cambia estado a 'Rechazado', requiere motivo
  - Request: `{ aprobador_id, motivo_rechazo }`
  - Response: `{ success: true, order_id, new_status: 'Rechazado' }`
- POST /api/orders/{id}/comments - Agregar comentario interno a un pedido
- GET /api/orders/{id}/comments - Listar comentarios de un pedido
- GET /api/orders/pending/count - Contador de pedidos pendientes para badge en header

### Gestión de Devoluciones
- GET /api/returns - Listar devoluciones con filtros (estado, cliente, fecha, producto), paginación
- GET /api/returns/{id} - Detalle completo de una devolución
- POST /api/returns - Registrar nueva devolución
  - Request: `{ pedido_id, numero_factura, productos: [{ producto_id, cantidad, lote, razon }], observaciones? }`
  - Response: `{ id, codigo_devolucion, estado: 'En Proceso', valorizado_total }`
- PUT /api/returns/{id} - Actualizar devolución (solo si estado es 'En Proceso')
- POST /api/returns/{id}/approve - Aprobar devolución, cambia estado a 'Aprobada'
- POST /api/returns/{id}/reject - Rechazar devolución con motivo
- GET /api/returns/reasons - Listar razones de devolución disponibles
- GET /api/orders/{id}/returnable-products - Listar productos del pedido que pueden devolverse (excluye inafectos y ya devueltos)
- POST /api/returns/{id}/calculate-valorizado - Calcular valorizado de devolución antes de guardar

### Cálculo de Comisiones
- GET /api/commissions - Listar registros de comisiones con filtros (distribuidor, mes, año, estado)
- GET /api/commissions/calculate - Ejecutar cálculo de comisiones para un periodo
  - Request: `{ mes, año, distribuidor_id? }` (si no se especifica distribuidor, calcula para todos)
  - Response: `{ commissions: [{ distribuidor, ventas_totales, porcentaje, comision_bruta, recuperos, neto_a_pagar }] }`
- POST /api/commissions - Guardar resultado de cálculo de comisiones con estado 'Calculada'
- POST /api/commissions/{id}/approve - Aprobar pago de comisión, cambia estado a 'Aprobada', genera registro contable
- GET /api/commissions/{id}/detail - Detalle desglosado del cálculo: pedidos incluidos, devoluciones, fórmulas aplicadas
- GET /api/commissions/export - Exportar cálculos de comisiones a Excel con formato contable
- GET /api/commissions/summary?mes={mes}&año={año} - Resumen de comisiones del periodo: ventas totales, comisiones totales, recuperos totales

---

## REPORTES Y ANALÍTICA

### Power BI Integration
- GET /api/reports/embed-token - Generar token de embed para reportes de Power BI autenticados
- GET /api/reports/list - Listar reportes disponibles según rol del usuario
- GET /api/reports/{reportId}/refresh - Solicitar refresh del dataset de un reporte específico
- GET /api/reports/last-refresh - Timestamp de última actualización de datos en Power BI

### Exportaciones
- GET /api/exports/orders - Exportar pedidos filtrados a Excel
- GET /api/exports/returns - Exportar devoluciones a Excel
- GET /api/exports/commissions - Exportar comisiones a Excel
- GET /api/exports/products - Exportar catálogo de productos a Excel
- POST /api/exports/custom - Generar exportación personalizada con selección de columnas y filtros

---

## INTEGRACIÓN SAP

### Sincronización
- GET /api/sap/inventory - Consultar inventario de SAP (stock, lotes, precios)
  - Response: `{ items: [{ codigo_sap, stock, lote, precio_vvf }] }`
- GET /api/sap/clients/{ruc} - Consultar información de cliente por RUC
- POST /api/sap/orders/{orderId}/sync - Enviar pedido aprobado a SAP para facturación
- GET /api/sap/invoices?pedido_id={pedidoId} - Consultar facturas asociadas a un pedido
- GET /api/sap/products/sync - Sincronizar catálogo de productos desde SAP a Dataverse (ejecutado por workflow)
- POST /api/sap/returns/{returnId}/sync - Enviar devolución aprobada a SAP

---

## NOTIFICACIONES

### Email
- POST /api/notifications/email - Enviar email manual (para testing)
- GET /api/notifications/email/templates - Listar plantillas de email disponibles
- GET /api/notifications/sent - Historial de notificaciones enviadas

### Push Notifications
- GET /api/notifications/user/{userId} - Listar notificaciones del usuario (leídas/no leídas)
- PUT /api/notifications/{id}/read - Marcar notificación como leída
- DELETE /api/notifications/{id} - Eliminar notificación
- GET /api/notifications/unread/count - Contador de notificaciones no leídas para badge

---

## ADMINISTRACIÓN

### Configuración
- GET /api/config/distributors - Listar distribuidores configurados (Dimexa, Química Suiza) con porcentajes de comisión
- PUT /api/config/distributors/{id} - Actualizar configuración de distribuidor (mínimos de pedido, porcentaje comisión)
- GET /api/config/payment-terms - Listar condiciones de pago disponibles
- POST /api/config/payment-terms - Crear nueva condición de pago
- GET /api/config/return-reasons - Listar razones de devolución
- POST /api/config/return-reasons - Agregar nueva razón de devolución

### Auditoría
- GET /api/audit/logs - Listar logs de auditoría con filtros (usuario, acción, entidad, fecha)
- GET /api/audit/logs/{entityId} - Historial de cambios de una entidad específica (pedido, devolución, comisión)

---

## MODELOS DE DATOS

### Pedido
- id: UUID (PK)
- codigo_pedido: string unique (formato: PED-YYYY-NNNN)
- fecha: datetime (auto-generado al crear)
- cliente_ruc: string(11) (validación: numérico)
- cliente_razon_social: string
- representante: string
- condicion_pago: string (Contado, Crédito 30 días, Crédito 60 días)
- estado: enum (Borrador, Enviado, Aprobado, Rechazado)
- subtotal: decimal(10,2) (calculado)
- igv: decimal(10,2) (calculado: subtotal × 0.18)
- total: decimal(10,2) (calculado: subtotal + igv)
- vendedor_id: UUID (FK -> User)
- aprobador_id: UUID nullable (FK -> User)
- fecha_aprobacion: datetime nullable
- motivo_rechazo: text nullable
- observaciones: text nullable
- created_at: datetime
- updated_at: datetime

### DetallePedido
- id: UUID (PK)
- pedido_id: UUID (FK -> Pedido)
- producto_id: UUID (FK -> Producto)
- cantidad: integer (validación: > 0)
- precio_unitario: decimal(10,2)
- tipo: enum (Venta, Bonificacion)
- subtotal: decimal(10,2) (calculado: cantidad × precio_unitario, 0 si tipo = Bonificacion)
- created_at: datetime

### Devolucion
- id: UUID (PK)
- codigo_devolucion: string unique (formato: DEV-YYYY-NNNN)
- pedido_id: UUID (FK -> Pedido)
- numero_factura: string (formato: F001-00012345)
- producto_id: UUID (FK -> Producto)
- cantidad: integer (validación: > 0 y <= cantidad original en pedido)
- lote: string
- razon: string (Producto dañado, Fecha de vencimiento próxima, Error en el pedido, Cliente rechazó entrega, Defecto de fabricación)
- estado: enum (En Proceso, Aprobada, Rechazada)
- valorizado: decimal(10,2) (calculado: cantidad × precio_unitario_original)
- observaciones: text nullable
- solicitante_id: UUID (FK -> User)
- aprobador_id: UUID nullable (FK -> User)
- fecha_aprobacion: datetime nullable
- motivo_rechazo: text nullable
- created_at: datetime
- updated_at: datetime

### Producto
- id: UUID (PK)
- codigo_sap: string unique (sincronizado desde SAP)
- nombre: string
- molecula: string
- precio_vvf: decimal(10,2)
- distribuidor: string (Dimexa, Quimica Suiza)
- inafecto_devolucion: boolean (default: false)
- stock_disponible: integer (sincronizado desde SAP cada 6 horas)
- activo: boolean (default: true)
- created_at: datetime
- updated_at: datetime

### Comision
- id: UUID (PK)
- distribuidor: string (Dimexa, Quimica Suiza)
- mes: integer (1-12)
- año: integer
- ventas_totales: decimal(12,2) (suma de pedidos aprobados del periodo)
- porcentaje: decimal(5,2) (10.00 para Dimexa, 13.00 para Quimica)
- comision_bruta: decimal(12,2) (calculado según fórmula del distribuidor)
- recuperos: decimal(12,2) (suma de devoluciones aprobadas × porcentaje)
- neto_a_pagar: decimal(12,2) (comision_bruta - recuperos)
- estado: enum (Calculada, Aprobada, Pagada)
- calculado_por_id: UUID (FK -> User)
- aprobado_por_id: UUID nullable (FK -> User)
- fecha_calculo: datetime
- fecha_aprobacion: datetime nullable
- observaciones: text nullable
- created_at: datetime
- updated_at: datetime

### User
- id: UUID (PK)
- nombre_completo: string
- email: string unique (validación: formato email)
- password_hash: string nullable (null si usa solo Entra ID)
- rol: enum (Vendedor, AdminComercial, Finanzas, GerenteGeneral)
- entra_id: string nullable unique (ID de Microsoft Entra ID)
- activo: boolean (default: true)
- ultimo_acceso: datetime nullable
- remember_token: string nullable
- created_at: datetime
- updated_at: datetime

### AuditLog
- id: UUID (PK)
- user_id: UUID (FK -> User)
- entidad: string (Pedido, Devolucion, Comision, Producto)
- entidad_id: UUID
- accion: enum (Crear, Actualizar, Eliminar, Aprobar, Rechazar)
- valores_anteriores: JSON nullable
- valores_nuevos: JSON
- ip_address: string
- user_agent: string
- created_at: datetime

### Notification
- id: UUID (PK)
- user_id: UUID (FK -> User)
- tipo: enum (Email, Push, InApp)
- titulo: string
- mensaje: text
- entidad: string nullable (Pedido, Devolucion, Comision)
- entidad_id: UUID nullable
- leido: boolean (default: false)
- enviado: boolean (default: false)
- fecha_envio: datetime nullable
- created_at: datetime

---

## REGLAS DE NEGOCIO PRINCIPALES

### Registro de Pedidos
1. Al crear pedido con estado 'Enviado':
   - Generar código único con formato PED-YYYY-NNNN (año actual + correlativo)
   - Validar que cliente_ruc tenga exactamente 11 dígitos numéricos
   - Validar que exista al menos 1 producto de tipo 'Venta' en detalles
   - Calcular subtotal sumando subtotales de productos de tipo 'Venta' (ignorar bonificaciones)
   - Calcular IGV = subtotal × 0.18
   - Calcular total = subtotal + IGV
   - Validar mínimos del distribuidor: consultar configuración y validar que total >= mínimo configurado
   - Si total < mínimo, retornar error 400 con mensaje específico del mínimo requerido
   - Si validación exitosa, guardar pedido y crear registros en DetallePedido
   - Disparar workflow 'NotificacionPedidos' pasando pedido_id
   - Retornar pedido creado con código generado

2. Productos de bonificación:
   - Si DetallePedido.tipo = 'Bonificacion', forzar precio_unitario = 0 y subtotal = 0
   - No sumar bonificaciones al total del pedido
   - En resumen mostrar cantidad total de bonificaciones por separado

3. Edición de pedidos:
   - Solo permitir edición si estado = 'Enviado'
   - Al editar, recalcular automáticamente subtotal, IGV, total
   - Registrar cambios en AuditLog

### Aprobación de Pedidos
1. Al aprobar pedido (POST /api/orders/{id}/approve):
   - Validar que estado actual = 'Enviado'
   - Cambiar estado a 'Aprobado'
   - Registrar aprobador_id y fecha_aprobacion
   - Disparar workflow 'IntegracionSAP' para enviar pedido a SAP
   - Disparar notificación email al vendedor con template 'pedido_aprobado'
   - Disparar notificación email al distribuidor correspondiente según productos
   - Registrar acción en AuditLog
   - Retornar confirmación

2. Al rechazar pedido (POST /api/orders/{id}/reject):
   - Validar que estado actual = 'Enviado'
   - Validar que motivo_rechazo no esté vacío
   - Cambiar estado a 'Rechazado'
   - Registrar aprobador_id, fecha_aprobacion, motivo_rechazo
   - Disparar notificación email al vendedor con motivo de rechazo
   - Registrar acción en AuditLog

### Gestión de Devoluciones
1. Al registrar devolución (POST /api/returns):
   - Validar que pedido asociado exista y estado = 'Aprobado'
   - Validar que numero_factura tenga formato correcto (regex: ^F\d{3}-\d{8}$)
   - Para cada producto a devolver:
     - Validar que producto no tenga inafecto_devolucion = true
     - Validar que cantidad <= cantidad original en DetallePedido del pedido
     - Calcular valorizado = cantidad × precio_unitario_original del DetallePedido
   - Generar codigo_devolucion único con formato DEV-YYYY-NNNN
   - Guardar con estado 'En Proceso'
   - Disparar workflow 'AprobacionDevoluciones' para notificar a administrador
   - Retornar devolución creada

2. Al aprobar devolución:
   - Cambiar estado a 'Aprobada'
   - Registrar aprobador_id y fecha_aprobacion
   - Actualizar estadísticas de devoluciones del producto
   - Disparar workflow 'IntegracionSAP' para sincronizar devolución
   - El valorizado de esta devolución se incluirá en recuperos del próximo cálculo de comisiones

### Cálculo de Comisiones
1. Fórmula para Dimexa (10%):
   - Consultar todos los pedidos con estado = 'Aprobado' y fecha_aprobacion dentro del mes/año seleccionado
   - ventas_totales = SUMA(pedido.total) de pedidos del distribuidor Dimexa
   - comision_bruta = ventas_totales × 0.10
   - Consultar todas las devoluciones con estado = 'Aprobada', fecha_aprobacion dentro del periodo, y producto.distribuidor = 'Dimexa'
   - recuperos = SUMA(devolucion.valorizado) × 0.10
   - neto_a_pagar = comision_bruta - recuperos

2. Fórmula para Química Suiza (13%):
   - Consultar todos los pedidos con estado = 'Aprobado' y fecha_aprobacion dentro del mes/año seleccionado
   - Para cada DetallePedido del distribuidor Química:
     - diferencia_precio = precio_unitario - producto.precio_compra (obtenido de SAP)
     - base_comision += cantidad × diferencia_precio
   - comision_bruta = base_comision × 0.13
   - Consultar devoluciones del distribuidor en el periodo
   - recuperos = SUMA(devolucion.valorizado) × 0.13
   - neto_a_pagar = comision_bruta - recuperos

3. Al ejecutar cálculo:
   - Validar que no exista registro de comisión para el mismo distribuidor/mes/año con estado 'Aprobada' o 'Pagada'
   - Si existe con estado 'Calculada', permitir recálculo (actualizar registro existente)
   - Guardar detalle desglosado: IDs de pedidos incluidos, IDs de devoluciones, fórmulas aplicadas
   - Retornar resumen del cálculo

4. Al aprobar comisión:
   - Cambiar estado a 'Aprobada'
   - Registrar aprobado_por_id y fecha_aprobacion
   - Generar registro contable (integración futura con sistema contable)
   - Disparar notificación a finanzas confirmando aprobación

### Sincronización SAP
1. Sincronización de catálogo de productos (workflow ejecutado cada 6 horas):
   - Consultar GET /api/sap/inventory
   - Para cada producto en respuesta:
     - Si codigo_sap ya existe en Dataverse, actualizar: nombre, precio_vvf, stock_disponible
     - Si no existe, crear nuevo registro de Producto
   - Registrar timestamp de última sincronización
   - Si falla sincronización, reintentar 3 veces con backoff exponencial
   - Si falla después de 3 intentos, notificar a administrador

2. Envío de pedido aprobado a SAP:
   - Al aprobar pedido, disparar POST /api/sap/orders/{orderId}/sync
   - Enviar JSON con estructura esperada por SAP
   - Si respuesta exitosa, registrar ID de factura en pedido
   - Si falla, marcar pedido con flag 'pendiente_sincronizacion' y reintentar en próximo ciclo

### Notificaciones Email
1. Plantilla 'pedido_enviado': Al vendedor registrar pedido → "Su pedido {codigo_pedido} ha sido enviado y está en revisión"
2. Plantilla 'pedido_aprobado': Al aprobar pedido → "Su pedido {codigo_pedido} ha sido aprobado por {aprobador_nombre}"
3. Plantilla 'pedido_rechazado': Al rechazar pedido → "Su pedido {codigo_pedido} fue rechazado. Motivo: {motivo_rechazo}"
4. Plantilla 'devolucion_registrada': Al registrar devolución → "Devolución {codigo_devolucion} registrada y en proceso de revisión"
5. Plantilla 'comision_calculada': Al calcular comisión → "Comisión del mes {mes}/{año} calculada: S/ {neto_a_pagar}"

### Validaciones Transversales
- Todos los endpoints protegidos requieren header `Authorization: Bearer {jwt_token}`
- Validar rol del usuario para acceso a endpoints según matriz de permisos
- Registrar todas las operaciones de escritura (POST, PUT, DELETE) en AuditLog
- Rate limiting: 100 requests por minuto por usuario
- Validación de entrada: sanitizar todos los inputs para prevenir SQL Injection y XSS
- Timestamps automáticos: created_at se llena al crear, updated_at se actualiza en cada modificación

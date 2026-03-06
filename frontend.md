# Frontend - Automatización de Pedidos y Devoluciones BONAPHARM

---

## PÁGINAS

### Autenticación

#### LoginPage
Pantalla de autenticación con dos métodos de acceso: formulario tradicional (email/contraseña) y Single Sign-On con Microsoft Entra ID. Muestra logo de BONAPHARM, campos de email y contraseña con validación en tiempo real, checkbox "Recordar mi sesión", enlace de recuperación de contraseña, y botón de SSO con logo de Microsoft. Al autenticar correctamente, redirige al dashboard correspondiente según rol del usuario. Incluye footer con información de seguridad (Azure AD, TLS 1.2+, AES-256). Diseño centrado verticalmente con gradiente de fondo azul claro. Accesible por cualquier usuario no autenticado.

**Datos que consume**: POST /api/auth/login o POST /api/auth/login/microsoft
**Acciones**: Enviar credenciales, validar formato de email, iniciar sesión SSO, recordar sesión
**Roles que la ven**: Público (no autenticado)

---

### Portal Vendedor

#### DashboardVendedorPage
Dashboard personalizado del vendedor con vista general de actividad mensual. Muestra 4 KPI cards: Pedidos Totales (con trending vs mes anterior), Pedidos en Aprobación (contador), Devoluciones del mes (con trending), Comisiones acumuladas (monto en soles). Incluye gráfico de barras horizontales de pedidos por estado (Aprobados verde, Pendientes amarillo, Rechazados rojo) con porcentajes calculados. Listado de top 5 productos vendidos con código SAP, nombre y unidades totales. Timeline de actividad reciente mostrando últimos 10 eventos con iconos diferenciados, descripción breve y timestamp relativo (ej: "Hace 12 min"). Header con barra de búsqueda global, icono de notificaciones con badge de mensajes no leídos. Sidebar con navegación a módulos de Portal Vendedor y Reportes. Footer con información del usuario (avatar, nombre, rol, botón logout).

**Datos que consume**: GET /api/dashboard/vendor/{vendorId}, GET /api/dashboard/vendor/{vendorId}/orders-by-status, GET /api/dashboard/vendor/{vendorId}/top-products, GET /api/dashboard/vendor/{vendorId}/recent-activity
**Acciones**: Ver métricas, buscar pedidos/productos, acceder a notificaciones, navegar a módulos
**Roles que la ven**: Vendedor

#### RegistroPedidosPage
Formulario de creación de pedidos con tres secciones principales. Primera sección: Información del Cliente con campos RUC (búsqueda automática con botón lupa que consulta SAP), razón social (auto-rellenado readonly), representante (texto libre), condición de pago (selector: Contado, Crédito 30/60 días). Segunda sección: Productos del Pedido con tabla dinámica de productos agregados mostrando columnas (Código SAP, Producto con descripción, Tipo con badge azul para Venta y verde para Bonificación, Cantidad editable inline, Precio unitario, Subtotal calculado, Acciones con botón eliminar). Botón "Agregar Producto" que abre modal de búsqueda de catálogo. Tercera sección: Resumen del Pedido con subtotal, IGV (18%), bonificaciones (cantidad de unidades), y total destacado en grande. Alert informativo en la parte superior con instrucciones. Botones de acción: "Guardar Borrador" (outline) y "Enviar Pedido" (primario con icono enviar). Validaciones visuales: campos requeridos marcados con asterisco rojo, mensajes de error inline, confirmación modal antes de enviar.

**Datos que consume**: GET /api/clients/search?ruc={ruc}, GET /api/products (con filtros), POST /api/orders (crear/submit)
**Acciones**: Buscar cliente por RUC, agregar/eliminar productos, editar cantidades, calcular totales automáticamente, guardar borrador, enviar pedido, validar mínimos
**Roles que la ven**: Vendedor

#### ConsultaPedidosPage
Listado paginado de pedidos del vendedor autenticado. Toolbar superior con barra de búsqueda (por código o cliente), filtros combinables (Estado: Todos/Enviado/Aprobado/Rechazado; Fecha: Último mes/3 meses/Año/Personalizado), botón "Nuevo Pedido", botón "Exportar". Tabla con columnas: Código (formato PED-YYYY-NNNN en fuente monospace), Cliente (razón social + RUC en texto secundario), Representante, Fecha (formato DD MMM YYYY), Total (monto en soles con formato contable), Estado (badges con punto de color y texto), Acciones (iconos: ver detalle, descargar PDF, editar si estado=Enviado, reenviar si estado=Rechazado). Paginación en footer con contador "Mostrando X-Y de Z pedidos", selector de página numérica y flechas de navegación. Al hacer clic en "Ver detalle" abre modal con información completa del pedido: cliente, vendedor, fecha, productos con cantidades y precios, totales, historial de estados. Tabla responsive con scroll horizontal en mobile.

**Datos que consume**: GET /api/orders (con filtros, paginación, ordenamiento), GET /api/orders/{id}, GET /api/orders/{id}/pdf
**Acciones**: Buscar/filtrar pedidos, ver detalle en modal, descargar PDF, editar pedido (si permite), reenviar pedido rechazado, exportar listado a Excel, cambiar página, ordenar por columna
**Roles que la ven**: Vendedor

---

### Portal Distribuidor/Comercial

#### AprobacionPedidosPage
Vista de tarjetas (cards) expandibles para revisión de pedidos pendientes de aprobación. Header con título, subtítulo, y badge amarillo mostrando cantidad de pedidos pendientes. Toolbar con búsqueda (por código o cliente), filtro por vendedor, selector de ordenamiento (Más recientes/Monto mayor/Fecha más antigua). Cada tarjeta de pedido muestra: header con icono de bolsa de compras, código del pedido, fecha y hora de registro, badge de estado "Pendiente Aprobación" amarillo, monto total en grande en el lado derecho. Sección de información del cliente/vendedor en fondo gris claro con 3 columnas: Cliente (razón social + RUC), Vendedor (nombre + email), Condición de Pago. Listado de productos con tarjetas individuales mostrando icono de píldora, nombre del producto, código SAP, cantidad, precio unitario, con diferenciación visual para bonificaciones (fondo verde claro, borde verde, icono de regalo). Footer de la tarjeta con 3 botones de acción: "Aprobar Pedido" (verde primario con sombra), "Rechazar" (rojo outline), icono de comentarios. Al aprobar muestra confirmación modal antes de ejecutar. Al rechazar abre modal solicitando motivo obligatorio. Confirmación visual con toast de éxito/error.

**Datos que consume**: GET /api/orders/pending (con filtros), GET /api/orders/{id}/approval-detail, POST /api/orders/{id}/approve, POST /api/orders/{id}/reject, POST /api/orders/{id}/comments
**Acciones**: Buscar/filtrar pedidos pendientes, revisar detalles de productos, aprobar pedido con confirmación, rechazar con motivo, agregar comentarios internos
**Roles que la ven**: AdminComercial

#### GestionDevolucionesPage
Interfaz con pestañas: "Registrar Devolución" (activa por defecto) y "Historial". Tab de Registro muestra formulario con secciones. Primera sección: Información de la Devolución con campos Pedido Asociado (con búsqueda y botón lupa), Número de Factura (formato F001-00012345). Box de información del cliente auto-rellenado en fondo gris con 3 columnas: razón social + RUC, representante, fecha del pedido. Segunda sección: Productos a Devolver con tarjetas por producto. Cada tarjeta muestra: header con icono de píldora en fondo rojo claro, nombre del producto, código SAP, botón X para eliminar. Grid de 4 columnas: Cantidad a devolver (input numérico con máximo indicado debajo), Número de Lote (texto), Razón de Devolución (selector desplegable: Producto dañado, Fecha de vencimiento próxima, Error en el pedido, Cliente rechazó entrega, Defecto de fabricación), con valorizado calculado en footer de la tarjeta. Botón "Agregar Otro Producto" con borde punteado. Tercera sección: Observaciones Adicionales (textarea). Box de Resumen de Devolución en fondo rojo claro con border rojo mostrando total de productos/unidades y valorizado total destacado. Botones finales: "Cancelar" (outline), "Registrar Devolución" (primario rojo con icono check). Tab de Historial muestra tabla de devoluciones recientes con columnas: Código (DEV-YYYY-NNNN), Pedido, Cliente, Producto, Lote, Cantidad, Valorizado, Estado (badges: En Proceso amarillo, Aprobada verde).

**Datos que consume**: GET /api/orders/{id}/returnable-products, POST /api/returns, POST /api/returns/{id}/calculate-valorizado, GET /api/returns/reasons, GET /api/returns (tabla historial)
**Acciones**: Buscar pedido, auto-rellenar cliente, agregar/eliminar productos a devolver, ingresar cantidades y lotes, seleccionar razón, calcular valorizado automáticamente, agregar observaciones, registrar devolución, ver historial
**Roles que la ven**: AdminComercial

#### CalculoComisionesPage
Dashboard de gestión de comisiones por distribuidor. Header con título, subtítulo, selector de periodo mensual (mes/año con calendario desplegable), botón "Exportar Excel", botón primario "Ejecutar Cálculo". Sección de KPIs con 3 cards hero con gradientes de colores: Total Ventas del Mes (gradiente azul con comparativa porcentual vs mes anterior), Comisiones Totales (gradiente verde con contador de distribuidores activos), Recuperos por Devoluciones (gradiente rojo con cantidad de devoluciones procesadas). Cada KPI card tiene icono en fondo semi-transparente, valor principal en grande, y texto secundario. Sección de detalles por distribuidor con tarjetas expandibles. Tarjeta de Dimexa con header en gradiente azul claro, icono de edificio, nombre y RUC del distribuidor, comisión del periodo en verde destacado. Grid de 4 boxes: Ventas Totales, Porcentaje (badge azul 10%), Recuperos (en rojo con signo negativo), Neto a Pagar (verde con borde). Tabla de detalle con columnas: Concepto (Ventas Febrero 2025, Recupero Devoluciones), Monto Base, % (badges de porcentaje), Comisión (verde para ventas, rojo para recuperos). Footer de tabla con Total Neto en grande. Botones: "Ver Detalle" (outline), "Aprobar Pago" (verde primario). Tarjeta de Química Suiza con estructura idéntica pero gradiente morado y porcentaje de 13%. Validaciones: no permitir ejecución si ya existe cálculo aprobado del periodo, confirmación modal antes de aprobar pago.

**Datos que consume**: GET /api/commissions/summary?mes={mes}&año={año}, GET /api/commissions/calculate, POST /api/commissions, POST /api/commissions/{id}/approve, GET /api/commissions/{id}/detail, GET /api/commissions/export
**Acciones**: Seleccionar periodo, ver resumen de KPIs, ejecutar cálculo de comisiones, revisar detalle por distribuidor, ver desglose pedido por pedido, aprobar pago de comisión, exportar a Excel
**Roles que la ven**: Finanzas

---

### Reportes y Analítica

#### PowerBIReportsPage
Pantalla de embed de reportes de Power BI con diseño fullscreen. Header sticky con título, subtítulo, botones de acción: "Actualizar" (refrescar datos), "Compartir" (generar link), icono maximizar. Contenedor blanco con pestañas de reportes: "Ventas General" (activa), "Por Vendedor", "Por Distribuidor", "Por Producto", "Por Región". Área de embed del dashboard de Power BI con altura de 600px. Dentro del iframe embebido se visualiza: barra de filtros estilo Power BI con selectores de calendario (Último Trimestre), filtro de distribuidores (Todos), y botón de configuración de filtros avanzados. Dashboard con layout de 3 columnas: Columna izquierda (3 cols) con 4 KPI cards pequeños mostrando Ventas Totales, Pedidos Procesados, Tasa de Aprobación, Devoluciones, cada uno con valor principal, trending (flecha arriba/abajo) y porcentaje de cambio. Columna central (6 cols) con gráfico de barras verticales "Evolución de Ventas Mensual" mostrando últimos 6 meses con gradiente azul, mes actual destacado con sombra. Columna derecha (3 cols) con gráfico de dona "Ventas por Distribuidor" mostrando distribución porcentual Dimexa/Química con leyenda, y tabla "Top Productos" con 4 filas. Logo de Power BI en esquina inferior izquierda. Footer de la página con botones "Exportar PDF" y "Exportar Excel", timestamp de última actualización ("Última actualización: Hace 5 minutos"). Sección de galería de otros reportes disponibles con 3 tarjetas clicables: Rendimiento por Vendedor (icono usuarios azul), Análisis de Comisiones (icono porcentaje verde), Devoluciones & Recuperos (icono paquete rojo), cada una con título, descripción breve, y enlace "Ver reporte →".

**Datos que consume**: GET /api/reports/embed-token, GET /api/reports/list, GET /api/reports/last-refresh
**Acciones**: Cambiar entre pestañas de reportes, aplicar filtros de Power BI (fecha, distribuidor, vendedor), refrescar datos, maximizar pantalla, exportar PDF/Excel, navegar a otros reportes
**Roles que la ven**: Vendedor (vistas filtradas por usuario), AdminComercial, Finanzas, GerenteGeneral (vistas completas)

---

## COMPONENTES

### Layout

#### AppLayout
Estructura general de la aplicación con sidebar fijo de 256px de ancho (64 en Tailwind: w-64), header horizontal de 64px de altura, y área de contenido principal con scroll vertical. Sidebar incluye: logo de BONAPHARM en header del sidebar (32x32px, fondo azul primario, icono de actividad blanco), navegación en lista vertical con items colapsables por sección (Portal Vendedor, Portal Distribuidor, Reportes), item activo resaltado con fondo azul claro y texto azul primario, items inactivos con hover gris. Footer del sidebar con card de perfil mostrando avatar circular con iniciales en gradiente, nombre del usuario, rol en texto secundario, y botón de logout. Header principal con título de página (h1 semibold), subtítulo descriptivo (texto secundario), y área de acciones contextuales en el lado derecho. Contenido principal con padding de 24px (p-6), fondo gris claro (bg-slate-50). Layout responsive: en mobile (<768px) el sidebar se oculta y se muestra mediante botón hamburguesa, en tablet (768-1024px) sidebar colapsado a iconos únicamente.

**Props**: `currentUser` (object: { id, nombre, email, rol, avatar }), `activePage` (string), `children` (ReactNode)
**Comportamiento**: Resalta navegación activa según ruta, oculta/muestra sidebar en mobile, ejecuta logout al hacer clic en botón salir
**Variantes**: SidebarCollapsed (solo iconos), SidebarHidden (mobile)

#### TopBar
Header horizontal sticky (sticky top-0 z-10) con fondo blanco, borde inferior gris, altura de 64px. Contiene dos secciones: izquierda con título de página (text-lg font-semibold) y subtítulo (text-xs text-slate-500), derecha con barra de búsqueda global (solo desktop, ancho 256px), icono de notificaciones con badge rojo circular si hay no leídas, y opcional área de acciones contextuales (botones específicos de cada página). Búsqueda incluye icono de lupa a la izquierda, placeholder "Buscar pedidos, productos...", y autocompletado con dropdown. Notificaciones al hacer clic muestran dropdown con lista de últimas 5, cada una con icono, mensaje breve, timestamp, y badge de no leída. Footer del dropdown con enlace "Ver todas".

**Props**: `pageTitle` (string), `pageSubtitle` (string), `actions` (ReactNode), `onSearch` (function), `notifications` (array)
**Comportamiento**: Ejecuta búsqueda global al escribir (debounce 300ms), abre dropdown de notificaciones al clic, marca como leída al hacer clic en notificación
**Variantes**: Con búsqueda, sin búsqueda, con acciones, sin acciones

#### Sidebar
Navegación lateral con estructura jerárquica. Logo de BONAPHARM en header de 64px de altura con borde inferior. Área de navegación con scroll vertical si el contenido excede la altura disponible. Items de navegación agrupados por sección con headers en texto gris (text-xs font-semibold text-slate-400 uppercase). Items de navegación con iconos de Lucide (20x20px), texto del item, y estado activo (fondo azul claro, texto azul, borde izquierdo azul de 4px). Hover en items inactivos muestra fondo gris claro. Footer del sidebar con tarjeta de perfil: avatar de 40x40px con gradiente de fondo y iniciales, nombre truncado con ellipsis, rol en texto secundario, botón de logout como icono pequeño en la derecha.

**Props**: `menuItems` (array de { id, label, icon, href, section }), `currentUser` (object), `activePath` (string), `onLogout` (function)
**Comportamiento**: Resalta item activo según path, ejecuta navegación al hacer clic, ejecuta logout al hacer clic en botón salir
**Variantes**: Collapsed (solo iconos y logos pequeños), Expanded (texto completo)

---

### Comunes

#### DataTable
Tabla genérica reutilizable con paginación, filtros, ordenamiento y acciones por fila. Header de tabla con fondo gris claro (bg-slate-50), columnas configurables con texto de header en gris oscuro (text-slate-500 font-medium). Filas con hover en gris claro (hover:bg-slate-50), bordes horizontales entre filas (divide-y divide-slate-100). Soporte de ordenamiento con iconos de chevron en headers clicables. Columna de acciones con iconos de botón (ver, editar, eliminar, descargar) con hover colorido. Footer con paginación: texto "Mostrando X-Y de Z registros", selector de página numérica (botones 1,2,3,...,N), flechas de navegación prev/next. Soporte de estados vacíos (ilustración + mensaje "No se encontraron resultados") y estados de carga (skeleton loaders en filas).

**Props**: `columns` (array de { key, label, sortable, align }), `data` (array de objetos), `actions` (array de { icon, label, onClick, color }), `pagination` (object: { page, perPage, total }), `onSort` (function), `onPageChange` (function), `loading` (boolean), `emptyMessage` (string)
**Comportamiento**: Renderiza columnas dinámicamente, ejecuta ordenamiento al clic en header, ejecuta acciones al clic en botón de fila, cambia de página al clic en paginador
**Variantes**: Con acciones, sin acciones, con ordenamiento, sin ordenamiento, con paginación, sin paginación

#### StatusBadge
Badge de estado con punto de color y texto. Tamaño pequeño (px-2.5 py-0.5), bordes redondeados (rounded-full), texto pequeño (text-xs font-medium). Punto circular de 6px de diámetro (w-1.5 h-1.5 rounded-full) en el lado izquierdo del texto. Variantes de color según estado: Aprobado (bg-green-50 text-green-700, punto bg-green-500), Enviado (bg-yellow-50 text-yellow-700, punto bg-yellow-500), Rechazado (bg-red-50 text-red-700, punto bg-red-500), En Proceso (bg-blue-50 text-blue-700, punto bg-blue-500), Borrador (bg-slate-50 text-slate-700, punto bg-slate-500).

**Props**: `status` (enum: Aprobado, Enviado, Rechazado, En Proceso, Borrador), `text` (string opcional, si no se proporciona usa status)
**Comportamiento**: Renderiza badge con color según status
**Variantes**: Aprobado, Enviado, Rechazado, En Proceso, Borrador

#### SearchBar
Barra de búsqueda con icono de lupa a la izquierda. Input de texto con padding izquierdo para el icono (pl-10), borde gris (border-slate-300), bordes redondeados (rounded-lg), focus con anillo azul (focus:ring-2 focus:ring-primary/20 focus:border-primary). Icono de lupa posicionado absolutamente (absolute left-3 top-1/2 -translate-y-1/2) en gris (text-slate-400). Placeholder descriptivo según contexto. Soporte de autocompletado con dropdown debajo del input mostrando resultados filtrados, cada resultado con hover en gris claro.

**Props**: `placeholder` (string), `value` (string), `onChange` (function), `onSearch` (function), `autoComplete` (boolean), `suggestions` (array)
**Comportamiento**: Ejecuta onChange al escribir, ejecuta onSearch al presionar Enter o después de 300ms sin escribir (debounce), muestra dropdown de sugerencias si autoComplete=true
**Variantes**: Con autocompletado, sin autocompletado, con icono derecho (X para limpiar)

#### FilterBar
Barra de filtros con múltiples selectores en línea horizontal. Cada filtro es un selector desplegable (select) con borde gris, texto pequeño (text-sm), y chevron-down a la derecha. Filtros comunes: Estado (multi-select con checkboxes), Fecha (selector de rango con calendario desplegable), Vendedor (multi-select), Distribuidor (multi-select). Botón opcional "Aplicar Filtros" si los filtros no se aplican automáticamente. Indicador visual de filtros activos (badge con número de filtros aplicados). Botón "Limpiar Filtros" para resetear todos.

**Props**: `filters` (array de { key, label, type, options }), `activeFilters` (object), `onChange` (function), `onClear` (function)
**Comportamiento**: Ejecuta onChange al seleccionar opción en filtro, ejecuta onClear al hacer clic en limpiar, muestra badge con cantidad de filtros activos
**Variantes**: Con aplicación manual (botón Aplicar), con aplicación automática (onChange inmediato)

#### Modal
Modal centrado con overlay semi-transparente oscuro (bg-black/50). Contenedor del modal con fondo blanco, bordes redondeados (rounded-xl), sombra grande (shadow-xl), ancho máximo configurable. Header del modal con título (text-lg font-semibold), botón X en esquina superior derecha. Contenido del modal con padding (p-6), scroll vertical si excede altura máxima. Footer del modal con botones de acción alineados a la derecha (Cancelar outline, Aceptar primario). Animación de entrada (fade in + scale from 95% to 100%). Cierre al hacer clic en overlay o botón X.

**Props**: `isOpen` (boolean), `onClose` (function), `title` (string), `children` (ReactNode), `footer` (ReactNode), `size` (enum: sm, md, lg, xl)
**Comportamiento**: Muestra/oculta según isOpen, ejecuta onClose al hacer clic en overlay o X, bloquea scroll del body cuando está abierto
**Variantes**: Pequeño (max-w-md), Mediano (max-w-lg), Grande (max-w-2xl), Extra grande (max-w-4xl)

#### Toast
Notificación tipo toast que aparece en esquina superior derecha. Contenedor con fondo blanco, borde según tipo, sombra, bordes redondeados (rounded-lg). Icono a la izquierda según tipo (check verde para success, X rojo para error, info azul para info, alerta amarilla para warning). Texto del mensaje (text-sm). Botón X pequeño en la derecha para cerrar. Auto-cierre después de 5 segundos (configurable). Animación de entrada desde arriba (slide down) y salida hacia arriba (slide up).

**Props**: `message` (string), `type` (enum: success, error, info, warning), `duration` (number, default 5000), `onClose` (function)
**Comportamiento**: Muestra toast al montar, auto-cierra después de duration, ejecuta onClose al cerrar
**Variantes**: Success (verde), Error (rojo), Info (azul), Warning (amarillo)

#### Card
Contenedor genérico tipo tarjeta con fondo blanco, borde gris (border-slate-200), bordes redondeados (rounded-xl), padding configurable. Soporte de hover con elevación (hover:shadow-md transition-shadow). Header opcional de la card con título (text-base font-semibold), subtítulo (text-sm text-slate-500), y área de acciones en la derecha (ej: botón de más opciones). Contenido de la card con padding (p-6). Footer opcional con borde superior (border-t border-slate-200).

**Props**: `title` (string), `subtitle` (string), `children` (ReactNode), `footer` (ReactNode), `headerActions` (ReactNode), `hoverable` (boolean)
**Comportamiento**: Renderiza header si title existe, renderiza footer si se proporciona, aplica hover si hoverable=true
**Variantes**: Con header, sin header, con footer, sin footer, con hover, sin hover

#### Button
Botón genérico con múltiples variantes de estilo. Tamaños: sm (px-3 py-1.5 text-xs), md (px-4 py-2 text-sm), lg (px-6 py-3 text-base). Variantes de estilo: Primary (bg-primary text-white hover:bg-primary-hover shadow-lg), Secondary (bg-slate-200 text-slate-700 hover:bg-slate-300), Outline (border border-slate-300 bg-white text-slate-700 hover:bg-slate-50), Ghost (text-slate-600 hover:bg-slate-100), Danger (bg-red-600 text-white hover:bg-red-700). Soporte de icono a la izquierda o derecha del texto. Estados: normal, hover, loading (spinner animado), disabled (opacity-50 cursor-not-allowed). Bordes redondeados (rounded-lg). Transiciones suaves (transition-colors duration-200).

**Props**: `variant` (enum: primary, secondary, outline, ghost, danger), `size` (enum: sm, md, lg), `icon` (ReactNode), `iconPosition` (enum: left, right), `loading` (boolean), `disabled` (boolean), `onClick` (function), `children` (ReactNode)
**Comportamiento**: Ejecuta onClick al hacer clic (si no disabled o loading), muestra spinner si loading=true, deshabilita interacción si disabled=true
**Variantes**: Primary, Secondary, Outline, Ghost, Danger, con icono izquierdo, con icono derecho, loading, disabled

#### FormField
Campo de formulario con label, input, y mensajes de error/ayuda. Label en la parte superior (text-sm font-medium text-slate-700), opcional asterisco rojo para campos requeridos. Input con borde gris (border-slate-300), bordes redondeados (rounded-lg), focus con anillo azul (focus:ring-2 focus:ring-primary/20 focus:border-primary). Mensaje de error debajo del input en rojo (text-xs text-red-600) si hay error. Mensaje de ayuda debajo del input en gris (text-xs text-slate-500) si no hay error. Soporte de icono a la izquierda del input (posición absoluta). Variantes de input: text, email, number, password, textarea, select.

**Props**: `label` (string), `type` (enum: text, email, number, password, textarea, select), `required` (boolean), `value` (string|number), `onChange` (function), `error` (string), `helpText` (string), `icon` (ReactNode), `options` (array, solo para select)
**Comportamiento**: Ejecuta onChange al modificar valor, muestra mensaje de error si existe, muestra asterisco si required=true
**Variantes**: Text input, Email input, Number input, Password input, Textarea, Select dropdown

---

### Portal Vendedor

#### OrderSummaryCard
Card de resumen de pedido con tres filas de información. Primera fila: Subtotal con valor en soles alineado a la derecha. Segunda fila: IGV (18%) con valor. Tercera fila: Bonificaciones con icono de regalo verde y cantidad de unidades en verde. Separador horizontal (border-t). Cuarta fila destacada: Total en texto grande (text-lg font-semibold) con valor en azul primario de tamaño extra grande (text-2xl font-bold text-primary). Fondo blanco, borde gris, bordes redondeados.

**Props**: `subtotal` (number), `igv` (number), `bonificaciones` (number), `total` (number)
**Comportamiento**: Formatea montos con separador de miles y 2 decimales, muestra bonificaciones en verde
**Variantes**: Versión compacta (sin separador de miles)

#### ProductSearchModal
Modal de búsqueda y selección de productos. Header con título "Agregar Producto" y barra de búsqueda. Filtros opcionales: Distribuidor (Dimexa, Química), Molécula (autocompletado). Grid de productos encontrados, cada uno en una tarjeta con: código SAP en fuente monospace, nombre del producto, molécula en texto secundario, precio VVF, distribuidor en badge, stock disponible. Botón "Agregar" en cada tarjeta. Footer del modal con contador de productos seleccionados y botón "Agregar al Pedido". Paginación si hay más de 20 productos. Estado de carga con skeleton loaders. Estado vacío si no hay resultados.

**Props**: `isOpen` (boolean), `onClose` (function), `onAddProducts` (function), `selectedProducts` (array)
**Comportamiento**: Ejecuta búsqueda al escribir (debounce 300ms), permite seleccionar múltiples productos, ejecuta onAddProducts al confirmar, cierra modal al confirmar o cancelar
**Variantes**: Selección simple, selección múltiple

#### DashboardKPICard
Card compacta de KPI con icono en esquina superior derecha en fondo de color semi-transparente, label del KPI en texto pequeño gris, valor principal en tamaño grande (text-3xl font-bold), y texto secundario con trending (icono flecha arriba/abajo + porcentaje en verde o rojo). Fondo blanco, borde gris, bordes redondeados, hover con sombra.

**Props**: `label` (string), `value` (string|number), `icon` (ReactNode), `iconColor` (string), `trending` (object: { direction: 'up'|'down', value: string })
**Comportamiento**: Muestra icono en color de fondo correspondiente, muestra trending en verde si up, rojo si down
**Variantes**: Con trending, sin trending, con icono, sin icono

---

### Portal Distribuidor/Comercial

#### OrderApprovalCard
Tarjeta expandible de pedido pendiente de aprobación. Border de 2px amarillo si es urgente, border normal si no. Header con icono de bolsa en fondo amarillo claro, código del pedido en grande (text-lg font-semibold), fecha y hora de registro en texto secundario, badge de estado "Pendiente Aprobación" amarillo, monto total en grande en la derecha (text-2xl font-bold). Sección de información con fondo gris claro, grid de 3 columnas: Cliente (nombre + RUC), Vendedor (nombre + email), Condición de Pago. Sección de productos con label "Productos del Pedido (N items)", lista de productos cada uno en tarjeta pequeña con icono de píldora en fondo azul claro, nombre del producto, código SAP, cantidad, precio unitario. Bonificaciones destacadas con fondo verde claro, icono de regalo, sin precio. Footer con 3 botones: "Aprobar Pedido" (verde primario con sombra), "Rechazar" (rojo outline), icono de mensaje (outline). Animación de hover en la tarjeta completa (sombra elevada).

**Props**: `order` (object: { id, codigo, fecha, cliente, vendedor, condicion_pago, productos, total, estado })
**Comportamiento**: Ejecuta onApprove con confirmación modal, ejecuta onReject abriendo modal de motivo, ejecuta onComment abriendo modal de comentarios
**Variantes**: Urgente (border amarillo grueso), Normal (border gris)

#### ReturnProductCard
Tarjeta de producto a devolver con header mostrando icono de píldora en fondo rojo claro, nombre del producto, código SAP, botón X para eliminar. Grid de inputs en 4 columnas: Cantidad a devolver (input number con validación de máximo, texto ayuda "Máx: X unidades"), Número de lote (input text), Razón de devolución (select con opciones predefinidas). Footer con separador y valorizado calculado en rojo (text-sm font-semibold text-red-600). Border gris, bordes redondeados, padding.

**Props**: `product` (object: { id, nombre, codigo_sap, precio_unitario, cantidad_maxima }), `onRemove` (function), `onChange` (function)
**Comportamiento**: Ejecuta onChange al modificar cantidad/lote/razón, calcula valorizado automáticamente, ejecuta onRemove al hacer clic en X, valida cantidad <= cantidad_maxima
**Variantes**: Con validación de cantidad, sin validación

#### CommissionCalculatorCard
Tarjeta de distribuidor con header en gradiente de color (azul para Dimexa, morado para Química), icono de edificio, nombre del distribuidor, RUC, comisión total del periodo en verde destacado en la derecha. Grid de 4 boxes pequeños con fondo gris claro: Ventas Totales, Porcentaje (badge de color), Recuperos (en rojo con negativo), Neto a Pagar (verde con borde). Tabla de detalle con headers gris claro, filas para Ventas y Recuperos, footer con Total Neto destacado. Footer con dos botones: "Ver Detalle" (outline), "Aprobar Pago" (verde primario).

**Props**: `distributor` (object: { nombre, ruc, ventas, porcentaje, recuperos, neto_a_pagar, detalles }), `onApprove` (function), `onViewDetail` (function)
**Comportamiento**: Ejecuta onApprove con confirmación modal, ejecuta onViewDetail abriendo modal con desglose completo
**Variantes**: Dimexa (gradiente azul), Química (gradiente morado)

---

### Reportes

#### PowerBIEmbed
Contenedor de iframe para embed de Power BI. Altura configurable (default 600px), ancho 100%. Barra de filtros de Power BI estilo nativo con selectores de fecha, distribuidor, vendedor. Placeholder mientras carga el reporte (spinner + texto "Cargando reporte..."). Estado de error si falla la carga (mensaje + botón reintentar). Logo de Power BI en esquina inferior izquierda. Botones de control en esquina superior derecha: Maximizar (fullscreen), Compartir, Refrescar.

**Props**: `embedUrl` (string), `embedToken` (string), `reportId` (string), `height` (number), `filters` (object), `onLoad` (function), `onError` (function)
**Comportamiento**: Carga iframe con embedUrl + token, aplica filtros de Power BI mediante postMessage, ejecuta onLoad cuando termina de cargar, ejecuta onError si falla, permite maximizar a fullscreen
**Variantes**: Con filtros, sin filtros, con botones de control, sin botones

#### ReportGalleryCard
Tarjeta de reporte disponible con hover elevado. Icono en fondo de color semi-transparente en esquina superior izquierda, título del reporte (text-sm font-semibold), descripción breve (text-xs text-slate-500), enlace "Ver reporte →" en azul primario. Border gris, bordes redondeados, padding, hover con sombra grande y elevación de icono de fondo.

**Props**: `title` (string), `description` (string), `icon` (ReactNode), `iconColor` (string), `onClick` (function)
**Comportamiento**: Ejecuta onClick al hacer clic en la tarjeta o enlace, aplica animación de hover
**Variantes**: Con icono azul, verde, rojo, morado según categoría del reporte

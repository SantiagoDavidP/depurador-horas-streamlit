# Construction - Automatización de Pedidos y Devoluciones BONAPHARM

## Stack

- **Frontend**: Microsoft Power Pages (Portal), Tailwind CSS 3.x, Lucide Icons, JavaScript ES6+ para interacciones cliente
- **Backend**: Microsoft Power Automate (Cloud Flows), Power Fx (fórmulas), Custom Connectors para APIs externas
- **Base de datos**: Microsoft Dataverse (base de datos primaria, OData API v9.2), Azure SQL Database (respaldo y reportes complejos si necesario)
- **Autenticación**: Microsoft Entra ID (Azure Active Directory), OAuth 2.0, OpenID Connect, MFA habilitado
- **Almacenamiento**: SharePoint Online (Document Library para exports Excel, PDFs), Azure Blob Storage (archivos temporales)
- **Cache**: Memoria caché de Dataverse (automática), Redis Cache (opcional para alto volumen)
- **Tareas programadas**: Power Automate Scheduled Flows (sincronización SAP cada 6 horas, cálculo mensual de comisiones)
- **Notificaciones**: Office 365 Outlook Connector (emails transaccionales), Power Automate Push Notifications
- **Infraestructura**: Microsoft Power Platform Environment (DEV, QA, PROD), Azure API Management (opcional para gateway), Application Insights (telemetría)
- **Monitoreo**: Power Platform Admin Center (auditoría), Application Insights (logs y métricas), Power Automate Analytics

## Estructura

```
BONAPHARM_Solution/
├── Dataverse/
│   ├── Tables/
│   │   ├── Pedido.json                  # Definición de tabla Pedido con columnas, relaciones
│   │   ├── DetallePedido.json           # Líneas de productos en pedidos
│   │   ├── Devolucion.json              # Registro de devoluciones
│   │   ├── Producto.json                # Catálogo sincronizado desde SAP
│   │   ├── Comision.json                # Cálculos de comisiones por periodo
│   │   ├── User.json                    # Usuarios del sistema (sincronizado con Entra ID)
│   │   ├── AuditLog.json                # Logs de auditoría de acciones
│   │   └── Notification.json            # Notificaciones del sistema
│   ├── Views/
│   │   ├── Pedido_ActiveOrders.xml      # Vista de pedidos activos
│   │   ├── Pedido_PendingApproval.xml   # Vista de pedidos pendientes
│   │   ├── Devolucion_Recent.xml        # Vista de devoluciones recientes
│   │   └── Producto_Catalog.xml         # Vista del catálogo de productos
│   ├── Forms/
│   │   ├── Pedido_MainForm.xml          # Formulario principal de pedido
│   │   ├── Devolucion_MainForm.xml      # Formulario de devolución
│   │   └── Comision_DetailForm.xml      # Formulario de detalle de comisión
│   ├── BusinessRules/
│   │   ├── Pedido_ValidateMinimums.json # Validación de mínimos al crear pedido
│   │   ├── Pedido_CalculateTotals.json  # Cálculo automático de subtotal, IGV, total
│   │   └── Devolucion_CalculateValorizado.json # Cálculo de valorizado de devolución
│   └── SecurityRoles/
│       ├── Vendedor.xml                 # Permisos: crear pedidos, consultar propios
│       ├── AdminComercial.xml           # Permisos: aprobar pedidos, gestionar devoluciones
│       ├── Finanzas.xml                 # Permisos: calcular comisiones, aprobar pagos
│       └── GerenteGeneral.xml           # Permisos: acceso completo a reportes
│
├── PowerPages/
│   ├── Portals/
│   │   ├── PortalVendedores/
│   │   │   ├── web-pages/
│   │   │   │   ├── login.html           # Página de autenticación (01-login.html)
│   │   │   │   ├── dashboard.html       # Dashboard del vendedor (02-dashboard.html)
│   │   │   │   ├── registro-pedidos.html # Formulario de registro (03-registro-pedidos.html)
│   │   │   │   └── consulta-pedidos.html # Listado de pedidos (04-consulta-pedidos.html)
│   │   │   ├── web-templates/
│   │   │   │   ├── header.html          # Header común con navegación y perfil
│   │   │   │   ├── sidebar.html         # Sidebar con menú de navegación
│   │   │   │   └── footer.html          # Footer con info de copyright
│   │   │   ├── web-files/
│   │   │   │   ├── css/
│   │   │   │   │   └── tailwind.config.js # Configuración de Tailwind
│   │   │   │   ├── js/
│   │   │   │   │   ├── auth.js          # Lógica de autenticación
│   │   │   │   │   ├── pedidos.js       # Funciones de gestión de pedidos
│   │   │   │   │   └── utils.js         # Utilidades comunes
│   │   │   │   └── images/
│   │   │   │       └── logo-bonapharm.png
│   │   │   └── site-settings.yml        # Configuración del portal vendedores
│   │   └── PortalDistribuidores/
│   │       ├── web-pages/
│   │       │   ├── aprobacion-pedidos.html # Revisión y aprobación (05-aprobacion-pedidos.html)
│   │       │   ├── gestion-devoluciones.html # Devoluciones (06-gestion-devoluciones.html)
│   │       │   ├── calculo-comisiones.html # Comisiones (07-calculo-comisiones.html)
│   │       │   └── reportes.html        # Power BI embebido (08-reportes.html)
│   │       ├── web-templates/
│   │       │   ├── header-admin.html    # Header para roles administrativos
│   │       │   └── sidebar-admin.html   # Sidebar con opciones de distribuidor
│   │       ├── web-files/
│   │       │   └── js/
│   │       │       ├── aprobaciones.js  # Lógica de aprobación/rechazo
│   │       │       ├── devoluciones.js  # Lógica de gestión de devoluciones
│   │       │       └── comisiones.js    # Lógica de cálculo de comisiones
│   │       └── site-settings.yml
│   └── configuration/
│       ├── entra-id.json                # Configuración de autenticación Entra ID
│       └── permissions.json             # Matriz de permisos por rol
│
├── PowerAutomate/
│   ├── Flows/
│   │   ├── NotificacionPedidos/
│   │   │   ├── flow.json                # Definición del flujo
│   │   │   ├── trigger.json             # Trigger: cuando se crea Pedido con estado 'Enviado'
│   │   │   ├── actions/
│   │   │   │   ├── get-pedido-details.json # Obtener detalles del pedido
│   │   │   │   ├── get-admin-email.json    # Consultar email de admin comercial
│   │   │   │   ├── send-email.json         # Enviar notificación por email
│   │   │   │   └── create-notification.json # Crear registro en tabla Notification
│   │   │   └── connections.json         # Conexiones a Dataverse y Office 365
│   │   ├── AprobacionDevoluciones/
│   │   │   ├── flow.json
│   │   │   ├── trigger.json             # Trigger: cuando se crea Devolucion
│   │   │   ├── actions/
│   │   │   │   ├── get-devolucion-details.json
│   │   │   │   ├── get-finanzas-email.json
│   │   │   │   ├── send-email.json
│   │   │   │   └── update-audit-log.json
│   │   │   └── connections.json
│   │   ├── CalculoComisiones/
│   │   │   ├── flow.json
│   │   │   ├── trigger.json             # Trigger: scheduled (primer día de cada mes a las 2:00 AM)
│   │   │   ├── actions/
│   │   │   │   ├── get-pedidos-mes-anterior.json # Consultar pedidos del mes anterior
│   │   │   │   ├── get-devoluciones-mes-anterior.json
│   │   │   │   ├── calculate-dimexa-commission.json # Cálculo para Dimexa (10%)
│   │   │   │   ├── calculate-quimica-commission.json # Cálculo para Química (13%)
│   │   │   │   ├── create-comision-record.json # Guardar en tabla Comision
│   │   │   │   ├── export-to-excel.json # Generar Excel y guardar en SharePoint
│   │   │   │   └── send-notification.json
│   │   │   └── connections.json
│   │   └── IntegracionSAP/
│   │       ├── flow.json
│   │       ├── trigger.json             # Trigger: scheduled (cada 6 horas)
│   │       ├── actions/
│   │       │   ├── call-sap-inventory-api.json # GET /api/sap/inventory
│   │       │   ├── parse-json-response.json
│   │       │   ├── loop-productos.json  # Iterar sobre productos de SAP
│   │       │   ├── upsert-producto-dataverse.json # Crear o actualizar Producto
│   │       │   └── log-sync-result.json
│   │       └── connections.json         # Conexión a SAP API (Custom Connector)
│   └── CustomConnectors/
│       └── SAP_API_Connector/
│           ├── apiDefinition.swagger.json # Definición OpenAPI 3.0 de SAP API
│           ├── apiProperties.json       # Configuración de autenticación (API Key)
│           └── icon.png                 # Icono del conector SAP
│
├── PowerBI/
│   ├── Dashboards/
│   │   ├── ReporteGerencial.pbix        # Archivo Power BI Desktop
│   │   │   ├── Datasets/
│   │   │   │   ├── Pedidos_Dataset.pbit # Consulta a Dataverse tabla Pedido
│   │   │   │   ├── Devoluciones_Dataset.pbit
│   │   │   │   ├── Comisiones_Dataset.pbit
│   │   │   │   └── Productos_Dataset.pbit
│   │   │   ├── Reports/
│   │   │   │   ├── VentasGeneral_Page.json # Página principal con KPIs y gráficos
│   │   │   │   ├── PorVendedor_Page.json
│   │   │   │   ├── PorDistribuidor_Page.json
│   │   │   │   ├── PorProducto_Page.json
│   │   │   │   └── PorRegion_Page.json
│   │   │   └── Visuals/
│   │   │       ├── KPI_VentasTotales.json
│   │   │       ├── Chart_EvolucionMensual.json # Gráfico de barras
│   │   │       ├── Donut_Distribuidores.json
│   │   │       └── Table_TopProductos.json
│   │   └── deployment/
│   │       ├── publish-settings.json    # Configuración de publicación a Power BI Service
│   │       └── embed-config.json        # Tokens y URLs de embed para Power Pages
│   └── DataFlows/
│       └── Dataverse_Refresh.json       # Flujo de actualización de datos cada hora
│
├── SharePoint/
│   ├── DocumentLibraries/
│   │   ├── DEV/
│   │   │   ├── Exports/                 # Carpeta para exports de Excel/PDF en desarrollo
│   │   │   └── Logs/                    # Logs de sincronización
│   │   ├── QA/
│   │   │   ├── Exports/
│   │   │   └── TestData/                # Datos de prueba
│   │   └── PROD/
│   │       ├── Exports/
│   │       │   ├── Pedidos/             # Exports de pedidos por mes
│   │       │   ├── Devoluciones/
│   │       │   └── Comisiones/
│   │       └── Archives/                # Archivos históricos (retención 2 años)
│   └── Lists/
│       └── ConfiguracionGeneral/        # Lista para parámetros de configuración
│           ├── Distribuidores.json      # Mínimos y porcentajes por distribuidor
│           ├── CondicionesPago.json     # Catálogo de condiciones de pago
│           └── RazonesDevoluciones.json # Catálogo de razones de devolución
│
├── Tests/                               # Pruebas unitarias e integración
│   ├── PowerAutomate/
│   │   ├── test-notificacion-pedidos.json
│   │   ├── test-calculo-comisiones.json
│   │   └── test-integracion-sap.json
│   └── PowerPages/
│       ├── test-login.js                # Selenium tests para autenticación
│       ├── test-registro-pedidos.js
│       └── test-aprobacion.js
│
├── Deployment/
│   ├── Environments/
│   │   ├── DEV.env                      # Variables de entorno desarrollo
│   │   ├── QA.env                       # Variables de entorno QA
│   │   └── PROD.env                     # Variables de entorno producción
│   ├── Scripts/
│   │   ├── deploy-solution.ps1          # Script PowerShell para despliegue
│   │   ├── create-environments.ps1      # Crear ambientes de Power Platform
│   │   ├── import-sample-data.ps1       # Importar datos de prueba
│   │   └── configure-security.ps1       # Configurar roles y permisos
│   └── Migrations/
│       ├── 001_initial_schema.xml       # Migración inicial de tablas Dataverse
│       ├── 002_add_audit_log.xml        # Agregar tabla AuditLog
│       └── 003_update_comision_fields.xml # Actualización de campos de comisión
│
├── Documentation/
│   ├── API/
│   │   ├── swagger.yaml                 # Documentación OpenAPI de endpoints
│   │   └── postman-collection.json      # Colección Postman para testing
│   ├── UserGuides/
│   │   ├── Manual_Vendedor.pdf          # Manual de usuario para vendedores
│   │   ├── Manual_AdminComercial.pdf    # Manual para administradores comerciales
│   │   └── Manual_Finanzas.pdf          # Manual para finanzas
│   └── Technical/
│       ├── arquitectura.drawio          # Diagrama de arquitectura (archivo leído)
│       ├── data-model.drawio            # Diagrama de modelo de datos
│       └── workflows.drawio             # Diagramas de flujos de Power Automate
│
├── .env.example                         # Plantilla de variables de entorno
├── solution.xml                         # Definición de la solución de Power Platform
├── manifest.json                        # Manifiesto de la aplicación
└── README.md                            # Documentación principal del proyecto
```

## Requisitos No Funcionales

### Rendimiento
- El sistema debe procesar 500 solicitudes mensuales con un crecimiento proyectado del 20% mensual durante 24 meses sin degradación de rendimiento
- Tiempo de respuesta de consultas a Dataverse: máximo 2 segundos para listados paginados
- Tiempo de respuesta de consultas a SAP API: máximo 10 segundos con timeout y reintentos automáticos
- Carga de páginas de Power Pages: máximo 3 segundos para First Contentful Paint (FCP)
- Renderizado de reportes de Power BI: máximo 5 segundos para datasets con hasta 50,000 registros
- Workflows de Power Automate: procesamiento de notificaciones en menos de 30 segundos desde el trigger

### Escalabilidad
- Arquitectura stateless: Los flows de Power Automate no mantienen estado entre ejecuciones
- Escalado automático de Power Pages: manejado por Azure infraestructura subyacente
- Particionamiento de datos en Dataverse por año para mejorar rendimiento de consultas históricas
- Índices en campos clave: codigo_pedido, cliente_ruc, fecha, estado, codigo_sap
- Interfaz responsive con diseño mobile-first: funcional en resoluciones HD (1920×1080), tablets (768×1024), smartphones (375×667)
- Paginación obligatoria en listados: máximo 50 registros por página en tablas de Power Pages

### Seguridad
- Cifrado en tránsito: TLS 1.2+ para todas las comunicaciones HTTPS
- Cifrado en reposo: AES-256 automático en Dataverse y SharePoint
- Autenticación multi-factor (MFA) obligatoria para roles Finanzas y GerenteGeneral
- Control de acceso basado en roles (RBAC) con permisos granulares por entidad (Create, Read, Update, Delete, Append, Assign)
- Validación de entrada: sanitización de inputs en Power Pages para prevenir SQL Injection y XSS
- Rate limiting: 100 requests por minuto por usuario autenticado en APIs de Dataverse
- Auditoría completa: todos los cambios en Pedido, Devolucion, Comision registrados en AuditLog con usuario, timestamp, valores anteriores/nuevos
- Tokens JWT con expiración: 60 minutos de vida, refresh token válido por 7 días
- Secretos gestionados en Azure Key Vault: ENTRA_ID_CLIENT_ID, ENTRA_ID_SECRET_KEY, SAP_API_KEY

### Disponibilidad
- SLA de Azure: 99.99% de uptime garantizado por Microsoft para Power Platform
- Backup automático de Dataverse: incremental cada 12 horas, full backup diario a las 2:00 AM UTC
- Retención de backups: 30 días para ambiente PROD, 7 días para DEV/QA
- Ventanas de mantenimiento: domingos de 2:00 AM a 4:00 AM hora local (Perú UTC-5)
- Monitoreo proactivo: Application Insights con alertas configuradas para errores críticos (tasa de error > 5%)
- Recuperación ante desastres (DR): Geo-redundancia en región secundaria de Azure (Brazil South)
- Health checks: Endpoint /api/health monitoreado cada 5 minutos con notificación si falla 3 veces consecutivas

### Compatibilidad
- Navegadores soportados: Chrome 90+, Edge 90+, Firefox 88+, Safari 14+
- Power Pages compatible con: Windows 10/11, macOS 11+, iOS 14+, Android 10+
- Resoluciones mínimas soportadas: 1366×768 (desktop), 768×1024 (tablet), 375×667 (smartphone)
- Accesibilidad: Cumplimiento WCAG 2.1 nivel AA (contraste de color 4.5:1, navegación por teclado, etiquetas ARIA)

### Usabilidad
- Mensajes de error claros y accionables: "El RUC ingresado no es válido. Debe tener 11 dígitos numéricos." en lugar de "Error 400"
- Feedback visual inmediato: spinners de carga, estados de botones (loading, success, error), toasts de confirmación
- Ayuda contextual: tooltips en campos complejos, enlaces a documentación en modales de error
- Idioma: Español (Perú) con formato de moneda S/ (soles peruanos), formato de fecha DD/MM/YYYY

### Mantenibilidad
- Código modular: cada flujo de Power Automate es independiente y reutiliza acciones compartidas cuando es posible
- Versionado de soluciones: cada despliegue a PROD etiquetado con versión semántica (v1.0.0, v1.1.0)
- Logs estructurados: Application Insights con logging level configurable (Debug, Info, Warning, Error, Critical)
- Documentación inline: comentarios en Power Fx formulas, descripciones en cada acción de Power Automate
- Testing automatizado: tests de integración en Postman ejecutados en pipeline CI/CD antes de cada despliegue

### Compliance
- GDPR: No se almacenan datos personales sensibles (salud, origen racial), consentimiento implícito por relación laboral
- Retención de datos: Pedidos y devoluciones retenidos por 7 años (regulación contable Perú), luego archivados en cold storage
- Trazabilidad: AuditLog con retención de 2 años, después exportado a Azure Data Lake para análisis histórico

### Monitoreo y Observabilidad
- Dashboard de métricas en tiempo real: Power Automate Analytics muestra ejecuciones exitosas/fallidas por flujo
- Application Insights: trazas distribuidas para seguir request desde Power Pages → Dataverse → Power Automate → SAP
- Alertas configuradas: email a equipo de TI si tasa de error > 5%, si latencia promedio > 5 segundos, si integración SAP falla 3 veces consecutivas
- Telemetría de uso: eventos enviados desde Power Pages (login, crear pedido, aprobar, calcular comisión) para análisis de comportamiento de usuarios

## Configuración Inicial

### Ambiente DEV
1. Ejecutar `pac admin create-environment --name "BONAPHARM_DEV" --type Sandbox --region southcentralus`
2. Importar solución: `pac solution import --path ./BONAPHARM_Solution.zip --environment https://bonapharm-dev.crm.dynamics.com`
3. Configurar variables de entorno en archivo `.env.DEV`:
   - ENTRA_ID_CLIENT_ID
   - ENTRA_ID_SECRET_KEY
   - DATAVERSE_ENVIRONMENT_URL
   - SAP_API_BASE_URL (apunta a ambiente de pruebas de SAP)
   - SHAREPOINT_SITE_URL
4. Ejecutar script `import-sample-data.ps1` para cargar datos de prueba (10 productos, 5 usuarios, 20 pedidos de ejemplo)
5. Configurar roles de seguridad y asignar usuarios de prueba

### Ambiente QA
1. Crear ambiente: `pac admin create-environment --name "BONAPHARM_QA" --type Sandbox --region southcentralus`
2. Importar solución desde paquete validado en DEV
3. Configurar variables de entorno QA (SAP API apunta a sandbox QA)
4. Ejecutar suite de tests automatizados
5. Validación UAT (User Acceptance Testing) con usuarios clave de cada rol

### Ambiente PROD
1. Crear ambiente: `pac admin create-environment --name "BONAPHARM_PROD" --type Production --region southcentralus`
2. Importar solución aprobada desde QA
3. Configurar variables de entorno PROD (SAP API apunta a producción)
4. Configurar backups automáticos con retención de 30 días
5. Activar Application Insights con alertas configuradas
6. Entrenar usuarios finales y activar acceso
7. Monitorear primeras 48 horas de uso con equipo de soporte disponible

### Integraciones Externas
- **Microsoft Entra ID**: Registrar aplicación en portal de Azure, configurar redirect URIs para Power Pages, habilitar permisos de API Graph (User.Read, Directory.Read.All)
- **SAP API**: Solicitar API Key a equipo de SAP, configurar Custom Connector en Power Automate con autenticación por header, validar endpoints de inventario y sincronización
- **SharePoint Online**: Crear sitio de equipo "BONAPHARM Pedidos y Devoluciones", configurar Document Libraries con carpetas DEV/QA/PROD, asignar permisos a service account de Power Automate
- **Power BI Service**: Publicar reporte desde Power BI Desktop a workspace "BONAPHARM Reports", configurar scheduled refresh cada hora, generar embed token para inserción en Power Pages

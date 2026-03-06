# Mockups BONAPHARM - Automatización de Pedidos y Devoluciones

**Proyecto:** BONAPHARM DEL PERÚ
**Cliente:** BONAPHARM
**Generado por:** BORIC Dev
**Fecha:** Marzo 2025

---

## 📋 Descripción

Este directorio contiene mockups HTML de alta fidelidad para el proyecto de Automatización de Pedidos y Devoluciones de BONAPHARM. Los mockups están diseñados basándose en el blueprint del proyecto y representan las interfaces principales del sistema.

---

## 🎨 Diseño Visual

### Paleta de Colores

| Uso | Color | Hex |
|-----|-------|-----|
| **Primary** | Azul Médico | `#1D4ED8` |
| **Accent** | Azul Cielo | `#0EA5E9` |
| **Success** | Verde | `#059669` |
| **Warning** | Amarillo | `#F59E0B` |
| **Error** | Rojo | `#DC2626` |
| **Neutral** | Slate | `#475569` |

### Tipografía

- **Fuente Principal:** Inter (Google Fonts)
- **Pesos:** 300, 400, 500, 600, 700
- **Tamaños:** Escalados con Tailwind CSS

### Iconos

- **Librería:** Lucide Icons
- **Formato:** SVG
- **Estilo:** Outline, consistente

---

## 📁 Estructura de Archivos

```
mockups/
├── index.html                      # Índice navegable de todos los mockups
├── 01-login.html                   # Pantalla de autenticación
├── 02-dashboard.html               # Dashboard principal con KPIs
├── 03-registro-pedidos.html        # Formulario de creación de pedidos
├── 04-consulta-pedidos.html        # Lista y búsqueda de pedidos
├── 05-aprobacion-pedidos.html      # Aprobación por distribuidores
├── 06-gestion-devoluciones.html    # Registro de devoluciones
├── 07-calculo-comisiones.html      # Cálculo automático de comisiones
└── 08-reportes.html                # Dashboard Power BI embebido
```

---

## 🚀 Cómo Ver los Mockups

### Opción 1: Navegación desde Index

1. Abre `index.html` en tu navegador
2. Navega a través de las cards para ver cada mockup

### Opción 2: Apertura Directa

Abre cualquier archivo HTML directamente en tu navegador:

```bash
# Windows
start 01-login.html

# macOS
open 01-login.html

# Linux
xdg-open 01-login.html
```

---

## 📱 Características de los Mockups

### ✅ Responsive Design
- **Mobile First:** Optimizado para 375px+
- **Tablet:** Breakpoint en 768px
- **Desktop:** Breakpoint en 1024px y 1440px

### ✅ Interactividad
- Hover states en botones y cards
- Focus states visibles para accesibilidad
- Cursor pointer en elementos clicables
- Transiciones suaves (150-300ms)

### ✅ Datos Realistas
- Nombres de empresas farmacéuticas peruanas
- RUCs y códigos de productos SAP
- Fechas en formato DD Mmm YYYY
- Montos en soles peruanos (S/)

### ✅ Estados UI
- Loading states (aunque no funcionales en mockup)
- Empty states (sin datos)
- Error states (mensajes de validación)
- Success states (confirmaciones)

---

## 🔍 Detalle de Pantallas

### 01. Login
**Ruta:** `/login`
**Usuario:** Todos los roles
**Características:**
- Autenticación con email/password
- Integración Microsoft Entra ID (SSO)
- Recuperación de contraseña
- Remember me checkbox

### 02. Dashboard
**Ruta:** `/dashboard`
**Usuario:** Todos los roles
**Características:**
- 4 KPI cards principales
- Gráfico de pedidos por estado
- Top 5 productos vendidos
- Actividad reciente (últimas 4 acciones)

### 03. Registro de Pedidos
**Ruta:** `/pedidos/nuevo`
**Usuario:** Vendedores
**Características:**
- Búsqueda de cliente por RUC
- Selección de productos del catálogo
- Bonificaciones automáticas (precio S/ 0.00)
- Cálculo automático de total + IGV
- Resumen de orden

### 04. Consulta de Pedidos
**Ruta:** `/pedidos`
**Usuario:** Vendedores
**Características:**
- Tabla paginada (5 registros por página)
- Filtros por estado y fecha
- Búsqueda por código o cliente
- Estados: Enviado, Aprobado, Rechazado
- Acciones: Ver, Editar, Descargar

### 05. Aprobación de Pedidos
**Ruta:** `/aprobacion`
**Usuario:** Administradores Comerciales
**Características:**
- Cards expansibles con detalle de pedido
- Información del cliente y vendedor
- Lista de productos con cantidades
- Resumen de bonificaciones
- Botones: Aprobar / Rechazar / Comentar

### 06. Gestión de Devoluciones
**Ruta:** `/devoluciones`
**Usuario:** Administradores Comerciales
**Características:**
- Formulario de registro de devolución
- Búsqueda de pedido asociado
- Selección de productos y cantidades
- Razones predefinidas de devolución
- Cálculo automático de "Valorizado"
- Historial de devoluciones recientes

### 07. Cálculo de Comisiones
**Ruta:** `/comisiones`
**Usuario:** Finanzas
**Características:**
- Selector de periodo (mes/año)
- 3 KPI cards: Ventas totales, Comisiones, Recuperos
- Detalle por distribuidor (Dimexa 10%, Química 13%)
- Tabla de cálculo con monto base, porcentaje y comisión
- Exportación a Excel
- Aprobación de pago

### 08. Reportes Power BI
**Ruta:** `/reportes`
**Usuario:** Gerentes y Finanzas
**Características:**
- Tabs de navegación (Ventas, Vendedor, Distribuidor, Producto, Región)
- Dashboard simulado de Power BI
- Filtros de fecha y distribuidor
- KPIs principales
- Gráfico de evolución mensual
- Donut chart de distribución
- Top productos table
- Galería de otros reportes disponibles

---

## 🛠️ Stack Tecnológico

| Tecnología | Versión | Uso |
|------------|---------|-----|
| **HTML5** | - | Estructura semántica |
| **Tailwind CSS** | 3.x CDN | Estilos utility-first |
| **Lucide Icons** | Latest | Iconografía SVG |
| **Google Fonts** | Inter | Tipografía |

### CDN Links Utilizados

```html
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Lucide Icons -->
<script src="https://unpkg.com/lucide@latest"></script>

<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

---

## 📊 Módulos Funcionales Cubiertos

✅ **Registro de Pedidos** (Módulo 1)
✅ **Aprobación de Pedidos** (Módulo 2)
✅ **Gestión de Devoluciones** (Módulo 3)
✅ **Cálculo de Comisiones** (Módulo 4)

---

## 🎯 Requisitos Funcionales Implementados

### Portal Vendedor
- [x] Registrar pedido con cliente y productos
- [x] Agregar bonificaciones (precio S/ 0)
- [x] Cálculo automático de total
- [x] Consultar estado de pedidos enviados

### Portal Distribuidor/Comercial
- [x] Revisar pedidos pendientes de aprobación
- [x] Aprobar o rechazar pedidos
- [x] Registrar devoluciones con valorización
- [x] Ver detalle de productos y cantidades

### Portal Finanzas
- [x] Calcular comisiones automáticamente por distribuidor
- [x] Diferenciar porcentajes (Dimexa 10%, Química 13%)
- [x] Visualizar recuperos por devoluciones
- [x] Generar reportes ejecutivos

---

## 🔒 Seguridad UI

- Autenticación mediante Azure AD (Entra ID)
- Roles diferenciados por sidebar (Vendedor, Admin, Finanzas)
- HTTPS obligatorio (TLS 1.2+)
- Estados deshabilitados en botones de acciones críticas
- Mensajes de confirmación antes de eliminar

---

## ♿ Accesibilidad

- ✅ Contraste mínimo WCAG AA (4.5:1)
- ✅ Labels asociados a inputs (`for` attribute)
- ✅ Focus rings visibles en todos los elementos interactivos
- ✅ HTML semántico (`<nav>`, `<main>`, `<section>`)
- ✅ Aria-labels en botones de icono
- ✅ Estados hover y focus diferenciados

---

## 📈 Performance

- Sin dependencias de JavaScript pesadas
- Carga de CDNs optimizada (defer/async implícito)
- Imágenes no presentes (solo iconos SVG)
- CSS utility-first (sin CSS custom innecesario)

---

## 🧩 Componentes Reutilizables Identificados

### Navegación
- Sidebar con navegación por módulos
- Topbar con breadcrumb y acciones
- User dropdown (footer del sidebar)

### Tablas
- Tabla paginada con filtros
- Tabla con acciones por fila
- Estados con badges de color

### Formularios
- Input con validación
- Select con opciones
- Textarea expandible
- Cards de resumen

### Cards
- KPI cards con iconos
- Info cards con gradientes
- Action cards con botones

### Estados
- Loading skeleton (placeholder)
- Empty state con CTA
- Error alert con reintento
- Success banner

---

## 📝 Notas de Implementación

### Para Desarrolladores Frontend

1. **Conversión a React/Vue/Svelte:**
   - Extraer componentes reutilizables
   - Implementar state management
   - Conectar APIs de Dataverse
   - Agregar validaciones de formularios

2. **Integración con Power Platform:**
   - Power Pages para hosting
   - Power Automate para workflows
   - Dataverse para persistencia
   - Power BI para reportes (reemplazar mockup)

3. **Autenticación Real:**
   - Implementar Microsoft Entra ID OAuth2.0
   - Configurar roles RBAC en Dataverse
   - Proteger rutas por permisos

### Para Diseñadores

1. **Assets Adicionales:**
   - Logo oficial de BONAPHARM (SVG)
   - Fotografías de productos farmacéuticos
   - Ilustraciones para empty states

2. **Ajustes de Marca:**
   - Validar paleta de colores con branding
   - Ajustar tipografía si usa fuente corporativa
   - Agregar footer con links legales

---

## 🐛 Limitaciones del Mockup

- ❌ No hay JavaScript funcional (no se envían datos)
- ❌ Las navegaciones no redirigen realmente
- ❌ Los filtros y búsquedas no funcionan
- ❌ La paginación es estática
- ❌ Power BI es un mockup visual (no embebido real)
- ❌ Las validaciones de formulario no se ejecutan
- ❌ Los modals/dialogs están en-página (no dinámicos)

---

## 📞 Contacto

**Proyecto:** BONAPHARM Automatización
**Generado por:** BORIC Dev
**Blueprint:** `DemoEnd2End/blueprint.json`

Para consultas sobre implementación, contactar al equipo de desarrollo.

---

## 📜 Licencia

© 2025 BONAPHARM DEL PERÚ. Todos los derechos reservados.
Mockups generados con fines de prototipado y presentación.

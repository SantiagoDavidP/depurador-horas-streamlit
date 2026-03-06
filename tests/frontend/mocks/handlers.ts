import { http, HttpResponse } from 'msw'

// Mock data matching frontend types
const mockUser = {
  id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  email: 'vendedor1@bonapharm.com',
  nombre: 'Juan',
  apellido: 'Perez',
  rol: 'vendedor' as const,
}

const mockAdminUser = {
  id: 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
  email: 'admin@bonapharm.com',
  nombre: 'Maria',
  apellido: 'Lopez',
  rol: 'admin_comercial' as const,
}

const mockPedidos = [
  {
    id: 'ped-001',
    codigo_pedido: 'PED-2026-0001',
    fecha: '2026-03-01T10:00:00Z',
    vendedor_id: mockUser.id,
    vendedor_nombre: 'Juan Perez',
    vendedor_email: 'vendedor1@bonapharm.com',
    cliente_ruc: '20123456789',
    cliente_razon_social: 'FARMACIA CENTRAL SAC',
    representante: 'Carlos Garcia',
    condicion_pago: 'Contado',
    subtotal: 1000.00,
    igv: 180.00,
    total: 1180.00,
    estado: 'Borrador' as const,
    detalles: [
      {
        id: 'det-001',
        pedido_id: 'ped-001',
        producto_id: 'prod-001',
        producto_nombre: 'PARACETAMOL 500MG',
        producto_codigo_sap: 'SAP001',
        cantidad: 50,
        precio_unitario: 10.50,
        bonificacion: 0,
        subtotal: 525.00,
        tipo: 'Venta' as const,
      },
    ],
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
  {
    id: 'ped-002',
    codigo_pedido: 'PED-2026-0002',
    fecha: '2026-03-02T11:00:00Z',
    vendedor_id: mockUser.id,
    vendedor_nombre: 'Juan Perez',
    vendedor_email: 'vendedor1@bonapharm.com',
    cliente_ruc: '20987654321',
    cliente_razon_social: 'BOTICA SALUD EIRL',
    representante: 'Ana Torres',
    condicion_pago: 'Credito 30 dias',
    subtotal: 2500.00,
    igv: 450.00,
    total: 2950.00,
    estado: 'Aprobado' as const,
    detalles: [],
    created_at: '2026-03-02T11:00:00Z',
    updated_at: '2026-03-02T14:00:00Z',
  },
]

const mockProductos = [
  {
    id: 'prod-001',
    codigo_sap: 'SAP001',
    nombre: 'PARACETAMOL 500MG',
    molecula: 'Paracetamol',
    distribuidor: 'Dimexa',
    precio_vvf: 10.50,
    precio_compra: 8.00,
    inafecto_devolucion: false,
    stock_disponible: 500,
    activo: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'prod-002',
    codigo_sap: 'SAP002',
    nombre: 'IBUPROFENO 400MG',
    molecula: 'Ibuprofeno',
    distribuidor: 'Quimica Suiza',
    precio_vvf: 15.00,
    precio_compra: 11.00,
    inafecto_devolucion: false,
    stock_disponible: 300,
    activo: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
]

const mockDevoluciones = [
  {
    id: 'dev-001',
    codigo_devolucion: 'DEV-2026-0001',
    pedido_id: 'ped-002',
    numero_factura: 'F001-00012345',
    producto_id: 'prod-001',
    cantidad: 10,
    lote: 'LOTE001',
    razon: 'Producto daniado',
    estado: 'En Proceso',
    valorizado: 105.00,
    observaciones: null,
    solicitante_id: mockUser.id,
    aprobador_id: null,
    fecha_aprobacion: null,
    motivo_rechazo: null,
    producto_nombre: 'PARACETAMOL 500MG',
    producto_codigo_sap: 'SAP001',
    created_at: '2026-03-05T09:00:00Z',
    updated_at: '2026-03-05T09:00:00Z',
  },
]

const mockComisiones = [
  {
    id: 'com-001',
    distribuidor: 'Dimexa',
    mes: 3,
    anio: 2026,
    ventas_totales: 2000.00,
    porcentaje: 10.0,
    comision_bruta: 200.00,
    recuperos: 0.0,
    neto_a_pagar: 200.00,
    estado: 'Calculada',
    calculado_por_id: mockUser.id,
    aprobado_por_id: null,
    fecha_calculo: '2026-03-05T00:00:00Z',
    fecha_aprobacion: null,
    observaciones: null,
    created_at: '2026-03-05T00:00:00Z',
    updated_at: '2026-03-05T00:00:00Z',
  },
]

// Base URL for API (matches axios baseURL)
const API_BASE = 'http://localhost:8000'

export const handlers = [
  // ==================== Health & Root ====================
  http.get(`${API_BASE}/health`, () => {
    return HttpResponse.json({
      status: 'ok',
      service: 'bonapharm-api',
      version: '0.1.0',
      timestamp: new Date().toISOString(),
    })
  }),

  http.get(`${API_BASE}/`, () => {
    return HttpResponse.json({
      message: 'BONAPHARM - API de Pedidos y Devoluciones',
      version: '0.1.0',
      docs: '/docs',
      health: '/health',
    })
  }),

  // ==================== Auth ====================
  http.post(`${API_BASE}/api/auth/login`, async ({ request }) => {
    const body = await request.json() as { email: string; password: string }

    if (body.email === 'vendedor1@bonapharm.com' && body.password === 'password123') {
      return HttpResponse.json({
        access_token: 'mock-jwt-token-123',
        refresh_token: 'mock-refresh-token-123',
        token_type: 'bearer',
        expires_in: 1800,
        user: mockUser,
      })
    }

    if (body.email === 'admin@bonapharm.com' && body.password === 'admin123') {
      return HttpResponse.json({
        access_token: 'mock-jwt-token-admin',
        refresh_token: 'mock-refresh-token-admin',
        token_type: 'bearer',
        expires_in: 1800,
        user: mockAdminUser,
      })
    }

    return HttpResponse.json(
      { detail: 'Credenciales invalidas' },
      { status: 401 }
    )
  }),

  http.post(`${API_BASE}/api/auth/logout`, () => {
    return HttpResponse.json({ message: 'Sesion cerrada exitosamente' })
  }),

  http.post(`${API_BASE}/api/auth/refresh-token`, () => {
    return HttpResponse.json({
      access_token: 'mock-jwt-token-456',
      refresh_token: 'mock-refresh-token-456',
      token_type: 'bearer',
      expires_in: 1800,
    })
  }),

  http.get(`${API_BASE}/api/auth/me`, () => {
    return HttpResponse.json({
      id: mockUser.id,
      nombre_completo: `${mockUser.nombre} ${mockUser.apellido}`,
      email: mockUser.email,
      rol: 'Vendedor',
      activo: true,
    })
  }),

  // ==================== Pedidos (frontend uses /api/pedidos) ====================
  http.get(`${API_BASE}/api/pedidos`, ({ request }) => {
    const url = new URL(request.url)
    const estado = url.searchParams.get('estado')
    const search = url.searchParams.get('search')

    let filteredPedidos = [...mockPedidos]

    if (estado) {
      filteredPedidos = filteredPedidos.filter(p => p.estado === estado)
    }

    if (search) {
      filteredPedidos = filteredPedidos.filter(p =>
        p.codigo_pedido.toLowerCase().includes(search.toLowerCase()) ||
        p.cliente_razon_social.toLowerCase().includes(search.toLowerCase())
      )
    }

    return HttpResponse.json({
      items: filteredPedidos,
      total: filteredPedidos.length,
      page: 1,
      page_size: 50,
      total_pages: 1,
    })
  }),

  http.get(`${API_BASE}/api/pedidos/pendientes`, () => {
    const pendientes = mockPedidos.filter(p => p.estado === 'Enviado')
    return HttpResponse.json({
      items: pendientes,
      total: pendientes.length,
      page: 1,
      page_size: 50,
      total_pages: 1,
    })
  }),

  http.get(`${API_BASE}/api/pedidos/dashboard`, () => {
    return HttpResponse.json({
      estadisticas: {
        total_pedidos: 50,
        pedidos_aprobados: 30,
        pedidos_pendientes: 10,
        pedidos_rechazados: 5,
        total_ventas: 150000.00,
        porcentaje_aprobados: 60,
        porcentaje_pendientes: 20,
        porcentaje_rechazados: 10,
        variacion_mes_anterior: 15,
      },
      top_productos: [
        { codigo_sap: 'SAP001', nombre: 'PARACETAMOL 500MG', unidades_vendidas: 500 },
      ],
      actividad_reciente: [],
      comisiones_acumuladas: 5000.00,
      devoluciones_mes: 3,
      variacion_devoluciones: -5,
    })
  }),

  http.get(`${API_BASE}/api/pedidos/:id`, ({ params }) => {
    const pedido = mockPedidos.find(p => p.id === params.id)

    if (!pedido) {
      return HttpResponse.json(
        { detail: 'Pedido no encontrado' },
        { status: 404 }
      )
    }

    return HttpResponse.json(pedido)
  }),

  http.post(`${API_BASE}/api/pedidos`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>

    const newPedido = {
      id: `ped-${Date.now()}`,
      codigo_pedido: `PED-2026-${String(mockPedidos.length + 1).padStart(4, '0')}`,
      fecha: new Date().toISOString(),
      vendedor_id: mockUser.id,
      vendedor_nombre: `${mockUser.nombre} ${mockUser.apellido}`,
      vendedor_email: mockUser.email,
      cliente_ruc: body.cliente_ruc as string,
      cliente_razon_social: (body.cliente_razon_social || '') as string,
      representante: (body.representante || '') as string,
      condicion_pago: (body.condicion_pago || 'Contado') as string,
      subtotal: 525.00,
      igv: 94.50,
      total: 619.50,
      estado: 'Borrador' as const,
      detalles: body.detalles || [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(newPedido, { status: 201 })
  }),

  http.post(`${API_BASE}/api/pedidos/borrador`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>

    const draft = {
      id: `ped-draft-${Date.now()}`,
      codigo_pedido: `PED-2026-${String(mockPedidos.length + 1).padStart(4, '0')}`,
      fecha: new Date().toISOString(),
      vendedor_id: mockUser.id,
      vendedor_nombre: `${mockUser.nombre} ${mockUser.apellido}`,
      vendedor_email: mockUser.email,
      cliente_ruc: body.cliente_ruc as string,
      cliente_razon_social: (body.cliente_razon_social || '') as string,
      representante: (body.representante || '') as string,
      condicion_pago: (body.condicion_pago || 'Contado') as string,
      subtotal: 0,
      igv: 0,
      total: 0,
      estado: 'Borrador' as const,
      detalles: body.detalles || [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(draft, { status: 201 })
  }),

  http.put(`${API_BASE}/api/pedidos/:id`, async ({ params, request }) => {
    const pedido = mockPedidos.find(p => p.id === params.id)

    if (!pedido) {
      return HttpResponse.json(
        { detail: 'Pedido no encontrado' },
        { status: 404 }
      )
    }

    const body = await request.json() as Record<string, unknown>
    const updated = { ...pedido, ...body, updated_at: new Date().toISOString() }

    return HttpResponse.json(updated)
  }),

  http.post(`${API_BASE}/api/pedidos/:id/aprobar`, ({ params }) => {
    const pedido = mockPedidos.find(p => p.id === params.id)

    if (!pedido) {
      return HttpResponse.json(
        { detail: 'Pedido no encontrado' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      ...pedido,
      estado: 'Aprobado',
      updated_at: new Date().toISOString(),
    })
  }),

  http.post(`${API_BASE}/api/pedidos/:id/rechazar`, async ({ params, request }) => {
    const pedido = mockPedidos.find(p => p.id === params.id)

    if (!pedido) {
      return HttpResponse.json(
        { detail: 'Pedido no encontrado' },
        { status: 404 }
      )
    }

    const body = await request.json() as { motivo_rechazo?: string }
    return HttpResponse.json({
      ...pedido,
      estado: 'Rechazado',
      motivo_rechazo: body.motivo_rechazo,
      updated_at: new Date().toISOString(),
    })
  }),

  // ==================== Productos (frontend uses /api/productos) ====================
  http.get(`${API_BASE}/api/productos`, ({ request }) => {
    const url = new URL(request.url)
    const search = url.searchParams.get('search')
    const distribuidor = url.searchParams.get('distribuidor')

    let filteredProductos = [...mockProductos]

    if (search) {
      filteredProductos = filteredProductos.filter(p =>
        p.nombre.toLowerCase().includes(search.toLowerCase()) ||
        p.codigo_sap.toLowerCase().includes(search.toLowerCase())
      )
    }

    if (distribuidor) {
      filteredProductos = filteredProductos.filter(p => p.distribuidor === distribuidor)
    }

    return HttpResponse.json({
      items: filteredProductos,
      total: filteredProductos.length,
      page: 1,
      page_size: 50,
      total_pages: 1,
    })
  }),

  http.get(`${API_BASE}/api/productos/search`, ({ request }) => {
    const url = new URL(request.url)
    const q = url.searchParams.get('q') || ''

    const results = mockProductos.filter(p =>
      p.nombre.toLowerCase().includes(q.toLowerCase()) ||
      p.codigo_sap.toLowerCase().includes(q.toLowerCase())
    )

    return HttpResponse.json(results)
  }),

  http.get(`${API_BASE}/api/productos/devolvibles/:pedidoId`, () => {
    return HttpResponse.json(mockProductos)
  }),

  http.get(`${API_BASE}/api/productos/:id`, ({ params }) => {
    const producto = mockProductos.find(p => p.id === params.id)

    if (!producto) {
      return HttpResponse.json(
        { detail: 'Producto no encontrado' },
        { status: 404 }
      )
    }

    return HttpResponse.json(producto)
  }),

  // ==================== Devoluciones (frontend uses /api/devoluciones) ====================
  http.get(`${API_BASE}/api/devoluciones`, ({ request }) => {
    const url = new URL(request.url)
    const estado = url.searchParams.get('estado')

    let filteredDevoluciones = [...mockDevoluciones]

    if (estado) {
      filteredDevoluciones = filteredDevoluciones.filter(d => d.estado === estado)
    }

    return HttpResponse.json({
      items: filteredDevoluciones,
      total: filteredDevoluciones.length,
      page: 1,
      page_size: 50,
      total_pages: 1,
    })
  }),

  http.get(`${API_BASE}/api/devoluciones/:id`, ({ params }) => {
    const devolucion = mockDevoluciones.find(d => d.id === params.id)

    if (!devolucion) {
      return HttpResponse.json(
        { detail: 'Devolucion no encontrada' },
        { status: 404 }
      )
    }

    return HttpResponse.json(devolucion)
  }),

  http.post(`${API_BASE}/api/devoluciones`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>

    const newDevolucion = {
      id: `dev-${Date.now()}`,
      codigo_devolucion: `DEV-2026-${String(mockDevoluciones.length + 1).padStart(4, '0')}`,
      pedido_id: body.pedido_id,
      numero_factura: body.numero_factura || 'F001-00099999',
      producto_id: body.producto_id,
      cantidad: body.cantidad || 1,
      lote: body.lote || '',
      razon: body.razon || body.motivo || 'Producto daniado',
      estado: 'En Proceso',
      valorizado: 105.00,
      observaciones: body.observaciones || null,
      solicitante_id: mockUser.id,
      aprobador_id: null,
      fecha_aprobacion: null,
      motivo_rechazo: null,
      producto_nombre: 'PARACETAMOL 500MG',
      producto_codigo_sap: 'SAP001',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    return HttpResponse.json(newDevolucion, { status: 201 })
  }),

  http.post(`${API_BASE}/api/devoluciones/:id/aprobar`, ({ params }) => {
    const devolucion = mockDevoluciones.find(d => d.id === params.id)

    if (!devolucion) {
      return HttpResponse.json(
        { detail: 'Devolucion no encontrada' },
        { status: 404 }
      )
    }

    return HttpResponse.json({
      ...devolucion,
      estado: 'Aprobada',
      aprobador_id: mockAdminUser.id,
      fecha_aprobacion: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }),

  http.post(`${API_BASE}/api/devoluciones/:id/rechazar`, async ({ params, request }) => {
    const devolucion = mockDevoluciones.find(d => d.id === params.id)

    if (!devolucion) {
      return HttpResponse.json(
        { detail: 'Devolucion no encontrada' },
        { status: 404 }
      )
    }

    const body = await request.json() as { motivo?: string }
    return HttpResponse.json({
      ...devolucion,
      estado: 'Rechazada',
      motivo_rechazo: body.motivo || 'Motivo no especificado',
      aprobador_id: mockAdminUser.id,
      fecha_aprobacion: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }),

  // ==================== Comisiones (frontend uses /api/comisiones) ====================
  http.get(`${API_BASE}/api/comisiones/resumen`, ({ request }) => {
    const url = new URL(request.url)
    const mes = url.searchParams.get('mes')
    const anio = url.searchParams.get('anio')

    return HttpResponse.json({
      mes: Number(mes) || 3,
      anio: Number(anio) || 2026,
      ventas_totales: 50000.00,
      comisiones_totales: 5000.00,
      recuperos_totales: 200.00,
      neto_total: 4800.00,
      distribuidores: [
        {
          distribuidor: 'Dimexa',
          ventas_totales: 30000.00,
          porcentaje: 10.0,
          comision_bruta: 3000.00,
          recuperos: 100.00,
          neto_a_pagar: 2900.00,
        },
        {
          distribuidor: 'Quimica Suiza',
          ventas_totales: 20000.00,
          porcentaje: 13.0,
          comision_bruta: 2600.00,
          recuperos: 100.00,
          neto_a_pagar: 2500.00,
        },
      ],
    })
  }),

  http.post(`${API_BASE}/api/comisiones/calcular`, async ({ request }) => {
    const body = await request.json() as { mes?: number; anio?: number; distribuidor?: string }

    return HttpResponse.json({
      mes: body.mes || 3,
      anio: body.anio || 2026,
      ventas_totales: 50000.00,
      comisiones_totales: 5000.00,
      recuperos_totales: 200.00,
      neto_total: 4800.00,
      distribuidores: [
        {
          distribuidor: 'Dimexa',
          ventas_totales: 30000.00,
          porcentaje: 10.0,
          comision_bruta: 3000.00,
          recuperos: 100.00,
          neto_a_pagar: 2900.00,
        },
      ],
    })
  }),

  http.post(`${API_BASE}/api/comisiones/:id/aprobar`, () => {
    return HttpResponse.json({ success: true, message: 'Comision aprobada' })
  }),

  // ==================== Dashboard ====================
  http.get(`${API_BASE}/api/dashboard/vendedor/:vendedorId`, ({ params }) => {
    return HttpResponse.json({
      vendedor_id: params.vendedorId,
      periodo: '2026-03',
      pedidos_pendientes: 3,
      pedidos_aprobados: 5,
      pedidos_rechazados: 1,
      total_ventas: 15000.00,
      comision_estimada: 1500.00,
      devoluciones_pendientes: 1,
    })
  }),

  http.get(`${API_BASE}/api/dashboard/gerencia`, () => {
    return HttpResponse.json({
      periodo: '2026-03',
      total_ventas: 150000.00,
      total_pedidos: 50,
      pedidos_por_aprobar: 10,
      total_devoluciones: 5000.00,
      top_vendedores: [
        { vendedor_id: mockUser.id, nombre: 'Juan Perez', ventas: 50000.00, comision: 5000.00 },
      ],
    })
  }),

  // ==================== Users ====================
  http.get(`${API_BASE}/api/users`, () => {
    return HttpResponse.json({
      items: [{
        id: mockUser.id,
        nombre_completo: `${mockUser.nombre} ${mockUser.apellido}`,
        email: mockUser.email,
        rol: 'Vendedor',
        activo: true,
        entra_id: null,
        ultimo_acceso: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }],
      total: 1,
      skip: 0,
      limit: 20,
    })
  }),

  http.get(`${API_BASE}/api/users/:id`, ({ params }) => {
    if (params.id === mockUser.id) {
      return HttpResponse.json({
        id: mockUser.id,
        nombre_completo: `${mockUser.nombre} ${mockUser.apellido}`,
        email: mockUser.email,
        rol: 'Vendedor',
        activo: true,
        entra_id: null,
        ultimo_acceso: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      })
    }

    return HttpResponse.json(
      { detail: 'Usuario no encontrado' },
      { status: 404 }
    )
  }),

  // ==================== Clientes ====================
  http.get(`${API_BASE}/api/clients/search`, ({ request }) => {
    const url = new URL(request.url)
    const ruc = url.searchParams.get('ruc')

    if (ruc === '20123456789') {
      return HttpResponse.json({
        ruc: '20123456789',
        razon_social: 'FARMACIA CENTRAL SAC',
        direccion: 'Av. Principal 123',
      })
    }

    return HttpResponse.json(
      { detail: 'Cliente no encontrado' },
      { status: 404 }
    )
  }),

  // ==================== Notificaciones ====================
  http.get(`${API_BASE}/api/notifications`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'not-001',
          user_id: mockUser.id,
          tipo: 'pedido_aprobado',
          titulo: 'Pedido Aprobado',
          mensaje: 'Tu pedido PED-2026-0001 ha sido aprobado',
          leido: false,
          created_at: '2026-03-05T10:00:00Z',
        },
      ],
      total: 1,
      skip: 0,
      limit: 20,
    })
  }),

  http.put(`${API_BASE}/api/notifications/:id/read`, ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      leido: true,
    })
  }),
]

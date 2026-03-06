import { describe, it, expect, beforeEach } from 'vitest'
import { usePedidoStore } from '@/store/pedidoStore'

describe('pedidoStore', () => {
  beforeEach(() => {
    const store = usePedidoStore.getState()
    store.reset()
  })

  it('has_initial_empty_state', () => {
    const state = usePedidoStore.getState()

    expect(state.currentPedido).toBeNull()
    expect(state.pedidos).toEqual([])
    expect(state.filters).toEqual({})
  })

  it('sets_current_pedido', () => {
    const store = usePedidoStore.getState()

    const mockPedido = {
      id: 1,
      codigo_pedido: 'PED-2026-0001',
      vendedor_id: 1,
      cliente_ruc: '20123456789',
      cliente_nombre: 'FARMACIA CENTRAL SAC',
      fecha_emision: '2026-03-01',
      tipo_pedido: 'contado' as const,
      subtotal: 1000,
      igv: 180,
      total: 1180,
      estado: 'pendiente' as const,
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
    }

    store.setCurrentPedido(mockPedido)

    expect(usePedidoStore.getState().currentPedido).toEqual(mockPedido)
  })

  it('clears_current_pedido', () => {
    const store = usePedidoStore.getState()

    const mockPedido = {
      id: 1,
      codigo_pedido: 'PED-2026-0001',
      vendedor_id: 1,
      cliente_ruc: '20123456789',
      cliente_nombre: 'FARMACIA CENTRAL SAC',
      fecha_emision: '2026-03-01',
      tipo_pedido: 'contado' as const,
      subtotal: 1000,
      igv: 180,
      total: 1180,
      estado: 'pendiente' as const,
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
    }

    store.setCurrentPedido(mockPedido)
    expect(usePedidoStore.getState().currentPedido).toBeTruthy()

    store.clearCurrentPedido()
    expect(usePedidoStore.getState().currentPedido).toBeNull()
  })

  it('sets_pedidos_list', () => {
    const store = usePedidoStore.getState()

    const mockPedidos = [
      {
        id: 1,
        codigo_pedido: 'PED-2026-0001',
        vendedor_id: 1,
        cliente_ruc: '20123456789',
        cliente_nombre: 'FARMACIA CENTRAL SAC',
        fecha_emision: '2026-03-01',
        tipo_pedido: 'contado' as const,
        subtotal: 1000,
        igv: 180,
        total: 1180,
        estado: 'pendiente' as const,
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-01T10:00:00Z',
      },
      {
        id: 2,
        codigo_pedido: 'PED-2026-0002',
        vendedor_id: 1,
        cliente_ruc: '20987654321',
        cliente_nombre: 'BOTICA SALUD EIRL',
        fecha_emision: '2026-03-02',
        tipo_pedido: 'credito' as const,
        subtotal: 2500,
        igv: 450,
        total: 2950,
        estado: 'aprobado' as const,
        created_at: '2026-03-02T11:00:00Z',
        updated_at: '2026-03-02T14:00:00Z',
      },
    ]

    store.setPedidos(mockPedidos)

    expect(usePedidoStore.getState().pedidos).toHaveLength(2)
    expect(usePedidoStore.getState().pedidos).toEqual(mockPedidos)
  })

  it('adds_pedido_to_list', () => {
    const store = usePedidoStore.getState()

    const mockPedido = {
      id: 1,
      codigo_pedido: 'PED-2026-0001',
      vendedor_id: 1,
      cliente_ruc: '20123456789',
      cliente_nombre: 'FARMACIA CENTRAL SAC',
      fecha_emision: '2026-03-01',
      tipo_pedido: 'contado' as const,
      subtotal: 1000,
      igv: 180,
      total: 1180,
      estado: 'pendiente' as const,
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
    }

    store.addPedido(mockPedido)

    expect(usePedidoStore.getState().pedidos).toHaveLength(1)
    expect(usePedidoStore.getState().pedidos[0]).toEqual(mockPedido)
  })

  it('updates_pedido_in_list', () => {
    const store = usePedidoStore.getState()

    const mockPedido = {
      id: 1,
      codigo_pedido: 'PED-2026-0001',
      vendedor_id: 1,
      cliente_ruc: '20123456789',
      cliente_nombre: 'FARMACIA CENTRAL SAC',
      fecha_emision: '2026-03-01',
      tipo_pedido: 'contado' as const,
      subtotal: 1000,
      igv: 180,
      total: 1180,
      estado: 'pendiente' as const,
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
    }

    store.addPedido(mockPedido)

    const updatedPedido = {
      ...mockPedido,
      estado: 'aprobado' as const,
    }

    store.updatePedido(1, updatedPedido)

    const state = usePedidoStore.getState()
    const pedido = state.pedidos.find(p => p.id === 1)

    expect(pedido?.estado).toBe('aprobado')
  })

  it('removes_pedido_from_list', () => {
    const store = usePedidoStore.getState()

    const mockPedidos = [
      {
        id: 1,
        codigo_pedido: 'PED-2026-0001',
        vendedor_id: 1,
        cliente_ruc: '20123456789',
        cliente_nombre: 'FARMACIA CENTRAL SAC',
        fecha_emision: '2026-03-01',
        tipo_pedido: 'contado' as const,
        subtotal: 1000,
        igv: 180,
        total: 1180,
        estado: 'pendiente' as const,
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-01T10:00:00Z',
      },
      {
        id: 2,
        codigo_pedido: 'PED-2026-0002',
        vendedor_id: 1,
        cliente_ruc: '20987654321',
        cliente_nombre: 'BOTICA SALUD EIRL',
        fecha_emision: '2026-03-02',
        tipo_pedido: 'credito' as const,
        subtotal: 2500,
        igv: 450,
        total: 2950,
        estado: 'aprobado' as const,
        created_at: '2026-03-02T11:00:00Z',
        updated_at: '2026-03-02T14:00:00Z',
      },
    ]

    store.setPedidos(mockPedidos)
    expect(usePedidoStore.getState().pedidos).toHaveLength(2)

    store.removePedido(1)

    const state = usePedidoStore.getState()
    expect(state.pedidos).toHaveLength(1)
    expect(state.pedidos.find(p => p.id === 1)).toBeUndefined()
  })

  it('sets_filters', () => {
    const store = usePedidoStore.getState()

    const filters = {
      estado: 'pendiente',
      fecha_desde: '2026-03-01',
      fecha_hasta: '2026-03-31',
    }

    store.setFilters(filters)

    expect(usePedidoStore.getState().filters).toEqual(filters)
  })

  it('clears_filters', () => {
    const store = usePedidoStore.getState()

    store.setFilters({
      estado: 'pendiente',
      fecha_desde: '2026-03-01',
    })

    expect(usePedidoStore.getState().filters).toBeTruthy()

    store.clearFilters()

    expect(usePedidoStore.getState().filters).toEqual({})
  })

  it('gets_filtered_pedidos_by_estado', () => {
    const store = usePedidoStore.getState()

    const mockPedidos = [
      {
        id: 1,
        codigo_pedido: 'PED-2026-0001',
        vendedor_id: 1,
        cliente_ruc: '20123456789',
        cliente_nombre: 'FARMACIA CENTRAL SAC',
        fecha_emision: '2026-03-01',
        tipo_pedido: 'contado' as const,
        subtotal: 1000,
        igv: 180,
        total: 1180,
        estado: 'pendiente' as const,
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-01T10:00:00Z',
      },
      {
        id: 2,
        codigo_pedido: 'PED-2026-0002',
        vendedor_id: 1,
        cliente_ruc: '20987654321',
        cliente_nombre: 'BOTICA SALUD EIRL',
        fecha_emision: '2026-03-02',
        tipo_pedido: 'credito' as const,
        subtotal: 2500,
        igv: 450,
        total: 2950,
        estado: 'aprobado' as const,
        created_at: '2026-03-02T11:00:00Z',
        updated_at: '2026-03-02T14:00:00Z',
      },
    ]

    store.setPedidos(mockPedidos)
    store.setFilters({ estado: 'pendiente' })

    const filtered = store.getFilteredPedidos()

    expect(filtered).toHaveLength(1)
    expect(filtered[0].estado).toBe('pendiente')
  })

  it('calculates_totals_correctly', () => {
    const store = usePedidoStore.getState()

    const mockPedidos = [
      {
        id: 1,
        codigo_pedido: 'PED-2026-0001',
        vendedor_id: 1,
        cliente_ruc: '20123456789',
        cliente_nombre: 'FARMACIA CENTRAL SAC',
        fecha_emision: '2026-03-01',
        tipo_pedido: 'contado' as const,
        subtotal: 1000,
        igv: 180,
        total: 1180,
        estado: 'pendiente' as const,
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-01T10:00:00Z',
      },
      {
        id: 2,
        codigo_pedido: 'PED-2026-0002',
        vendedor_id: 1,
        cliente_ruc: '20987654321',
        cliente_nombre: 'BOTICA SALUD EIRL',
        fecha_emision: '2026-03-02',
        tipo_pedido: 'credito' as const,
        subtotal: 2500,
        igv: 450,
        total: 2950,
        estado: 'aprobado' as const,
        created_at: '2026-03-02T11:00:00Z',
        updated_at: '2026-03-02T14:00:00Z',
      },
    ]

    store.setPedidos(mockPedidos)

    const totals = store.getTotals()

    expect(totals.subtotal).toBe(3500)
    expect(totals.igv).toBe(630)
    expect(totals.total).toBe(4130)
  })

  it('resets_store_to_initial_state', () => {
    const store = usePedidoStore.getState()

    const mockPedido = {
      id: 1,
      codigo_pedido: 'PED-2026-0001',
      vendedor_id: 1,
      cliente_ruc: '20123456789',
      cliente_nombre: 'FARMACIA CENTRAL SAC',
      fecha_emision: '2026-03-01',
      tipo_pedido: 'contado' as const,
      subtotal: 1000,
      igv: 180,
      total: 1180,
      estado: 'pendiente' as const,
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
    }

    store.setCurrentPedido(mockPedido)
    store.setPedidos([mockPedido])
    store.setFilters({ estado: 'pendiente' })

    store.reset()

    const state = usePedidoStore.getState()

    expect(state.currentPedido).toBeNull()
    expect(state.pedidos).toEqual([])
    expect(state.filters).toEqual({})
  })
})

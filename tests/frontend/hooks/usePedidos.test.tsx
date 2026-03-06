import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { usePedidos } from '@/hooks/usePedidos'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'

describe('usePedidos', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'mock-jwt-token-123')
  })

  it('fetches_pedidos_on_mount', async () => {
    const { result } = renderHook(() => usePedidos())

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.pedidos).toHaveLength(2)
    })
  })

  it('returns_pedidos_data', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.pedidos).toBeDefined()
      expect(result.current.pedidos[0]).toHaveProperty('codigo_pedido')
      expect(result.current.pedidos[0]).toHaveProperty('cliente_nombre')
      expect(result.current.pedidos[0]).toHaveProperty('total')
    })
  })

  it('filters_pedidos_by_estado', async () => {
    const { result } = renderHook(() => usePedidos({ estado: 'pendiente' }))

    await waitFor(() => {
      expect(result.current.pedidos).toHaveLength(1)
      expect(result.current.pedidos[0].estado).toBe('pendiente')
    })
  })

  it('filters_pedidos_by_vendedor_id', async () => {
    const { result } = renderHook(() => usePedidos({ vendedor_id: 1 }))

    await waitFor(() => {
      expect(result.current.pedidos).toBeDefined()
      expect(result.current.pedidos.every(p => p.vendedor_id === 1)).toBe(true)
    })
  })

  it('creates_new_pedido', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const newPedido = {
      vendedor_id: 1,
      cliente_ruc: '20111222333',
      cliente_nombre: 'TEST CLIENTE',
      fecha_emision: '2026-03-10',
      tipo_pedido: 'contado' as const,
      subtotal: 1000,
      igv: 180,
      total: 1180,
    }

    await result.current.createPedido(newPedido)

    await waitFor(() => {
      expect(result.current.pedidos).toHaveLength(3)
      expect(result.current.pedidos.some(p => p.cliente_nombre === 'TEST CLIENTE')).toBe(true)
    })
  })

  it('updates_pedido', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.pedidos).toHaveLength(2)
    })

    const updatedData = {
      cliente_nombre: 'UPDATED NAME',
    }

    await result.current.updatePedido(1, updatedData)

    await waitFor(() => {
      const updatedPedido = result.current.pedidos.find(p => p.id === 1)
      expect(updatedPedido?.cliente_nombre).toBe('UPDATED NAME')
    })
  })

  it('approves_pedido', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.pedidos).toBeDefined()
    })

    await result.current.approvePedido(1)

    await waitFor(() => {
      const pedido = result.current.pedidos.find(p => p.id === 1)
      expect(pedido?.estado).toBe('aprobado')
    })
  })

  it('rejects_pedido', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.pedidos).toBeDefined()
    })

    await result.current.rejectPedido(1, 'Stock insuficiente')

    await waitFor(() => {
      const pedido = result.current.pedidos.find(p => p.id === 1)
      expect(pedido?.estado).toBe('rechazado')
    })
  })

  it('gets_pedido_by_id', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const pedido = await result.current.getPedidoById(1)

    expect(pedido).toBeDefined()
    expect(pedido?.id).toBe(1)
    expect(pedido?.codigo_pedido).toBe('PED-2026-0001')
  })

  it('handles_error_when_pedido_not_found', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/pedidos/:id', () => {
        return HttpResponse.json(
          { detail: 'Pedido no encontrado' },
          { status: 404 }
        )
      })
    )

    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    await expect(result.current.getPedidoById(999)).rejects.toThrow()
  })

  it('handles_API_error_gracefully', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/pedidos', () => {
        return HttpResponse.json(
          { detail: 'Server error' },
          { status: 500 }
        )
      })
    )

    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.error).toBeTruthy()
      expect(result.current.pedidos).toHaveLength(0)
    })
  })

  it('refetches_pedidos', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    await result.current.refetch()

    expect(result.current.isLoading).toBe(true)

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('returns_pagination_info', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.pagination).toBeDefined()
      expect(result.current.pagination.total).toBe(2)
      expect(result.current.pagination.page).toBe(1)
    })
  })

  it('paginates_results', async () => {
    const { result, rerender } = renderHook(
      ({ page }) => usePedidos({ page }),
      { initialProps: { page: 1 } }
    )

    await waitFor(() => {
      expect(result.current.pagination.page).toBe(1)
    })

    rerender({ page: 2 })

    await waitFor(() => {
      expect(result.current.pagination.page).toBe(2)
    })
  })

  it('calculates_totals_correctly', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.totals).toBeDefined()
      expect(result.current.totals.subtotal).toBe(3500)
      expect(result.current.totals.igv).toBe(630)
      expect(result.current.totals.total).toBe(4130)
    })
  })

  it('groups_pedidos_by_estado', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.groupedByEstado).toBeDefined()
      expect(result.current.groupedByEstado.pendiente).toHaveLength(1)
      expect(result.current.groupedByEstado.aprobado).toHaveLength(1)
    })
  })

  it('validates_pedido_data_before_creation', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const invalidPedido = {
      vendedor_id: 1,
      cliente_ruc: '', // Invalid: empty RUC
      cliente_nombre: '',
      fecha_emision: '',
      tipo_pedido: 'contado' as const,
      subtotal: 0,
      igv: 0,
      total: 0,
    }

    await expect(result.current.createPedido(invalidPedido)).rejects.toThrow()
  })

  it('includes_detalle_when_fetching_single_pedido', async () => {
    const { result } = renderHook(() => usePedidos())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    const pedido = await result.current.getPedidoById(1)

    expect(pedido?.detalle).toBeDefined()
    expect(pedido?.detalle).toHaveLength(1)
    expect(pedido?.detalle![0]).toHaveProperty('producto_id')
    expect(pedido?.detalle![0]).toHaveProperty('cantidad')
  })
})

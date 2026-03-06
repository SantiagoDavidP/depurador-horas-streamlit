import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { ConsultaPedidosPage } from '@/pages/ConsultaPedidosPage'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'

const renderConsultaPedidos = () => {
  return render(
    <BrowserRouter>
      <ConsultaPedidosPage />
    </BrowserRouter>
  )
}

describe('ConsultaPedidosPage', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'mock-jwt-token-123')
    localStorage.setItem('user', JSON.stringify({ id: 1, role: 'vendedor' }))
  })

  it('renders_page_title', () => {
    renderConsultaPedidos()
    expect(screen.getByText(/consulta.*pedidos/i)).toBeInTheDocument()
  })

  it('displays_loading_state_initially', () => {
    renderConsultaPedidos()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('displays_pedidos_table_after_loading', async () => {
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })
  })

  it('displays_pedidos_data_in_table', async () => {
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText('PED-2026-0001')).toBeInTheDocument()
      expect(screen.getByText('PED-2026-0002')).toBeInTheDocument()
      expect(screen.getByText('FARMACIA CENTRAL SAC')).toBeInTheDocument()
      expect(screen.getByText('BOTICA SALUD EIRL')).toBeInTheDocument()
    })
  })

  it('renders_filter_bar', () => {
    renderConsultaPedidos()

    expect(screen.getByLabelText(/estado/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/fecha desde/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/fecha hasta/i)).toBeInTheDocument()
  })

  it('filters_by_status', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText('PED-2026-0001')).toBeInTheDocument()
    })

    const statusFilter = screen.getByLabelText(/estado/i)
    await user.selectOptions(statusFilter, 'aprobado')

    await waitFor(() => {
      expect(screen.queryByText('PED-2026-0001')).not.toBeInTheDocument()
      expect(screen.getByText('PED-2026-0002')).toBeInTheDocument()
    })
  })

  it('searches_by_codigo_pedido', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText('PED-2026-0001')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/buscar/i)
    await user.type(searchInput, 'PED-2026-0002')

    await waitFor(() => {
      expect(screen.queryByText('PED-2026-0001')).not.toBeInTheDocument()
      expect(screen.getByText('PED-2026-0002')).toBeInTheDocument()
    })
  })

  it('displays_status_badges_correctly', async () => {
    renderConsultaPedidos()

    await waitFor(() => {
      const pendienteBadge = screen.getByText(/pendiente/i)
      expect(pendienteBadge).toHaveClass('bg-yellow-100', 'text-yellow-800')

      const aprobadoBadge = screen.getByText(/aprobado/i)
      expect(aprobadoBadge).toHaveClass('bg-green-100', 'text-green-800')
    })
  })

  it('displays_order_totals', async () => {
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText(/1,180\.00/)).toBeInTheDocument()
      expect(screen.getByText(/2,950\.00/)).toBeInTheDocument()
    })
  })

  it('opens_order_details_modal_on_row_click', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText('PED-2026-0001')).toBeInTheDocument()
    })

    const firstRow = screen.getByText('PED-2026-0001').closest('tr')
    await user.click(firstRow!)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText(/detalles.*pedido/i)).toBeInTheDocument()
    })
  })

  it('displays_order_details_in_modal', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText('PED-2026-0001')).toBeInTheDocument()
    })

    const firstRow = screen.getByText('PED-2026-0001').closest('tr')
    await user.click(firstRow!)

    await waitFor(() => {
      const modal = screen.getByRole('dialog')
      expect(within(modal).getByText('FARMACIA CENTRAL SAC')).toBeInTheDocument()
      expect(within(modal).getByText(/PARACETAMOL/i)).toBeInTheDocument()
    })
  })

  it('closes_modal_when_close_button_clicked', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText('PED-2026-0001')).toBeInTheDocument()
    })

    const firstRow = screen.getByText('PED-2026-0001').closest('tr')
    await user.click(firstRow!)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    const closeButton = screen.getByRole('button', { name: /cerrar/i })
    await user.click(closeButton)

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('displays_pagination_controls', async () => {
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /anterior/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /siguiente/i })).toBeInTheDocument()
    })
  })

  it('navigates_to_next_page', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    const nextButton = screen.getByRole('button', { name: /siguiente/i })
    await user.click(nextButton)

    await waitFor(() => {
      expect(screen.getByText(/página 2/i)).toBeInTheDocument()
    })
  })

  it('displays_empty_state_when_no_pedidos', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/pedidos', () => {
        return HttpResponse.json({
          items: [],
          total: 0,
          page: 1,
          size: 50,
          pages: 0,
        })
      })
    )

    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText(/no se encontraron pedidos/i)).toBeInTheDocument()
    })
  })

  it('shows_export_button', () => {
    renderConsultaPedidos()
    expect(screen.getByRole('button', { name: /exportar/i })).toBeInTheDocument()
  })

  it('exports_pedidos_to_CSV', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    const exportButton = screen.getByRole('button', { name: /exportar/i })
    await user.click(exportButton)

    // Verify download was triggered (mock implementation)
    await waitFor(() => {
      expect(screen.getByText(/descargando/i)).toBeInTheDocument()
    })
  })

  it('displays_refresh_button', () => {
    renderConsultaPedidos()
    expect(screen.getByRole('button', { name: /actualizar/i })).toBeInTheDocument()
  })

  it('refreshes_data_when_refresh_clicked', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })

    const refreshButton = screen.getByRole('button', { name: /actualizar/i })
    await user.click(refreshButton)

    expect(screen.getByRole('status')).toBeInTheDocument()
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

    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText(/error.*cargar.*pedidos/i)).toBeInTheDocument()
    })
  })

  it('sorts_table_by_column', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    const totalHeader = screen.getByText(/total/i)
    await user.click(totalHeader)

    // Should sort by total amount
    const rows = screen.getAllByRole('row')
    const firstDataRow = rows[1]
    expect(within(firstDataRow).getByText(/1,180/)).toBeInTheDocument()
  })

  it('displays_order_count', async () => {
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByText(/2.*pedidos/i)).toBeInTheDocument()
    })
  })

  it('clears_filters', async () => {
    const user = userEvent.setup()
    renderConsultaPedidos()

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    const statusFilter = screen.getByLabelText(/estado/i)
    await user.selectOptions(statusFilter, 'aprobado')

    const clearButton = screen.getByRole('button', { name: /limpiar filtros/i })
    await user.click(clearButton)

    await waitFor(() => {
      expect(statusFilter).toHaveValue('')
    })
  })
})

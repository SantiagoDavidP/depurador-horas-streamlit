import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { DashboardVendedorPage } from '@/pages/DashboardVendedorPage'

const renderDashboard = () => {
  return render(
    <BrowserRouter>
      <DashboardVendedorPage />
    </BrowserRouter>
  )
}

describe('DashboardVendedorPage', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'mock-jwt-token-123')
    localStorage.setItem('user', JSON.stringify({ id: 1, role: 'vendedor' }))
  })

  it('renders_dashboard_title', () => {
    renderDashboard()
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
  })

  it('displays_loading_state_initially', () => {
    renderDashboard()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('displays_KPI_cards_after_loading', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/pedidos pendientes/i)).toBeInTheDocument()
      expect(screen.getByText(/pedidos aprobados/i)).toBeInTheDocument()
      expect(screen.getByText(/total ventas/i)).toBeInTheDocument()
      expect(screen.getByText(/comisión estimada/i)).toBeInTheDocument()
    })
  })

  it('displays_correct_KPI_values', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument() // pedidos_pendientes
      expect(screen.getByText('5')).toBeInTheDocument() // pedidos_aprobados
      expect(screen.getByText(/15,000/)).toBeInTheDocument() // total_ventas
      expect(screen.getByText(/1,500/)).toBeInTheDocument() // comision_estimada
    })
  })

  it('displays_recent_orders_section', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/pedidos recientes/i)).toBeInTheDocument()
    })
  })

  it('displays_quick_action_buttons', () => {
    renderDashboard()

    expect(screen.getByRole('button', { name: /nuevo pedido/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /consultar pedidos/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /registrar devolución/i })).toBeInTheDocument()
  })

  it('navigates_to_new_order_page_on_button_click', async () => {
    const user = userEvent.setup()
    renderDashboard()

    const newOrderButton = screen.getByRole('button', { name: /nuevo pedido/i })
    await user.click(newOrderButton)

    await waitFor(() => {
      expect(window.location.pathname).toBe('/pedidos/nuevo')
    })
  })

  it('displays_pending_returns_notification', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/1.*devolución.*pendiente/i)).toBeInTheDocument()
    })
  })

  it('shows_period_selector', () => {
    renderDashboard()
    expect(screen.getByLabelText(/periodo/i)).toBeInTheDocument()
  })

  it('updates_data_when_period_changes', async () => {
    const user = userEvent.setup()
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByLabelText(/periodo/i)).toBeInTheDocument()
    })

    const periodSelector = screen.getByLabelText(/periodo/i)
    await user.selectOptions(periodSelector, '2026-02')

    // Should trigger new data fetch
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('displays_sales_chart', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByTestId('sales-chart')).toBeInTheDocument()
    })
  })

  it('displays_commission_breakdown_by_line', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/dimexa/i)).toBeInTheDocument()
      expect(screen.getByText(/química/i)).toBeInTheDocument()
    })
  })

  it('shows_welcome_message_with_user_name', async () => {
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      role: 'vendedor',
      full_name: 'Juan Pérez'
    }))

    renderDashboard()

    expect(screen.getByText(/bienvenido.*juan pérez/i)).toBeInTheDocument()
  })

  it('handles_error_state_when_API_fails', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/dashboard/vendedor/:vendedor_id', () => {
        return HttpResponse.json(
          { detail: 'Error loading dashboard' },
          { status: 500 }
        )
      })
    )

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText(/error.*cargar.*datos/i)).toBeInTheDocument()
    })
  })

  it('displays_refresh_button', () => {
    renderDashboard()
    expect(screen.getByRole('button', { name: /actualizar/i })).toBeInTheDocument()
  })

  it('refreshes_data_when_refresh_button_clicked', async () => {
    const user = userEvent.setup()
    renderDashboard()

    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })

    const refreshButton = screen.getByRole('button', { name: /actualizar/i })
    await user.click(refreshButton)

    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

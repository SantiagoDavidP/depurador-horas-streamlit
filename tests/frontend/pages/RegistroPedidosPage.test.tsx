import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { RegistroPedidosPage } from '@/pages/RegistroPedidosPage'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'

const renderRegistroPedidos = () => {
  return render(
    <BrowserRouter>
      <RegistroPedidosPage />
    </BrowserRouter>
  )
}

describe('RegistroPedidosPage', () => {
  beforeEach(() => {
    localStorage.setItem('token', 'mock-jwt-token-123')
    localStorage.setItem('user', JSON.stringify({ id: 1, role: 'vendedor' }))
  })

  it('renders_page_title', () => {
    renderRegistroPedidos()
    expect(screen.getByText(/nuevo pedido/i)).toBeInTheDocument()
  })

  it('renders_client_information_section', () => {
    renderRegistroPedidos()

    expect(screen.getByLabelText(/ruc/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/nombre.*cliente/i)).toBeInTheDocument()
  })

  it('searches_and_fills_client_data_by_RUC', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    const rucInput = screen.getByLabelText(/ruc/i)
    await user.type(rucInput, '20123456789')

    await waitFor(() => {
      expect(screen.getByDisplayValue('FARMACIA CENTRAL SAC')).toBeInTheDocument()
    })
  })

  it('renders_order_type_selector', () => {
    renderRegistroPedidos()

    expect(screen.getByLabelText(/tipo.*pedido/i)).toBeInTheDocument()
    expect(screen.getByText(/contado/i)).toBeInTheDocument()
    expect(screen.getByText(/crédito/i)).toBeInTheDocument()
  })

  it('renders_product_search_section', () => {
    renderRegistroPedidos()

    expect(screen.getByRole('button', { name: /agregar producto/i })).toBeInTheDocument()
  })

  it('opens_product_search_modal', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
      expect(screen.getByText(/buscar producto/i)).toBeInTheDocument()
    })
  })

  it('searches_products_in_modal', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText(/buscar/i)
    await user.type(searchInput, 'PARACETAMOL')

    await waitFor(() => {
      expect(screen.getByText(/PARACETAMOL 500MG/i)).toBeInTheDocument()
    })
  })

  it('adds_product_to_order_details', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    await waitFor(() => {
      expect(screen.getByText(/PARACETAMOL 500MG/i)).toBeInTheDocument()
    })

    const selectButton = screen.getByRole('button', { name: /seleccionar/i })
    await user.click(selectButton)

    await waitFor(() => {
      expect(screen.getByText(/PARACETAMOL 500MG/i)).toBeInTheDocument()
    })
  })

  it('allows_editing_product_quantity', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    // Add product first
    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    await waitFor(() => {
      const selectButton = screen.getByRole('button', { name: /seleccionar/i })
      user.click(selectButton)
    })

    const quantityInput = screen.getByLabelText(/cantidad/i)
    await user.clear(quantityInput)
    await user.type(quantityInput, '50')

    expect(quantityInput).toHaveValue(50)
  })

  it('calculates_subtotal_correctly', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    // Add product with quantity
    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    // Assuming product price is 10.50
    await waitFor(() => {
      expect(screen.getByText(/subtotal.*525\.00/i)).toBeInTheDocument()
    })
  })

  it('calculates_IGV_automatically', async () => {
    renderRegistroPedidos()

    await waitFor(() => {
      // IGV should be 18% of subtotal
      expect(screen.getByText(/igv.*94\.50/i)).toBeInTheDocument()
    })
  })

  it('calculates_total_correctly', async () => {
    renderRegistroPedidos()

    await waitFor(() => {
      expect(screen.getByText(/total.*619\.50/i)).toBeInTheDocument()
    })
  })

  it('removes_product_from_details', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    // Add product first
    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    await waitFor(() => {
      expect(screen.getByText(/PARACETAMOL/i)).toBeInTheDocument()
    })

    const removeButton = screen.getByRole('button', { name: /eliminar/i })
    await user.click(removeButton)

    await waitFor(() => {
      expect(screen.queryByText(/PARACETAMOL/i)).not.toBeInTheDocument()
    })
  })

  it('validates_required_fields_before_submit', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    const submitButton = screen.getByRole('button', { name: /guardar pedido/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/ruc.*requerido/i)).toBeInTheDocument()
      expect(screen.getByText(/agregar.*producto/i)).toBeInTheDocument()
    })
  })

  it('submits_order_successfully', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    // Fill client data
    const rucInput = screen.getByLabelText(/ruc/i)
    await user.type(rucInput, '20123456789')

    // Add product
    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    await waitFor(() => {
      const selectButton = screen.getByRole('button', { name: /seleccionar/i })
      user.click(selectButton)
    })

    // Submit
    const submitButton = screen.getByRole('button', { name: /guardar pedido/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/pedido.*creado.*exitosamente/i)).toBeInTheDocument()
    })
  })

  it('shows_loading_state_during_submission', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    // Fill minimal data
    const rucInput = screen.getByLabelText(/ruc/i)
    await user.type(rucInput, '20123456789')

    const submitButton = screen.getByRole('button', { name: /guardar pedido/i })
    await user.click(submitButton)

    expect(screen.getByRole('button', { name: /guardando/i })).toBeDisabled()
  })

  it('handles_API_error_gracefully', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/pedidos', () => {
        return HttpResponse.json(
          { detail: 'Error creating order' },
          { status: 500 }
        )
      })
    )

    const user = userEvent.setup()
    renderRegistroPedidos()

    const rucInput = screen.getByLabelText(/ruc/i)
    await user.type(rucInput, '20123456789')

    const submitButton = screen.getByRole('button', { name: /guardar pedido/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/error.*crear.*pedido/i)).toBeInTheDocument()
    })
  })

  it('shows_cancel_button', () => {
    renderRegistroPedidos()
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument()
  })

  it('navigates_back_on_cancel', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    const cancelButton = screen.getByRole('button', { name: /cancelar/i })
    await user.click(cancelButton)

    await waitFor(() => {
      expect(window.location.pathname).toBe('/pedidos')
    })
  })

  it('displays_order_summary_section', () => {
    renderRegistroPedidos()

    expect(screen.getByText(/resumen.*pedido/i)).toBeInTheDocument()
  })

  it('validates_stock_availability', async () => {
    const user = userEvent.setup()
    renderRegistroPedidos()

    const addButton = screen.getByRole('button', { name: /agregar producto/i })
    await user.click(addButton)

    const quantityInput = screen.getByLabelText(/cantidad/i)
    await user.type(quantityInput, '9999')

    await waitFor(() => {
      expect(screen.getByText(/stock insuficiente/i)).toBeInTheDocument()
    })
  })
})

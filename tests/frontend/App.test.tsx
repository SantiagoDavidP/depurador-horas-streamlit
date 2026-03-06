import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '@/App'

describe('App', () => {
  it('renders the main heading', () => {
    render(<App />)
    expect(screen.getByText('BONAPHARM')).toBeInTheDocument()
  })

  it('displays the application modules', () => {
    render(<App />)
    expect(screen.getByText('Gestión de Pedidos')).toBeInTheDocument()
    expect(screen.getByText('Gestión de Devoluciones')).toBeInTheDocument()
    expect(screen.getByText('Cálculo de Comisiones')).toBeInTheDocument()
  })
})

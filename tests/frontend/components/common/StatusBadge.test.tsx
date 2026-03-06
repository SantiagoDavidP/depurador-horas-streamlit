import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StatusBadge } from '@/components/common/StatusBadge'

describe('StatusBadge', () => {
  it('renders_pendiente_status', () => {
    render(<StatusBadge status="pendiente" />)
    const badge = screen.getByText(/pendiente/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800')
  })

  it('renders_aprobado_status', () => {
    render(<StatusBadge status="aprobado" />)
    const badge = screen.getByText(/aprobado/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('renders_rechazado_status', () => {
    render(<StatusBadge status="rechazado" />)
    const badge = screen.getByText(/rechazado/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-red-100', 'text-red-800')
  })

  it('renders_enviado_status', () => {
    render(<StatusBadge status="enviado" />)
    const badge = screen.getByText(/enviado/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-blue-100', 'text-blue-800')
  })

  it('renders_en_proceso_status', () => {
    render(<StatusBadge status="en_proceso" />)
    const badge = screen.getByText(/en proceso/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-indigo-100', 'text-indigo-800')
  })

  it('renders_completado_status', () => {
    render(<StatusBadge status="completado" />)
    const badge = screen.getByText(/completado/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-green-100', 'text-green-800')
  })

  it('renders_cancelado_status', () => {
    render(<StatusBadge status="cancelado" />)
    const badge = screen.getByText(/cancelado/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800')
  })

  it('renders_default_status_for_unknown', () => {
    render(<StatusBadge status="unknown" />)
    const badge = screen.getByText(/unknown/i)
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-gray-100', 'text-gray-800')
  })

  it('applies_correct_size_classes', () => {
    const { rerender } = render(<StatusBadge status="pendiente" size="sm" />)
    let badge = screen.getByText(/pendiente/i)
    expect(badge).toHaveClass('text-xs', 'px-2', 'py-0.5')

    rerender(<StatusBadge status="pendiente" size="md" />)
    badge = screen.getByText(/pendiente/i)
    expect(badge).toHaveClass('text-sm', 'px-2.5', 'py-0.5')

    rerender(<StatusBadge status="pendiente" size="lg" />)
    badge = screen.getByText(/pendiente/i)
    expect(badge).toHaveClass('text-base', 'px-3', 'py-1')
  })

  it('renders_with_icon', () => {
    render(<StatusBadge status="aprobado" showIcon />)
    const icon = screen.getByTestId('status-icon')
    expect(icon).toBeInTheDocument()
  })

  it('applies_custom_className', () => {
    render(<StatusBadge status="pendiente" className="custom-badge" />)
    expect(screen.getByText(/pendiente/i)).toHaveClass('custom-badge')
  })

  it('renders_with_custom_label', () => {
    render(<StatusBadge status="pendiente" label="En Espera" />)
    expect(screen.getByText('En Espera')).toBeInTheDocument()
  })

  it('formats_label_correctly', () => {
    render(<StatusBadge status="en_proceso" />)
    expect(screen.getByText(/en proceso/i)).toBeInTheDocument()
  })
})

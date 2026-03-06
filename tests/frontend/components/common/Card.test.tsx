import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Card } from '@/components/common/Card'

describe('Card', () => {
  it('renders_children_content', () => {
    render(<Card>Card Content</Card>)
    expect(screen.getByText('Card Content')).toBeInTheDocument()
  })

  it('renders_with_title', () => {
    render(<Card title="Card Title">Content</Card>)
    expect(screen.getByText('Card Title')).toBeInTheDocument()
  })

  it('renders_with_subtitle', () => {
    render(<Card title="Title" subtitle="Subtitle">Content</Card>)
    expect(screen.getByText('Subtitle')).toBeInTheDocument()
  })

  it('renders_header_actions', () => {
    const actions = <button>Action</button>
    render(<Card title="Title" actions={actions}>Content</Card>)
    expect(screen.getByRole('button', { name: /action/i })).toBeInTheDocument()
  })

  it('renders_without_padding_when_noPadding_is_true', () => {
    const { container } = render(<Card noPadding>Content</Card>)
    const cardContent = container.querySelector('.card-content')
    expect(cardContent).not.toHaveClass('p-6')
  })

  it('applies_hover_effect_when_hoverable_is_true', () => {
    const { container } = render(<Card hoverable>Content</Card>)
    const card = container.firstChild
    expect(card).toHaveClass('hover:shadow-lg')
  })

  it('renders_as_clickable_when_onClick_is_provided', () => {
    const { container } = render(<Card onClick={() => {}}>Content</Card>)
    const card = container.firstChild
    expect(card).toHaveClass('cursor-pointer')
  })

  it('applies_custom_className', () => {
    const { container } = render(<Card className="custom-card">Content</Card>)
    expect(container.firstChild).toHaveClass('custom-card')
  })

  it('renders_footer', () => {
    const footer = <div>Footer Content</div>
    render(<Card footer={footer}>Content</Card>)
    expect(screen.getByText('Footer Content')).toBeInTheDocument()
  })

  it('renders_loading_state', () => {
    render(<Card loading>Content</Card>)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

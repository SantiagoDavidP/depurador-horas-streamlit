import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Modal } from '@/components/common/Modal'

describe('Modal', () => {
  it('does_not_render_when_open_is_false', () => {
    render(
      <Modal open={false} onClose={() => {}}>
        Modal Content
      </Modal>
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('renders_when_open_is_true', () => {
    render(
      <Modal open={true} onClose={() => {}}>
        Modal Content
      </Modal>
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Modal Content')).toBeInTheDocument()
  })

  it('renders_title', () => {
    render(
      <Modal open={true} onClose={() => {}} title="Modal Title">
        Content
      </Modal>
    )
    expect(screen.getByText('Modal Title')).toBeInTheDocument()
  })

  it('calls_onClose_when_close_button_clicked', async () => {
    const handleClose = vi.fn()
    const user = userEvent.setup()

    render(
      <Modal open={true} onClose={handleClose} title="Title">
        Content
      </Modal>
    )

    const closeButton = screen.getByRole('button', { name: /close/i })
    await user.click(closeButton)

    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('calls_onClose_when_backdrop_clicked', async () => {
    const handleClose = vi.fn()
    const user = userEvent.setup()

    render(
      <Modal open={true} onClose={handleClose}>
        Content
      </Modal>
    )

    const backdrop = screen.getByTestId('modal-backdrop')
    await user.click(backdrop)

    expect(handleClose).toHaveBeenCalledTimes(1)
  })

  it('does_not_close_on_backdrop_click_when_disableBackdropClick_is_true', async () => {
    const handleClose = vi.fn()
    const user = userEvent.setup()

    render(
      <Modal open={true} onClose={handleClose} disableBackdropClick>
        Content
      </Modal>
    )

    const backdrop = screen.getByTestId('modal-backdrop')
    await user.click(backdrop)

    expect(handleClose).not.toHaveBeenCalled()
  })

  it('renders_footer_actions', () => {
    const footer = (
      <div>
        <button>Cancel</button>
        <button>Save</button>
      </div>
    )

    render(
      <Modal open={true} onClose={() => {}} footer={footer}>
        Content
      </Modal>
    )

    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
  })

  it('applies_size_classes_correctly', () => {
    const { rerender } = render(
      <Modal open={true} onClose={() => {}} size="sm">
        Content
      </Modal>
    )
    let dialog = screen.getByRole('dialog')
    expect(dialog).toHaveClass('max-w-sm')

    rerender(
      <Modal open={true} onClose={() => {}} size="md">
        Content
      </Modal>
    )
    dialog = screen.getByRole('dialog')
    expect(dialog).toHaveClass('max-w-md')

    rerender(
      <Modal open={true} onClose={() => {}} size="lg">
        Content
      </Modal>
    )
    dialog = screen.getByRole('dialog')
    expect(dialog).toHaveClass('max-w-2xl')

    rerender(
      <Modal open={true} onClose={() => {}} size="xl">
        Content
      </Modal>
    )
    dialog = screen.getByRole('dialog')
    expect(dialog).toHaveClass('max-w-4xl')
  })

  it('prevents_body_scroll_when_open', () => {
    const { rerender } = render(
      <Modal open={true} onClose={() => {}}>
        Content
      </Modal>
    )
    expect(document.body).toHaveStyle({ overflow: 'hidden' })

    rerender(
      <Modal open={false} onClose={() => {}}>
        Content
      </Modal>
    )
    expect(document.body).not.toHaveStyle({ overflow: 'hidden' })
  })

  it('renders_loading_state', () => {
    render(
      <Modal open={true} onClose={() => {}} loading>
        Content
      </Modal>
    )
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

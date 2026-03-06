import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { FormField } from '@/components/common/FormField'

describe('FormField', () => {
  it('renders_text_input', () => {
    render(<FormField type="text" label="Name" name="name" />)

    expect(screen.getByLabelText('Name')).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })

  it('renders_with_placeholder', () => {
    render(
      <FormField
        type="text"
        label="Email"
        name="email"
        placeholder="Enter your email"
      />
    )

    expect(screen.getByPlaceholderText('Enter your email')).toBeInTheDocument()
  })

  it('calls_onChange_when_input_value_changes', async () => {
    const handleChange = vi.fn()
    const user = userEvent.setup()

    render(
      <FormField type="text" label="Name" name="name" onChange={handleChange} />
    )

    const input = screen.getByRole('textbox')
    await user.type(input, 'John')

    expect(handleChange).toHaveBeenCalled()
  })

  it('displays_value_prop', () => {
    render(
      <FormField type="text" label="Name" name="name" value="John Doe" />
    )

    expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
  })

  it('shows_required_asterisk_when_required', () => {
    render(<FormField type="text" label="Name" name="name" required />)

    expect(screen.getByText('*')).toBeInTheDocument()
  })

  it('shows_error_message', () => {
    render(
      <FormField
        type="text"
        label="Email"
        name="email"
        error="Email is required"
      />
    )

    expect(screen.getByText('Email is required')).toBeInTheDocument()
  })

  it('applies_error_styles_when_error_exists', () => {
    render(
      <FormField
        type="text"
        label="Email"
        name="email"
        error="Invalid email"
      />
    )

    const input = screen.getByRole('textbox')
    expect(input).toHaveClass('border-red-500')
  })

  it('renders_textarea_when_type_is_textarea', () => {
    render(
      <FormField type="textarea" label="Description" name="description" />
    )

    expect(screen.getByRole('textbox')).toBeInTheDocument()
    expect(screen.getByRole('textbox').tagName).toBe('TEXTAREA')
  })

  it('renders_select_dropdown', () => {
    const options = [
      { value: 'option1', label: 'Option 1' },
      { value: 'option2', label: 'Option 2' },
    ]

    render(
      <FormField
        type="select"
        label="Choose"
        name="choice"
        options={options}
      />
    )

    expect(screen.getByRole('combobox')).toBeInTheDocument()
    expect(screen.getByText('Option 1')).toBeInTheDocument()
    expect(screen.getByText('Option 2')).toBeInTheDocument()
  })

  it('renders_checkbox_input', () => {
    render(<FormField type="checkbox" label="Accept terms" name="terms" />)

    expect(screen.getByRole('checkbox')).toBeInTheDocument()
  })

  it('renders_radio_input', () => {
    render(<FormField type="radio" label="Yes" name="answer" value="yes" />)

    expect(screen.getByRole('radio')).toBeInTheDocument()
  })

  it('renders_number_input', () => {
    render(<FormField type="number" label="Age" name="age" />)

    const input = screen.getByLabelText('Age')
    expect(input).toHaveAttribute('type', 'number')
  })

  it('renders_date_input', () => {
    render(<FormField type="date" label="Birthdate" name="birthdate" />)

    const input = screen.getByLabelText('Birthdate')
    expect(input).toHaveAttribute('type', 'date')
  })

  it('shows_helper_text', () => {
    render(
      <FormField
        type="text"
        label="Username"
        name="username"
        helperText="Must be at least 3 characters"
      />
    )

    expect(screen.getByText('Must be at least 3 characters')).toBeInTheDocument()
  })

  it('disables_input_when_disabled_prop_is_true', () => {
    render(<FormField type="text" label="Name" name="name" disabled />)

    expect(screen.getByRole('textbox')).toBeDisabled()
  })

  it('applies_custom_className', () => {
    render(
      <FormField
        type="text"
        label="Name"
        name="name"
        className="custom-input"
      />
    )

    expect(screen.getByRole('textbox')).toHaveClass('custom-input')
  })

  it('renders_with_icon_prefix', () => {
    const icon = <span data-testid="icon">@</span>

    render(
      <FormField type="text" label="Email" name="email" prefixIcon={icon} />
    )

    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('renders_with_icon_suffix', () => {
    const icon = <span data-testid="icon">✓</span>

    render(
      <FormField type="text" label="Name" name="name" suffixIcon={icon} />
    )

    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('supports_min_and_max_for_number_input', () => {
    render(
      <FormField type="number" label="Age" name="age" min={18} max={100} />
    )

    const input = screen.getByLabelText('Age')
    expect(input).toHaveAttribute('min', '18')
    expect(input).toHaveAttribute('max', '100')
  })

  it('supports_maxLength_for_text_input', () => {
    render(
      <FormField type="text" label="Name" name="name" maxLength={50} />
    )

    const input = screen.getByRole('textbox')
    expect(input).toHaveAttribute('maxLength', '50')
  })

  it('renders_readonly_input', () => {
    render(
      <FormField type="text" label="ID" name="id" value="12345" readOnly />
    )

    expect(screen.getByDisplayValue('12345')).toHaveAttribute('readOnly')
  })
})

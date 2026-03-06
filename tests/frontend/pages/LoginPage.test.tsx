import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import { LoginPage } from '@/pages/LoginPage'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'

const renderLoginPage = () => {
  return render(
    <BrowserRouter>
      <LoginPage />
    </BrowserRouter>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders_login_form', () => {
    renderLoginPage()

    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument()
  })

  it('shows_validation_errors_when_submitting_empty_form', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/usuario es requerido/i)).toBeInTheDocument()
      expect(screen.getByText(/contraseña es requerida/i)).toBeInTheDocument()
    })
  })

  it('logs_in_successfully_with_valid_credentials', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const usernameInput = screen.getByLabelText(/usuario/i)
    const passwordInput = screen.getByLabelText(/contraseña/i)
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })

    await user.type(usernameInput, 'vendedor1')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    await waitFor(() => {
      expect(localStorage.getItem('token')).toBe('mock-jwt-token-123')
    })
  })

  it('shows_error_message_with_invalid_credentials', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/auth/login', () => {
        return HttpResponse.json(
          { detail: 'Incorrect username or password' },
          { status: 401 }
        )
      })
    )

    const user = userEvent.setup()
    renderLoginPage()

    const usernameInput = screen.getByLabelText(/usuario/i)
    const passwordInput = screen.getByLabelText(/contraseña/i)
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })

    await user.type(usernameInput, 'wronguser')
    await user.type(passwordInput, 'wrongpass')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/incorrect username or password/i)).toBeInTheDocument()
    })
  })

  it('shows_loading_state_during_login', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const usernameInput = screen.getByLabelText(/usuario/i)
    const passwordInput = screen.getByLabelText(/contraseña/i)
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })

    await user.type(usernameInput, 'vendedor1')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    expect(screen.getByRole('button', { name: /iniciando/i })).toBeDisabled()
  })

  it('toggles_password_visibility', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const passwordInput = screen.getByLabelText(/contraseña/i)
    const toggleButton = screen.getByRole('button', { name: /mostrar contraseña/i })

    expect(passwordInput).toHaveAttribute('type', 'password')

    await user.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'text')

    await user.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('displays_company_logo_and_branding', () => {
    renderLoginPage()

    expect(screen.getByText(/bonapharm/i)).toBeInTheDocument()
    expect(screen.getByAltText(/logo/i)).toBeInTheDocument()
  })

  it('handles_network_error_gracefully', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/auth/login', () => {
        return HttpResponse.error()
      })
    )

    const user = userEvent.setup()
    renderLoginPage()

    const usernameInput = screen.getByLabelText(/usuario/i)
    const passwordInput = screen.getByLabelText(/contraseña/i)
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })

    await user.type(usernameInput, 'vendedor1')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/error de conexión/i)).toBeInTheDocument()
    })
  })

  it('redirects_to_dashboard_after_successful_login', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const usernameInput = screen.getByLabelText(/usuario/i)
    const passwordInput = screen.getByLabelText(/contraseña/i)
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })

    await user.type(usernameInput, 'vendedor1')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    await waitFor(() => {
      expect(window.location.pathname).toBe('/dashboard')
    })
  })

  it('remembers_me_functionality', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const rememberCheckbox = screen.getByLabelText(/recordarme/i)
    await user.click(rememberCheckbox)

    expect(rememberCheckbox).toBeChecked()
  })
})

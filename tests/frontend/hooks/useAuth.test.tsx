import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuth } from '@/hooks/useAuth'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns_initial_unauthenticated_state', () => {
    const { result } = renderHook(() => useAuth())

    expect(result.current.user).toBeNull()
    expect(result.current.token).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isLoading).toBe(false)
  })

  it('login_sets_user_and_token', async () => {
    const { result } = renderHook(() => useAuth())

    await result.current.login('vendedor1', 'password123')

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.user).toBeDefined()
      expect(result.current.user?.username).toBe('vendedor1')
      expect(result.current.token).toBe('mock-jwt-token-123')
    })
  })

  it('stores_token_in_localStorage_after_login', async () => {
    const { result } = renderHook(() => useAuth())

    await result.current.login('vendedor1', 'password123')

    await waitFor(() => {
      expect(localStorage.getItem('token')).toBe('mock-jwt-token-123')
    })
  })

  it('login_fails_with_invalid_credentials', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/auth/login', () => {
        return HttpResponse.json(
          { detail: 'Incorrect username or password' },
          { status: 401 }
        )
      })
    )

    const { result } = renderHook(() => useAuth())

    await expect(
      result.current.login('wronguser', 'wrongpass')
    ).rejects.toThrow()

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
  })

  it('logout_clears_user_and_token', async () => {
    const { result } = renderHook(() => useAuth())

    // Login first
    await result.current.login('vendedor1', 'password123')

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
    })

    // Logout
    await result.current.logout()

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.user).toBeNull()
      expect(result.current.token).toBeNull()
    })
  })

  it('logout_removes_token_from_localStorage', async () => {
    const { result } = renderHook(() => useAuth())

    await result.current.login('vendedor1', 'password123')

    await waitFor(() => {
      expect(localStorage.getItem('token')).toBeTruthy()
    })

    await result.current.logout()

    await waitFor(() => {
      expect(localStorage.getItem('token')).toBeNull()
    })
  })

  it('restores_session_from_localStorage_on_mount', () => {
    localStorage.setItem('token', 'existing-token')
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'vendedor1',
      role: 'vendedor',
    }))

    const { result } = renderHook(() => useAuth())

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.token).toBe('existing-token')
    expect(result.current.user?.username).toBe('vendedor1')
  })

  it('refreshes_token_successfully', async () => {
    const { result } = renderHook(() => useAuth())

    localStorage.setItem('token', 'old-token')

    await result.current.refreshToken()

    await waitFor(() => {
      expect(result.current.token).toBe('mock-jwt-token-456')
      expect(localStorage.getItem('token')).toBe('mock-jwt-token-456')
    })
  })

  it('handles_token_refresh_failure', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/auth/refresh', () => {
        return HttpResponse.json(
          { detail: 'Invalid refresh token' },
          { status: 401 }
        )
      })
    )

    const { result } = renderHook(() => useAuth())

    localStorage.setItem('token', 'expired-token')

    await expect(result.current.refreshToken()).rejects.toThrow()

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(false)
    })
  })

  it('sets_loading_state_during_login', async () => {
    const { result } = renderHook(() => useAuth())

    const loginPromise = result.current.login('vendedor1', 'password123')

    expect(result.current.isLoading).toBe(true)

    await loginPromise

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })
  })

  it('checks_user_role_correctly', () => {
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'admin',
      role: 'admin',
    }))

    const { result } = renderHook(() => useAuth())

    expect(result.current.hasRole('admin')).toBe(true)
    expect(result.current.hasRole('vendedor')).toBe(false)
  })

  it('checks_if_user_is_vendedor', () => {
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'vendedor1',
      role: 'vendedor',
    }))

    const { result } = renderHook(() => useAuth())

    expect(result.current.isVendedor).toBe(true)
  })

  it('checks_if_user_is_admin', () => {
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'admin',
      role: 'admin',
    }))

    const { result } = renderHook(() => useAuth())

    expect(result.current.isAdmin).toBe(true)
  })

  it('checks_if_user_is_finanzas', () => {
    localStorage.setItem('user', JSON.stringify({
      id: 1,
      username: 'finanzas',
      role: 'finanzas',
    }))

    const { result } = renderHook(() => useAuth())

    expect(result.current.isFinanzas).toBe(true)
  })

  it('updates_user_profile', async () => {
    const { result } = renderHook(() => useAuth())

    await result.current.login('vendedor1', 'password123')

    await waitFor(() => {
      expect(result.current.user).toBeDefined()
    })

    const updatedUser = {
      ...result.current.user!,
      full_name: 'Juan Updated',
    }

    result.current.updateUser(updatedUser)

    expect(result.current.user?.full_name).toBe('Juan Updated')
  })

  it('handles_network_error_during_login', async () => {
    server.use(
      http.post('http://localhost:8000/api/v1/auth/login', () => {
        return HttpResponse.error()
      })
    )

    const { result } = renderHook(() => useAuth())

    await expect(
      result.current.login('vendedor1', 'password123')
    ).rejects.toThrow()

    expect(result.current.isAuthenticated).toBe(false)
  })
})

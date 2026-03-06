import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '@/store/authStore'

describe('authStore', () => {
  beforeEach(() => {
    const store = useAuthStore.getState()
    store.logout()
    localStorage.clear()
  })

  it('has_initial_state', () => {
    const state = useAuthStore.getState()

    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('sets_user_and_token_on_login', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    const mockToken = 'mock-jwt-token-123'

    store.login(mockUser, mockToken)

    const updatedState = useAuthStore.getState()

    expect(updatedState.user).toEqual(mockUser)
    expect(updatedState.token).toBe(mockToken)
    expect(updatedState.isAuthenticated).toBe(true)
  })

  it('stores_token_in_localStorage_on_login', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    expect(localStorage.getItem('token')).toBe('mock-token')
    expect(localStorage.getItem('user')).toBeTruthy()
  })

  it('clears_user_and_token_on_logout', () => {
    const store = useAuthStore.getState()

    // Login first
    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    expect(useAuthStore.getState().isAuthenticated).toBe(true)

    // Logout
    store.logout()

    const state = useAuthStore.getState()

    expect(state.user).toBeNull()
    expect(state.token).toBeNull()
    expect(state.isAuthenticated).toBe(false)
  })

  it('removes_token_from_localStorage_on_logout', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    expect(localStorage.getItem('token')).toBeTruthy()

    store.logout()

    expect(localStorage.getItem('token')).toBeNull()
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('updates_user_data', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    const updatedUser = {
      ...mockUser,
      full_name: 'Juan Updated',
      email: 'juan.updated@bonapharm.com',
    }

    store.updateUser(updatedUser)

    const state = useAuthStore.getState()

    expect(state.user?.full_name).toBe('Juan Updated')
    expect(state.user?.email).toBe('juan.updated@bonapharm.com')
  })

  it('updates_user_in_localStorage', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    const updatedUser = {
      ...mockUser,
      full_name: 'Juan Updated',
    }

    store.updateUser(updatedUser)

    const storedUser = JSON.parse(localStorage.getItem('user') || '{}')
    expect(storedUser.full_name).toBe('Juan Updated')
  })

  it('updates_token', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'old-token')

    expect(useAuthStore.getState().token).toBe('old-token')

    store.setToken('new-token')

    expect(useAuthStore.getState().token).toBe('new-token')
    expect(localStorage.getItem('token')).toBe('new-token')
  })

  it('checks_if_user_has_role', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'admin',
      email: 'admin@bonapharm.com',
      full_name: 'Admin User',
      role: 'admin',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    expect(store.hasRole('admin')).toBe(true)
    expect(store.hasRole('vendedor')).toBe(false)
  })

  it('returns_false_for_hasRole_when_no_user', () => {
    const store = useAuthStore.getState()

    expect(store.hasRole('admin')).toBe(false)
    expect(store.hasRole('vendedor')).toBe(false)
  })

  it('checks_if_user_is_vendedor', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    expect(store.isVendedor()).toBe(true)
  })

  it('checks_if_user_is_admin', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'admin',
      email: 'admin@bonapharm.com',
      full_name: 'Admin User',
      role: 'admin',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    expect(store.isAdmin()).toBe(true)
  })

  it('checks_if_user_is_finanzas', () => {
    const store = useAuthStore.getState()

    const mockUser = {
      id: 1,
      username: 'finanzas',
      email: 'finanzas@bonapharm.com',
      full_name: 'Finanzas User',
      role: 'finanzas',
      is_active: true,
      created_at: '2026-01-01',
    }

    store.login(mockUser, 'mock-token')

    expect(store.isFinanzas()).toBe(true)
  })

  it('restores_session_from_localStorage', () => {
    const mockUser = {
      id: 1,
      username: 'vendedor1',
      email: 'vendedor1@bonapharm.com',
      full_name: 'Juan Pérez',
      role: 'vendedor',
      is_active: true,
      created_at: '2026-01-01',
    }

    localStorage.setItem('token', 'stored-token')
    localStorage.setItem('user', JSON.stringify(mockUser))

    // Reinitialize store (simulate app restart)
    useAuthStore.getState().restoreSession()

    const state = useAuthStore.getState()

    expect(state.isAuthenticated).toBe(true)
    expect(state.token).toBe('stored-token')
    expect(state.user?.username).toBe('vendedor1')
  })

  it('handles_invalid_data_in_localStorage', () => {
    localStorage.setItem('token', 'some-token')
    localStorage.setItem('user', 'invalid-json')

    useAuthStore.getState().restoreSession()

    const state = useAuthStore.getState()

    expect(state.isAuthenticated).toBe(false)
    expect(state.user).toBeNull()
  })
})

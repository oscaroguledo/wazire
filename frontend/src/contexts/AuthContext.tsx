import React, { useEffect, useState, createContext, useContext } from 'react'
import { User, UserRole } from '@/lib/types'
import * as authApi from '@/apis/auth'

interface AuthContextType {
  user: User | null
  setUser: (user: User | null) => void
  login: (email: string, password: string) => Promise<User>
  register: (name: string, email: string, password: string, role: UserRole) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  authLoading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

/** Normalize a backend user object — adds a computed `name` field */
function normalizeUser(u: Partial<User> & { first_name?: string; middle_name?: string; last_name?: string; name?: string; email?: string }): User {
  const first = u?.first_name ?? ''
  const middle = u?.middle_name ?? ''
  const last = u?.last_name ?? ''
  const name = [first, middle, last].filter(Boolean).join(' ') || u?.name || u?.email || ''
  return { ...u, name } as User
}

const USER_KEY = 'wazire_user'
const TOKEN_KEY = 'access_token'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null)
  const [authLoading, setAuthLoading] = useState(true)

  const setUser = (u: User | null) => {
    const normalized = u ? normalizeUser(u) : null
    setUserState(normalized)
    if (normalized) {
      localStorage.setItem(USER_KEY, JSON.stringify(normalized))
    } else {
      localStorage.removeItem(USER_KEY)
    }
  }

  useEffect(() => {
    const init = async () => {
      try {
        const token = localStorage.getItem(TOKEN_KEY)
        if (token) {
          // Always re-fetch from backend on load so tenant_id is fresh
          const freshUser = await authApi.me()
          setUser(freshUser as any)
          return
        }
        // No token — try stored user as fallback (offline/stale)
        const stored = localStorage.getItem(USER_KEY)
        if (stored) setUserState(JSON.parse(stored))
      } catch {
        // Token invalid or network error — fall back to stored user
        const stored = localStorage.getItem(USER_KEY)
        if (stored) setUserState(JSON.parse(stored))
      } finally {
        setAuthLoading(false)
      }
    }
    init()
  }, [])

  const login = async (email: string, password: string): Promise<User> => {
    const data = await authApi.login({ email, password })
    // login returns AuthResponse: { user, tokens }
    const rawData = data as { user?: User; tokens?: { access_token: string; refresh_token: string } } | User
    const rawUser: User | undefined = 'user' in rawData ? rawData.user : rawData as User
    if (!rawUser) {
      throw new Error('Invalid login response: no user data')
    }
    const normalized = normalizeUser(rawUser)
    setUserState(normalized)
    localStorage.setItem(USER_KEY, JSON.stringify(normalized))
    return normalized
  }

  const register = async (name: string, email: string, password: string, role: UserRole) => {
    const parts = name.trim().split(/\s+/)
    const first_name = parts.shift() ?? ''
    const last_name = parts.join(' ')
    await authApi.register({ first_name, last_name, email, password, role })
    // Auto-login after register
    const data = await authApi.login({ email, password })
    const rawData = data as { user?: User; tokens?: { access_token: string; refresh_token: string } } | User
    const rawUser: User | undefined = 'user' in rawData ? rawData.user : rawData as User
    if (!rawUser) {
      throw new Error('Invalid login response after registration')
    }
    // 13.3: Store access token in localStorage so user is authenticated immediately after registration
    const tokens = (rawData as { tokens?: { access_token: string; refresh_token: string } }).tokens
    if (tokens?.access_token) {
      localStorage.setItem(TOKEN_KEY, tokens.access_token)
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token)
      }
    }
    setUser(rawUser)
  }

  const logout = () => {
    setUserState(null)
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem('refresh_token')
  }

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout, isAuthenticated: !!user, authLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

import { create } from 'zustand'

interface Admin {
  id: string
  email: string
  full_name: string
}

interface AuthState {
  accessToken: string | null
  admin: Admin | null
  setSession: (accessToken: string, admin: Admin) => void
  clearSession: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  admin: null,
  setSession: (accessToken, admin) => set({ accessToken, admin }),
  clearSession: () => set({ accessToken: null, admin: null }),
}))

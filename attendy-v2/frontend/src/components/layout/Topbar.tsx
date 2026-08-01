import { Moon, Sun, LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../../hooks/useTheme'
import { useAuthStore } from '../../store/authStore'
import { api } from '../../lib/api'

export function Topbar() {
  const { theme, toggle } = useTheme()
  const admin = useAuthStore((s) => s.admin)
  const clearSession = useAuthStore((s) => s.clearSession)
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      await api.post('/auth/logout')
    } finally {
      clearSession()
      navigate('/login', { replace: true })
    }
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="text-sm text-gray-500 dark:text-gray-400">
        {admin ? `Signed in as ${admin.fullName}` : ''}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={toggle}
          aria-label="Toggle dark mode"
          className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </header>
  )
}

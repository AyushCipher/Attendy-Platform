import { NavLink } from 'react-router-dom'
import { LayoutDashboard, ClipboardList, Users, Camera, UtensilsCrossed, BookOpen } from 'lucide-react'
import clsx from 'clsx'

const links = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/attendance', label: 'Attendance', icon: ClipboardList },
  { to: '/admin/meals', label: 'Mess', icon: UtensilsCrossed },
  { to: '/admin/library', label: 'Library', icon: BookOpen },
  { to: '/admin/students', label: 'Students', icon: Users },
  { to: '/admin/scan', label: 'Scan', icon: Camera },
]

export function Sidebar() {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-gray-200 bg-white px-3 py-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-6 px-2 text-lg font-semibold text-brand-600 dark:text-brand-400">
        Attendy
      </div>
      <nav className="flex flex-col gap-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800',
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

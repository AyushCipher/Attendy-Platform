import { Link } from 'react-router-dom'
import { ClipboardCheck, UtensilsCrossed, BookOpen } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface ModeCard {
  to: string
  label: string
  description: string
  icon: LucideIcon
}

const MODES: ModeCard[] = [
  {
    to: '/admin/scan/attendance',
    label: 'Attendance',
    description: 'Mark students present by face or QR code.',
    icon: ClipboardCheck,
  },
  {
    to: '/admin/scan/mess',
    label: 'Mess',
    description: 'Mark a meal taken — face recognition only, no QR fallback.',
    icon: UtensilsCrossed,
  },
  {
    to: '/admin/scan/library',
    label: 'Library',
    description: 'Identify a student, then scan a book to borrow or return it.',
    icon: BookOpen,
  },
]

export function ScanModePicker() {
  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold text-gray-900 dark:text-gray-100">Scan</h1>
      <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">Choose what you're scanning for.</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {MODES.map(({ to, label, description, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-5 transition-colors hover:border-brand-400 hover:bg-brand-50 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-brand-600 dark:hover:bg-brand-900/20"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-400">
              <Icon size={20} />
            </div>
            <div>
              <p className="font-semibold text-gray-900 dark:text-gray-100">{label}</p>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string
  icon: LucideIcon
  accent?: 'brand' | 'present' | 'absent'
}

const ACCENT_CLASSES: Record<NonNullable<StatCardProps['accent']>, string> = {
  brand: 'bg-brand-50 text-brand-600 dark:bg-brand-900/40 dark:text-brand-400',
  present: 'bg-green-50 text-present dark:bg-green-950',
  absent: 'bg-red-50 text-absent dark:bg-red-950',
}

export function StatCard({ label, value, icon: Icon, accent = 'brand' }: StatCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${ACCENT_CLASSES[accent]}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-xl font-semibold text-gray-900 dark:text-gray-100">{value}</p>
      </div>
    </div>
  )
}

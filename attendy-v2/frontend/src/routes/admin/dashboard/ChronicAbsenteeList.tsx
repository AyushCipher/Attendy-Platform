import { AlertTriangle } from 'lucide-react'
import type { ChronicAbsenteeRow } from '../../../hooks/useAnalytics'

interface Props {
  items: ChronicAbsenteeRow[]
}

export function ChronicAbsenteeList({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="flex h-full items-center justify-center py-8 text-sm text-gray-400">
        No students crossed the absence threshold in this range.
      </div>
    )
  }

  return (
    <ul className="divide-y divide-gray-100 dark:divide-gray-800">
      {items.map((row) => (
        <li key={row.student_id} className="flex items-center justify-between py-2.5 text-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle size={15} className="shrink-0 text-absent" />
            <div>
              <p className="font-medium text-gray-900 dark:text-gray-100">{row.name}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Roll {row.roll_number} · {row.class_section.label}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-medium text-absent">{Math.round(row.absence_rate * 100)}% absent</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {row.absent_days}/{row.school_days} days
            </p>
          </div>
        </li>
      ))}
    </ul>
  )
}

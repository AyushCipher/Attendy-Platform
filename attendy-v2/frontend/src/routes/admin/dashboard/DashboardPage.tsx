import { useState } from 'react'
import { CalendarDays, TrendingUp, UserCheck, UserX } from 'lucide-react'
import { StatCard } from '../../../components/common/StatCard'
import { useClassSections } from '../../../hooks/useClassSections'
import { useAttendanceSummary, useChronicAbsentees } from '../../../hooks/useAnalytics'
import { AttendanceTrendChart } from './AttendanceTrendChart'
import { ChronicAbsenteeList } from './ChronicAbsenteeList'

function isoDaysAgo(days: number) {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}

export function DashboardPage() {
  const [dateFrom, setDateFrom] = useState(isoDaysAgo(13))
  const [dateTo, setDateTo] = useState(isoDaysAgo(0))
  const [classSectionId, setClassSectionId] = useState('')

  const { data: classSections } = useClassSections()
  const filters = { dateFrom, dateTo, classSectionId: classSectionId || undefined }
  const { data: summary, isLoading: summaryLoading } = useAttendanceSummary(filters)
  const { data: absentees, isLoading: absenteesLoading } = useChronicAbsentees({ ...filters, threshold: 0.2 })

  const totalPresent = summary?.points.reduce((sum, p) => sum + p.present_count, 0) ?? 0
  const totalAbsent = summary?.points.reduce((sum, p) => sum + p.absent_count, 0) ?? 0

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Dashboard</h1>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
          <span className="text-gray-400">to</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
          <select
            value={classSectionId}
            onChange={(e) => setClassSectionId(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800"
          >
            <option value="">All classes</option>
            {classSections?.map((cs) => (
              <option key={cs.id} value={cs.id}>
                {cs.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard
          label="Overall attendance rate"
          value={summary ? `${Math.round(summary.overall_present_rate * 100)}%` : '—'}
          icon={TrendingUp}
          accent="brand"
        />
        <StatCard label="Present (school days)" value={String(totalPresent)} icon={UserCheck} accent="present" />
        <StatCard label="Absent (school days)" value={String(totalAbsent)} icon={UserX} accent="absent" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900 lg:col-span-2">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            <CalendarDays size={16} />
            Attendance rate trend
          </h2>
          {summaryLoading ? (
            <div className="flex h-64 items-center justify-center text-sm text-gray-400">Loading…</div>
          ) : (
            <AttendanceTrendChart points={summary?.points ?? []} />
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            Chronic absentees (&gt;20%)
          </h2>
          {absenteesLoading ? (
            <div className="flex h-40 items-center justify-center text-sm text-gray-400">Loading…</div>
          ) : (
            <ChronicAbsenteeList items={absentees?.items ?? []} />
          )}
        </div>
      </div>
    </div>
  )
}

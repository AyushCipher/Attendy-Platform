import { useState } from 'react'
import { Download, Search, Wifi, WifiOff } from 'lucide-react'
import clsx from 'clsx'
import { useClassSections } from '../../../hooks/useClassSections'
import { useAttendanceSheet } from '../../../hooks/useAttendance'
import { useAttendanceFeed } from '../../../hooks/useAttendanceFeed'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export function AttendancePage() {
  const [date, setDate] = useState(todayIso())
  const [classSectionId, setClassSectionId] = useState('')
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')

  const { data: classSections } = useClassSections()
  const { data, isLoading } = useAttendanceSheet({ date, classSectionId, status, search })
  const { connected } = useAttendanceFeed()

  function exportCsv() {
    if (!data) return
    const header = ['Name', 'Roll', 'Class', 'Status', 'Marked At', 'Source']
    const rows = data.items.map((row) => [
      row.name,
      row.roll_number,
      row.class_section.label,
      row.status,
      row.event_time ?? '',
      row.source ?? '',
    ])
    const csv = [header, ...rows].map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `attendance_${date}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Attendance</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {data ? `${data.present_count} present · ${data.absent_count} absent · ${data.total} total` : '…'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={clsx(
              'flex items-center gap-1.5 text-xs',
              connected ? 'text-present' : 'text-gray-400',
            )}
          >
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connected ? 'Live' : 'Offline'}
          </span>
          <button
            onClick={exportCsv}
            className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            <Download size={16} />
            Export CSV
          </button>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        />

        <select
          value={classSectionId}
          onChange={(e) => setClassSectionId(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <option value="">All classes</option>
          {classSections?.map((cs) => (
            <option key={cs.id} value={cs.id}>
              {cs.label}
            </option>
          ))}
        </select>

        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <option value="">All statuses</option>
          <option value="present">Present</option>
          <option value="absent">Absent</option>
        </select>

        <div className="relative">
          <Search size={16} className="absolute left-2.5 top-2.5 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name or roll…"
            className="rounded-lg border border-gray-300 py-2 pl-8 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2.5">Name</th>
              <th className="px-4 py-2.5">Roll</th>
              <th className="px-4 py-2.5">Class</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Marked at</th>
              <th className="px-4 py-2.5">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                  No students match these filters.
                </td>
              </tr>
            )}
            {data?.items.map((row) => (
              <tr key={row.student_id} className="bg-white dark:bg-gray-900">
                <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-gray-100">{row.name}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{row.roll_number}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{row.class_section.label}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={clsx(
                      'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                      row.status === 'present'
                        ? 'bg-green-100 text-present dark:bg-green-950'
                        : 'bg-red-100 text-absent dark:bg-red-950',
                    )}
                  >
                    {row.status === 'present' ? 'Present' : 'Absent'}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-500 dark:text-gray-400">
                  {row.event_time ? new Date(row.event_time).toLocaleTimeString() : '—'}
                </td>
                <td className="px-4 py-2.5 text-gray-500 dark:text-gray-400">{row.source ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

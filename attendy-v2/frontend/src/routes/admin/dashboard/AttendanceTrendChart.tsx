import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DailySummaryPoint } from '../../../hooks/useAnalytics'

const BRAND = '#4f46e5'

interface Props {
  points: DailySummaryPoint[]
}

function formatDateLabel(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function AttendanceTrendChart({ points }: Props) {
  const data = points.map((p) => ({
    ...p,
    rate: p.total > 0 ? Math.round((p.present_count / p.total) * 1000) / 10 : 0,
    label: formatDateLabel(p.date),
  }))

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-gray-400">
        No school days in this range.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <defs>
          <linearGradient id="attendanceFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={BRAND} stopOpacity={0.25} />
            <stop offset="100%" stopColor={BRAND} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="currentColor" className="text-gray-200 dark:text-gray-800" />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 12, fill: 'currentColor' }}
          className="text-gray-500 dark:text-gray-400"
        />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 12, fill: 'currentColor' }}
          className="text-gray-500 dark:text-gray-400"
          width={40}
        />
        <Tooltip
          formatter={(_value, _name, item) => {
            const point = item.payload as (typeof data)[number]
            return [`${point.present_count} / ${point.total} present (${point.rate}%)`, 'Attendance']
          }}
          labelFormatter={(label) => label}
          contentStyle={{ borderRadius: 8, fontSize: 13 }}
        />
        <Area
          type="monotone"
          dataKey="rate"
          stroke={BRAND}
          strokeWidth={2}
          fill="url(#attendanceFill)"
          dot={false}
          activeDot={{ r: 4 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

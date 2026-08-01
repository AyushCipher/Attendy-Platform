import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ClassSection } from '../types'

export interface DailySummaryPoint {
  date: string
  present_count: number
  absent_count: number
  total: number
}

export interface AttendanceSummaryResponse {
  date_from: string
  date_to: string
  points: DailySummaryPoint[]
  overall_present_rate: number
}

export interface ChronicAbsenteeRow {
  student_id: string
  name: string
  roll_number: number
  class_section: ClassSection
  school_days: number
  absent_days: number
  absence_rate: number
}

export interface ChronicAbsenteesResponse {
  date_from: string
  date_to: string
  threshold: number
  items: ChronicAbsenteeRow[]
}

export interface AnalyticsFilters {
  dateFrom: string
  dateTo: string
  classSectionId?: string
}

export function useAttendanceSummary(filters: AnalyticsFilters) {
  return useQuery({
    queryKey: ['analytics', 'summary', filters],
    queryFn: async () =>
      (
        await api.get<AttendanceSummaryResponse>('/attendance/analytics/summary', {
          params: {
            date_from: filters.dateFrom,
            date_to: filters.dateTo,
            class_section_id: filters.classSectionId || undefined,
          },
        })
      ).data,
  })
}

export function useChronicAbsentees(filters: AnalyticsFilters & { threshold?: number }) {
  return useQuery({
    queryKey: ['analytics', 'chronic-absentees', filters],
    queryFn: async () =>
      (
        await api.get<ChronicAbsenteesResponse>('/attendance/analytics/chronic-absentees', {
          params: {
            date_from: filters.dateFrom,
            date_to: filters.dateTo,
            class_section_id: filters.classSectionId || undefined,
            threshold: filters.threshold ?? 0.2,
          },
        })
      ).data,
  })
}

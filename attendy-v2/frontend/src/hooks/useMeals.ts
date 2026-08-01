import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { AttendanceFilters } from './useAttendance'
import type { MealSheetResponse } from '../types/meal'

export function useMealSheet(filters: AttendanceFilters) {
  return useQuery({
    queryKey: ['meals', filters],
    queryFn: async () => {
      const params = {
        event_date: filters.date,
        class_section_id: filters.classSectionId || undefined,
        status: filters.status || undefined,
        search: filters.search || undefined,
      }
      return (await api.get<MealSheetResponse>('/attendance/meals', { params })).data
    },
    refetchInterval: 15_000,
  })
}

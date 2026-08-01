import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { AttendanceSheetResponse } from '../types/attendance'

export interface AttendanceFilters {
  date: string
  classSectionId?: string
  status?: string
  search?: string
}

export function attendanceQueryKey(filters: AttendanceFilters) {
  return ['attendance', filters] as const
}

export function useAttendanceSheet(filters: AttendanceFilters) {
  return useQuery({
    queryKey: attendanceQueryKey(filters),
    queryFn: async () => {
      const params = {
        event_date: filters.date,
        class_section_id: filters.classSectionId || undefined,
        status: filters.status || undefined,
        search: filters.search || undefined,
      }
      return (await api.get<AttendanceSheetResponse>('/attendance', { params })).data
    },
    refetchInterval: 30_000, // fallback safety net if the WS connection drops
  })
}

export function useMarkManualAttendance() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { student_id: string; event_date: string; status: 'present' | 'absent' }) =>
      (await api.post('/attendance/manual', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attendance'] })
    },
  })
}

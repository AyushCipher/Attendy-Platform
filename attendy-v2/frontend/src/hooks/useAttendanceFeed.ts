import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import type { AttendanceFilters } from './useAttendance'
import type { AttendanceConfirmedEvent, AttendanceSheetResponse } from '../types/attendance'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export function useAttendanceFeed() {
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!accessToken) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/attendance-feed?token=${accessToken}`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)

    ws.onmessage = (event) => {
      let data: AttendanceConfirmedEvent
      try {
        data = JSON.parse(event.data)
      } catch {
        return
      }
      if (data.type !== 'attendance_confirmed') return

      const matches = queryClient.getQueriesData<AttendanceSheetResponse>({ queryKey: ['attendance'] })

      for (const [queryKey, old] of matches) {
        if (!old) continue
        const filters = queryKey[1] as AttendanceFilters
        if (filters.date !== todayIso()) continue
        if (filters.classSectionId && filters.classSectionId !== data.class_section.id) continue

        const alreadyPresent = old.items.some((item) => item.student_id === data.student_id)
        if (alreadyPresent) continue

        const newRow = {
          student_id: data.student_id,
          name: data.name,
          roll_number: data.roll_number,
          class_section: data.class_section,
          status: 'present' as const,
          event_time: data.event_time,
          confidence: data.confidence,
          source: data.source,
        }

        if (filters.status === 'absent') {
          // this row no longer belongs in an "absent only" view
          queryClient.setQueryData<AttendanceSheetResponse>(queryKey, {
            ...old,
            present_count: old.present_count + 1,
            absent_count: old.absent_count - 1,
            items: old.items.filter((item) => item.student_id !== data.student_id),
          })
          continue
        }

        queryClient.setQueryData<AttendanceSheetResponse>(queryKey, {
          ...old,
          present_count: old.present_count + 1,
          absent_count: old.absent_count - 1,
          items: [...old.items, newRow].sort((a, b) => a.name.localeCompare(b.name)),
        })
      }
    }

    return () => {
      ws.close()
    }
  }, [accessToken, queryClient])

  return { connected }
}

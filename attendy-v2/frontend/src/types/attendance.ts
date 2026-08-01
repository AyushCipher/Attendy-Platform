import type { ClassSection } from './index'

export interface AttendanceRow {
  student_id: string
  name: string
  roll_number: number
  class_section: ClassSection
  status: 'present' | 'absent'
  event_time: string | null
  confidence: number | null
  source: string | null
}

export interface AttendanceSheetResponse {
  date: string
  items: AttendanceRow[]
  total: number
  present_count: number
  absent_count: number
}

export interface AttendanceConfirmedEvent {
  type: 'attendance_confirmed'
  student_id: string
  name: string
  roll_number: number
  class_section: ClassSection
  event_time: string
  confidence: number
  source: string
}

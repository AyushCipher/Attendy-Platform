import type { ClassSection } from './index'

export interface MealRow {
  student_id: string
  name: string
  roll_number: number
  class_section: ClassSection
  status: 'present' | 'absent'
  event_time: string | null
  source: string | null
}

export interface MealSheetResponse {
  date: string
  items: MealRow[]
  total: number
  present_count: number
  absent_count: number
}

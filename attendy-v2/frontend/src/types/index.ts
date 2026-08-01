export interface ClassSection {
  id: string
  grade: number
  section: string
  label: string
}

export interface Student {
  id: string
  name: string
  roll_number: number
  status: 'active' | 'inactive'
  photo_url: string | null
  class_section: ClassSection
  face_enrolled: boolean
  created_at: string
}

export interface StudentListResponse {
  items: Student[]
  total: number
  page: number
  page_size: number
}

export interface FaceEnrollResult {
  images_received: number
  images_usable: number
  average_quality: number | null
  rejected_reasons: string[]
  total_embeddings_stored: number
}

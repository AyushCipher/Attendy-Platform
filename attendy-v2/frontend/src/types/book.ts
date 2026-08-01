export interface Book {
  id: string
  name: string
  author: string
  serial_number: string
  status: 'active' | 'retired'
  currently_borrowed: boolean
  created_at: string
}

export interface BookListResponse {
  items: Book[]
  total: number
}

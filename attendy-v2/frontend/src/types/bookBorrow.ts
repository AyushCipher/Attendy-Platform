export interface BookBorrow {
  id: string
  book_id: string
  book_name: string
  student_id: string
  student_name: string
  borrowed_at: string
  returned_at: string | null
  fine_amount: number
  fine_settled: boolean
  is_overdue: boolean
}

export interface BookBorrowListResponse {
  items: BookBorrow[]
  total: number
}

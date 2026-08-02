import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Book, BookListResponse } from '../types/book'
import type { BookBorrowListResponse } from '../types/bookBorrow'

export interface BookFilters {
  search?: string
  status?: string
}

export function useBooks(filters: BookFilters) {
  return useQuery({
    queryKey: ['books', filters],
    queryFn: async () =>
      (
        await api.get<BookListResponse>('/books', {
          params: { search: filters.search || undefined, status: filters.status || undefined },
        })
      ).data,
  })
}

export function useCreateBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { name: string; author: string; serial_number: string }) =>
      (await api.post<Book>('/books', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })
}

export function useDeleteBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (bookId: string) => {
      await api.delete(`/books/${bookId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })
}

export function useReactivateBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (bookId: string) => (await api.post<Book>(`/books/${bookId}/reactivate`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })
}

export function useBorrowedBooks() {
  return useQuery({
    queryKey: ['book-borrows'],
    queryFn: async () =>
      (await api.get<BookBorrowListResponse>('/books/borrows', { params: { only_open: true } })).data,
    refetchInterval: 15_000,
  })
}

export function useSettleFine() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (borrowId: string) => (await api.post(`/books/borrows/${borrowId}/settle-fine`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book-borrows'] })
    },
  })
}

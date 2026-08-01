import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { FaceEnrollResult, Student, StudentListResponse } from '../types'

export interface StudentFilters {
  classSectionId?: string
  status?: string
  search?: string
  page?: number
}

export function useStudents(filters: StudentFilters) {
  return useQuery({
    queryKey: ['students', filters],
    queryFn: async () => {
      const params = {
        class_section_id: filters.classSectionId || undefined,
        status: filters.status || undefined,
        search: filters.search || undefined,
        page: filters.page ?? 1,
        page_size: 25,
      }
      return (await api.get<StudentListResponse>('/students', { params })).data
    },
  })
}

export function useCreateStudent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { name: string; roll_number: number; class_section_id: string }) =>
      (await api.post<Student>('/students', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}

export function useDeleteStudent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (studentId: string) => {
      await api.delete(`/students/${studentId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}

export function useEnrollFace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ studentId, photos }: { studentId: string; photos: Blob[] }) => {
      const form = new FormData()
      photos.forEach((blob, i) => form.append('photos', blob, `capture_${i}.jpg`))
      return (
        await api.post<FaceEnrollResult>(`/students/${studentId}/enroll-face`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      ).data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['students'] })
    },
  })
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ClassSection } from '../types'

export function useClassSections() {
  return useQuery({
    queryKey: ['class-sections'],
    queryFn: async () => (await api.get<ClassSection[]>('/class-sections')).data,
  })
}

export function useCreateClassSection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { grade: number; section: string }) =>
      (await api.post<ClassSection>('/class-sections', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['class-sections'] })
    },
  })
}

import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ClassSection } from '../types'

export function useClassSections() {
  return useQuery({
    queryKey: ['class-sections'],
    queryFn: async () => (await api.get<ClassSection[]>('/class-sections')).data,
  })
}

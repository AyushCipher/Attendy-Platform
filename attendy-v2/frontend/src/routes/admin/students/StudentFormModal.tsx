import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../../../components/common/Modal'
import { useCreateStudent } from '../../../hooks/useStudents'
import type { Student } from '../../../types'

const GRADES = Array.from({ length: 12 }, (_, i) => i + 1)
const SECTIONS = ['A', 'B', 'C', 'D', 'E', 'F'] as const

const schema = z.object({
  name: z.string().min(1, 'Required'),
  roll_number: z.string().min(1, 'Required').regex(/^\d+$/, 'Must be a number'),
  grade: z.string().min(1, 'Required'),
  section: z.string().min(1, 'Required'),
})

type FormValues = z.infer<typeof schema>

interface StudentFormModalProps {
  onClose: () => void
  onCreated: (student: Student) => void
}

export function StudentFormModal({ onClose, onCreated }: StudentFormModalProps) {
  const createStudent = useCreateStudent()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    setServerError(null)
    try {
      const student = await createStudent.mutateAsync({
        name: values.name,
        roll_number: Number(values.roll_number),
        grade: Number(values.grade),
        section: values.section,
      })
      onCreated(student)
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Could not create student'
      setServerError(message)
    }
  }

  return (
    <Modal title="Add student" onClose={onClose}>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
        <div>
          <label htmlFor="name" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Name
          </label>
          <input
            id="name"
            {...register('name')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>

        <div>
          <label
            htmlFor="roll_number"
            className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Roll number
          </label>
          <input
            id="roll_number"
            type="number"
            {...register('roll_number')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
          {errors.roll_number && <p className="mt-1 text-xs text-red-600">{errors.roll_number.message}</p>}
        </div>

        <div className="flex gap-3">
          <div className="flex-1">
            <label htmlFor="grade" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Class
            </label>
            <select
              id="grade"
              {...register('grade')}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
            >
              <option value="">Select…</option>
              {GRADES.map((g) => (
                <option key={g} value={g}>
                  Class {g}
                </option>
              ))}
            </select>
            {errors.grade && <p className="mt-1 text-xs text-red-600">{errors.grade.message}</p>}
          </div>

          <div className="flex-1">
            <label
              htmlFor="section"
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Section
            </label>
            <select
              id="section"
              {...register('section')}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
            >
              <option value="">Select…</option>
              {SECTIONS.map((s) => (
                <option key={s} value={s}>
                  Section {s}
                </option>
              ))}
            </select>
            {errors.section && <p className="mt-1 text-xs text-red-600">{errors.section.message}</p>}
          </div>
        </div>

        {serverError && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {serverError}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {isSubmitting ? 'Creating…' : 'Create student'}
        </button>
      </form>
    </Modal>
  )
}

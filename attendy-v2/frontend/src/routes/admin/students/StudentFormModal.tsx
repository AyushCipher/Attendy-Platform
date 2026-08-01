import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../../../components/common/Modal'
import { useClassSections, useCreateClassSection } from '../../../hooks/useClassSections'
import { useCreateStudent } from '../../../hooks/useStudents'
import type { Student } from '../../../types'

const schema = z.object({
  name: z.string().min(1, 'Required'),
  roll_number: z.string().min(1, 'Required').regex(/^\d+$/, 'Must be a number'),
  class_section_id: z.string().min(1, 'Required'),
})

type FormValues = z.infer<typeof schema>

interface StudentFormModalProps {
  onClose: () => void
  onCreated: (student: Student) => void
}

export function StudentFormModal({ onClose, onCreated }: StudentFormModalProps) {
  const { data: classSections } = useClassSections()
  const createStudent = useCreateStudent()
  const createClassSection = useCreateClassSection()
  const [serverError, setServerError] = useState<string | null>(null)
  const [showNewClassSection, setShowNewClassSection] = useState(false)
  const [newGrade, setNewGrade] = useState('')
  const [newSection, setNewSection] = useState('')

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function handleCreateClassSection() {
    if (!newGrade || !newSection) return
    const cs = await createClassSection.mutateAsync({ grade: Number(newGrade), section: newSection })
    setValue('class_section_id', cs.id)
    setShowNewClassSection(false)
    setNewGrade('')
    setNewSection('')
  }

  async function onSubmit(values: FormValues) {
    setServerError(null)
    try {
      const student = await createStudent.mutateAsync({
        ...values,
        roll_number: Number(values.roll_number),
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
          <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
          <input
            {...register('name')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Roll number</label>
          <input
            type="number"
            {...register('roll_number')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
          {errors.roll_number && <p className="mt-1 text-xs text-red-600">{errors.roll_number.message}</p>}
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Class / Section
          </label>
          <select
            {...register('class_section_id')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          >
            <option value="">Select…</option>
            {classSections?.map((cs) => (
              <option key={cs.id} value={cs.id}>
                {cs.label}
              </option>
            ))}
          </select>
          {errors.class_section_id && (
            <p className="mt-1 text-xs text-red-600">{errors.class_section_id.message}</p>
          )}

          {!showNewClassSection ? (
            <button
              type="button"
              onClick={() => setShowNewClassSection(true)}
              className="mt-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
            >
              + New class/section
            </button>
          ) : (
            <div className="mt-2 flex items-end gap-2">
              <div>
                <label className="mb-1 block text-xs text-gray-500 dark:text-gray-400">Grade</label>
                <input
                  type="number"
                  value={newGrade}
                  onChange={(e) => setNewGrade(e.target.value)}
                  className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500 dark:text-gray-400">Section</label>
                <input
                  value={newSection}
                  onChange={(e) => setNewSection(e.target.value.toUpperCase())}
                  maxLength={4}
                  className="w-20 rounded-lg border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-700 dark:bg-gray-800"
                />
              </div>
              <button
                type="button"
                onClick={handleCreateClassSection}
                disabled={createClassSection.isPending}
                className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900"
              >
                Add
              </button>
            </div>
          )}
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

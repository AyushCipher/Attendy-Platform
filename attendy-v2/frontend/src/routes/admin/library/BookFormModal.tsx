import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Modal } from '../../../components/common/Modal'
import { useCreateBook } from '../../../hooks/useBooks'
import type { Book } from '../../../types/book'

const schema = z.object({
  name: z.string().min(1, 'Required'),
  author: z.string().min(1, 'Required'),
  serial_number: z.string().min(1, 'Required'),
})

type FormValues = z.infer<typeof schema>

interface BookFormModalProps {
  onClose: () => void
  onCreated: (book: Book) => void
}

export function BookFormModal({ onClose, onCreated }: BookFormModalProps) {
  const createBook = useCreateBook()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  async function onSubmit(values: FormValues) {
    setServerError(null)
    try {
      const book = await createBook.mutateAsync(values)
      onCreated(book)
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Could not create book'
      setServerError(message)
    }
  }

  return (
    <Modal title="Register book" onClose={onClose}>
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3">
        <div>
          <label htmlFor="name" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Book name
          </label>
          <input
            id="name"
            {...register('name')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>

        <div>
          <label htmlFor="author" className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Author
          </label>
          <input
            id="author"
            {...register('author')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
          {errors.author && <p className="mt-1 text-xs text-red-600">{errors.author.message}</p>}
        </div>

        <div>
          <label
            htmlFor="serial_number"
            className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Serial number
          </label>
          <input
            id="serial_number"
            {...register('serial_number')}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
          {errors.serial_number && (
            <p className="mt-1 text-xs text-red-600">{errors.serial_number.message}</p>
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
          {isSubmitting ? 'Registering…' : 'Register book'}
        </button>
      </form>
    </Modal>
  )
}

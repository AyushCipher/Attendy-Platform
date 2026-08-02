import { useState } from 'react'
import { AlertTriangle, Plus, QrCode, RotateCcw, Search, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import { useBooks, useBorrowedBooks, useDeleteBook, useReactivateBook, useSettleFine } from '../../../hooks/useBooks'
import type { Book } from '../../../types/book'
import { BookFormModal } from './BookFormModal'
import { BookQrModal } from './BookQrModal'

export function LibraryPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('active')
  const [showForm, setShowForm] = useState(false)
  const [qrTarget, setQrTarget] = useState<Book | null>(null)

  const { data, isLoading } = useBooks({ search: search || undefined, status: statusFilter || undefined })
  const deleteBook = useDeleteBook()
  const reactivateBook = useReactivateBook()
  const { data: borrowsData } = useBorrowedBooks()
  const settleFine = useSettleFine()

  const books = data?.items ?? []
  const borrows = borrowsData?.items ?? []

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Library</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {data?.total ?? 0} book{data?.total === 1 ? '' : 's'}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          <Plus size={16} />
          Register book
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search size={16} className="absolute left-2.5 top-2.5 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search title, author, serial…"
            className="rounded-lg border border-gray-300 py-2 pl-8 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <option value="active">Active</option>
          <option value="retired">Retired</option>
          <option value="">All</option>
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2.5">Title</th>
              <th className="px-4 py-2.5">Author</th>
              <th className="px-4 py-2.5">Serial</th>
              <th className="px-4 py-2.5">Availability</th>
              <th className="px-4 py-2.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {isLoading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  Loading…
                </td>
              </tr>
            )}
            {!isLoading && books.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  No books match these filters.
                </td>
              </tr>
            )}
            {books.map((book) => (
              <tr key={book.id} className="bg-white dark:bg-gray-900">
                <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-gray-100">{book.name}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{book.author}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{book.serial_number}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={clsx(
                      'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                      book.currently_borrowed
                        ? 'bg-red-100 text-absent dark:bg-red-950'
                        : 'bg-green-100 text-present dark:bg-green-950',
                    )}
                  >
                    {book.currently_borrowed ? 'Borrowed' : 'Available'}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => setQrTarget(book)}
                      title="View / download QR code"
                      className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-brand-600 dark:hover:bg-gray-800"
                    >
                      <QrCode size={16} />
                    </button>
                    {book.status === 'retired' ? (
                      <button
                        onClick={() => reactivateBook.mutate(book.id)}
                        disabled={reactivateBook.isPending}
                        title="Reactivate"
                        className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-brand-600 dark:hover:bg-gray-800"
                      >
                        <RotateCcw size={16} />
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          if (confirm(`Retire ${book.name}?`)) deleteBook.mutate(book.id)
                        }}
                        title="Retire"
                        className="rounded-lg p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Currently borrowed
        </h2>
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500 dark:bg-gray-900 dark:text-gray-400">
              <tr>
                <th className="px-4 py-2.5">Book</th>
                <th className="px-4 py-2.5">Student</th>
                <th className="px-4 py-2.5">Borrowed at</th>
                <th className="px-4 py-2.5">Fine</th>
                <th className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {borrows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                    Nothing currently borrowed.
                  </td>
                </tr>
              )}
              {borrows.map((borrow) => (
                <tr key={borrow.id} className="bg-white dark:bg-gray-900">
                  <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-gray-100">
                    {borrow.book_name}
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{borrow.student_name}</td>
                  <td className="px-4 py-2.5 text-gray-500 dark:text-gray-400">
                    {new Date(borrow.borrowed_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2.5">
                    {borrow.fine_amount > 0 ? (
                      <span
                        className={clsx(
                          'flex items-center gap-1 font-medium',
                          borrow.fine_settled ? 'text-gray-400 line-through' : 'text-absent',
                        )}
                      >
                        <AlertTriangle size={14} />
                        ₹{borrow.fine_amount}
                        {borrow.fine_settled && ' (settled)'}
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {borrow.fine_amount > 0 && !borrow.fine_settled && (
                      <button
                        onClick={() => settleFine.mutate(borrow.id)}
                        disabled={settleFine.isPending}
                        className="rounded-lg border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
                      >
                        Settle fine
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showForm && (
        <BookFormModal
          onClose={() => setShowForm(false)}
          onCreated={(book) => {
            setShowForm(false)
            setQrTarget(book)
          }}
        />
      )}

      {qrTarget && <BookQrModal book={qrTarget} onClose={() => setQrTarget(null)} />}
    </div>
  )
}

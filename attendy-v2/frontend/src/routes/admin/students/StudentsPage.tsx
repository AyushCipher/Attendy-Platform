import { useState } from 'react'
import { Plus, ScanFace, Search, Trash2 } from 'lucide-react'
import clsx from 'clsx'
import { useClassSections } from '../../../hooks/useClassSections'
import { useDeleteStudent, useStudents } from '../../../hooks/useStudents'
import type { Student } from '../../../types'
import { StudentFormModal } from './StudentFormModal'
import { FaceEnrollWizard } from './FaceEnrollWizard'

export function StudentsPage() {
  const [classSectionId, setClassSectionId] = useState('')
  const [statusFilter, setStatusFilter] = useState('active')
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [enrollTarget, setEnrollTarget] = useState<Student | null>(null)

  const { data: classSections } = useClassSections()
  const { data, isLoading } = useStudents({
    classSectionId: classSectionId || undefined,
    status: statusFilter || undefined,
    search: search || undefined,
  })
  const deleteStudent = useDeleteStudent()

  const students = data?.items ?? []

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Students</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {data?.total ?? 0} student{data?.total === 1 ? '' : 's'}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          <Plus size={16} />
          Add student
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search size={16} className="absolute left-2.5 top-2.5 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name or roll…"
            className="rounded-lg border border-gray-300 py-2 pl-8 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-800"
          />
        </div>

        <select
          value={classSectionId}
          onChange={(e) => setClassSectionId(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <option value="">All classes</option>
          {classSections?.map((cs) => (
            <option key={cs.id} value={cs.id}>
              {cs.label}
            </option>
          ))}
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="">All</option>
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            <tr>
              <th className="px-4 py-2.5">Name</th>
              <th className="px-4 py-2.5">Roll</th>
              <th className="px-4 py-2.5">Class</th>
              <th className="px-4 py-2.5">Face enrolled</th>
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
            {!isLoading && students.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-400">
                  No students match these filters.
                </td>
              </tr>
            )}
            {students.map((student) => (
              <tr key={student.id} className="bg-white dark:bg-gray-900">
                <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-gray-100">{student.name}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{student.roll_number}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{student.class_section.label}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={clsx(
                      'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                      student.face_enrolled
                        ? 'bg-green-100 text-present dark:bg-green-950'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-800',
                    )}
                  >
                    {student.face_enrolled ? 'Enrolled' : 'Not enrolled'}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      onClick={() => setEnrollTarget(student)}
                      title="Enroll / re-enroll face"
                      className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-brand-600 dark:hover:bg-gray-800"
                    >
                      <ScanFace size={16} />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Deactivate ${student.name}?`)) deleteStudent.mutate(student.id)
                      }}
                      title="Deactivate"
                      className="rounded-lg p-1.5 text-gray-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <StudentFormModal
          onClose={() => setShowForm(false)}
          onCreated={(student) => {
            setShowForm(false)
            setEnrollTarget(student)
          }}
        />
      )}

      {enrollTarget && (
        <FaceEnrollWizard student={enrollTarget} onClose={() => setEnrollTarget(null)} />
      )}
    </div>
  )
}

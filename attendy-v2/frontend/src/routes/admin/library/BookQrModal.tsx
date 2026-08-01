import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import { Modal } from '../../../components/common/Modal'
import { api } from '../../../lib/api'
import type { Book } from '../../../types/book'

interface BookQrModalProps {
  book: Book
  onClose: () => void
}

export function BookQrModal({ book, onClose }: BookQrModalProps) {
  const [qrUrl, setQrUrl] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    async function loadQr() {
      const response = await api.get(`/books/${book.id}/qr-code`, { responseType: 'blob' })
      if (cancelled) return
      objectUrl = URL.createObjectURL(response.data)
      setQrUrl(objectUrl)
    }

    loadQr()
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [book.id])

  return (
    <Modal title={`Book QR — ${book.name}`} onClose={onClose}>
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-56 w-56 items-center justify-center rounded-lg border border-gray-200 bg-white dark:border-gray-700">
          {qrUrl ? (
            <img src={qrUrl} alt={`QR code for ${book.name}`} className="h-full w-full object-contain" />
          ) : (
            <span className="text-sm text-gray-400">Loading…</span>
          )}
        </div>

        <div>
          <p className="font-semibold text-gray-900 dark:text-gray-100">{book.name}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {book.author} · Serial {book.serial_number}
          </p>
        </div>

        {qrUrl && (
          <a
            href={qrUrl}
            download={`${book.name.replace(/\s+/g, '_')}_qr.png`}
            className="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            <Download size={16} />
            Download QR
          </a>
        )}
      </div>
    </Modal>
  )
}

import { useEffect, useState } from 'react'
import { User } from 'lucide-react'
import { api } from '../../../lib/api'

interface StudentPhotoThumbnailProps {
  studentId: string
  hasPhoto: boolean
  name: string
}

export function StudentPhotoThumbnail({ studentId, hasPhoto, name }: StudentPhotoThumbnailProps) {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!hasPhoto) return
    let objectUrl: string | null = null
    let cancelled = false

    api
      .get(`/students/${studentId}/photo`, { responseType: 'blob' })
      .then((response) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(response.data)
        setUrl(objectUrl)
      })
      .catch(() => {
        // No photo on file yet (e.g. race with a just-started enrollment) -- fall
        // back to the placeholder icon below, nothing else to do.
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [studentId, hasPhoto])

  if (url) {
    return <img src={url} alt={name} className="h-8 w-8 rounded-full object-cover" />
  }

  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-400 dark:bg-gray-800">
      <User size={16} />
    </div>
  )
}

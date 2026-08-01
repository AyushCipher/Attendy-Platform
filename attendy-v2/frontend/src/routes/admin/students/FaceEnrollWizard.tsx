import { useEffect, useRef, useState } from 'react'
import { Camera, CheckCircle2, XCircle } from 'lucide-react'
import { Modal } from '../../../components/common/Modal'
import { useEnrollFace } from '../../../hooks/useStudents'
import type { FaceEnrollResult, Student } from '../../../types'

const POSES = [
  { label: 'Look straight at the camera', shots: 3 },
  { label: 'Turn slightly to your left', shots: 2 },
  { label: 'Turn slightly to your right', shots: 2 },
  { label: 'Tilt your chin down a little', shots: 2 },
]
const CAPTURE_INTERVAL_MS = 500

interface FaceEnrollWizardProps {
  student: Student
  onClose: () => void
}

type Phase = 'starting' | 'capturing' | 'uploading' | 'done' | 'error'

export function FaceEnrollWizard({ student, onClose }: FaceEnrollWizardProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const capturedBlobs = useRef<Blob[]>([])

  const [phase, setPhase] = useState<Phase>('starting')
  const [poseIndex, setPoseIndex] = useState(0)
  const [shotCount, setShotCount] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [result, setResult] = useState<FaceEnrollResult | null>(null)

  const enrollFace = useEnrollFace()

  useEffect(() => {
    let cancelled = false

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: 'user' },
        })
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
        setPhase('capturing')
      } catch {
        setErrorMessage('Could not access the camera. Check browser permissions.')
        setPhase('error')
      }
    }

    start()
    return () => {
      cancelled = true
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  useEffect(() => {
    if (phase !== 'capturing') return
    if (poseIndex >= POSES.length) {
      void finishCapture()
      return
    }

    const targetShots = POSES[poseIndex].shots
    if (shotCount >= targetShots) {
      const timer = setTimeout(() => {
        setPoseIndex((p) => p + 1)
        setShotCount(0)
      }, 400)
      return () => clearTimeout(timer)
    }

    const timer = setTimeout(() => {
      captureFrame()
      setShotCount((c) => c + 1)
    }, CAPTURE_INTERVAL_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, poseIndex, shotCount])

  function captureFrame() {
    const video = videoRef.current
    if (!video) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (blob) capturedBlobs.current.push(blob)
      },
      'image/jpeg',
      0.9,
    )
  }

  async function finishCapture() {
    setPhase('uploading')
    streamRef.current?.getTracks().forEach((t) => t.stop())
    try {
      const uploadResult = await enrollFace.mutateAsync({
        studentId: student.id,
        photos: capturedBlobs.current,
      })
      setResult(uploadResult)
      setPhase('done')
    } catch {
      setErrorMessage('Upload failed. Check your connection and try again.')
      setPhase('error')
    }
  }

  const totalShots = POSES.reduce((sum, p) => sum + p.shots, 0)
  const shotsSoFar = POSES.slice(0, poseIndex).reduce((sum, p) => sum + p.shots, 0) + shotCount

  return (
    <Modal title={`Enroll face — ${student.name}`} onClose={onClose} widthClassName="max-w-lg">
      {phase === 'error' && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {errorMessage}
        </div>
      )}

      {(phase === 'starting' || phase === 'capturing') && (
        <div>
          <div className="relative mx-auto aspect-video w-full overflow-hidden rounded-lg bg-black">
            <video ref={videoRef} muted playsInline className="h-full w-full -scale-x-100 object-cover" />
          </div>
          <div className="mt-4 text-center">
            {phase === 'starting' ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">Starting camera…</p>
            ) : (
              <>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {POSES[poseIndex]?.label ?? 'Hold still…'}
                </p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Captured {shotsSoFar} / {totalShots}
                </p>
                <div className="mt-2 h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-800">
                  <div
                    className="h-1.5 rounded-full bg-brand-600 transition-all"
                    style={{ width: `${(shotsSoFar / totalShots) * 100}%` }}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {phase === 'uploading' && (
        <div className="flex flex-col items-center gap-3 py-8">
          <Camera className="animate-pulse text-brand-600" size={32} />
          <p className="text-sm text-gray-500 dark:text-gray-400">Processing captures…</p>
        </div>
      )}

      {phase === 'done' && result && (
        <div>
          <div className="mb-4 flex items-center gap-2">
            {result.images_usable > 0 ? (
              <CheckCircle2 className="text-present" size={22} />
            ) : (
              <XCircle className="text-absent" size={22} />
            )}
            <p className="font-medium text-gray-900 dark:text-gray-100">
              {result.images_usable}/{result.images_received} captures usable
              {result.average_quality != null && ` · avg quality ${(result.average_quality * 100).toFixed(0)}%`}
            </p>
          </div>
          {result.rejected_reasons.length > 0 && (
            <ul className="mb-4 list-inside list-disc space-y-1 text-xs text-gray-500 dark:text-gray-400">
              {result.rejected_reasons.map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
          )}
          <p className="mb-4 text-sm text-gray-600 dark:text-gray-300">
            {result.total_embeddings_stored} total face samples stored for this student.
          </p>
          <button
            onClick={onClose}
            className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Done
          </button>
        </div>
      )}
    </Modal>
  )
}

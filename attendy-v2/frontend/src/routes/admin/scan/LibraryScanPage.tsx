import { useCallback, useState } from 'react'
import { Wifi, WifiOff, BookOpen } from 'lucide-react'
import clsx from 'clsx'
import { useRecognitionSocket } from '../../../hooks/useRecognitionSocket'
import { drawLabel, resizeCanvasToVideo } from '../../../lib/canvasOverlay'

interface FaceResult {
  bbox: [number, number, number, number]
  status: 'unknown' | 'recognizing' | 'confirmed' | 'already_marked'
  name: string | null
  similarity: number
  live: boolean
}

interface QRResult {
  points: [number, number][] | null
  status: 'unknown' | 'confirmed' | 'already_marked'
  name: string | null
}

interface LibraryMessage {
  stage: 'identifying' | 'awaiting_book' | 'done'
  student: { id: string; name: string } | null
  book: { id: string; name: string } | null
  action: 'borrowed' | 'returned' | 'rejected' | null
  message: string | null
  faces: FaceResult[]
  qr: QRResult | null
}

const FACE_COLOR: Record<FaceResult['status'], string> = {
  unknown: '#dc2626',
  recognizing: '#f59e0b',
  confirmed: '#16a34a',
  already_marked: '#2563eb',
}

const ACTION_STYLE: Record<NonNullable<LibraryMessage['action']>, string> = {
  borrowed: 'bg-green-50 text-present dark:bg-green-950',
  returned: 'bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400',
  rejected: 'bg-red-50 text-absent dark:bg-red-950',
}

export function LibraryScanPage() {
  const [lastResult, setLastResult] = useState<LibraryMessage | null>(null)

  const handleMessage = useCallback((raw: unknown, video: HTMLVideoElement, canvas: HTMLCanvasElement) => {
    const data = raw as LibraryMessage
    setLastResult(data)

    resizeCanvasToVideo(canvas, video)
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    for (const face of data.faces) {
      const [x1, y1, x2, y2] = face.bbox
      const color = FACE_COLOR[face.status]
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
      drawLabel(ctx, x1, y1 - 24, face.name ?? face.status, color)
    }

    if (data.qr?.points) {
      const color = data.qr.status === 'unknown' ? '#dc2626' : '#16a34a'
      const [p0, p1, p2, p3] = data.qr.points
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.moveTo(p0[0], p0[1])
      ctx.lineTo(p1[0], p1[1])
      ctx.lineTo(p2[0], p2[1])
      ctx.lineTo(p3[0], p3[1])
      ctx.closePath()
      ctx.stroke()
      const top = data.qr.points.reduce((min, p) => Math.min(min, p[1]), Infinity)
      const left = data.qr.points.reduce((min, p) => Math.min(min, p[0]), Infinity)
      drawLabel(ctx, left, top - 24, data.qr.name ?? 'QR', color)
    }
  }, [])

  const { videoRef, canvasRef, connected, cameraError } = useRecognitionSocket({
    mode: 'library',
    onMessage: handleMessage,
  })

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Library Scan</h1>
        <div className="flex items-center gap-2 text-sm">
          {connected ? (
            <span className="flex items-center gap-1.5 text-present">
              <Wifi size={16} /> Connected
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-gray-400">
              <WifiOff size={16} /> Connecting…
            </span>
          )}
        </div>
      </div>

      {cameraError && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {cameraError}
        </div>
      )}

      <div className="mb-4 flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm dark:border-gray-800 dark:bg-gray-900">
        <BookOpen size={18} className="shrink-0 text-brand-600 dark:text-brand-400" />
        {!lastResult || lastResult.stage === 'identifying' ? (
          <span className="text-gray-600 dark:text-gray-300">
            Step 1 — scan your face or student QR code to identify yourself.
          </span>
        ) : lastResult.stage === 'awaiting_book' ? (
          <span className="text-gray-900 dark:text-gray-100">
            Hi <strong>{lastResult.student?.name}</strong> — now scan the book's QR code.
          </span>
        ) : (
          <span
            className={clsx(
              'rounded-md px-2 py-0.5 font-medium',
              lastResult.action && ACTION_STYLE[lastResult.action],
            )}
          >
            {lastResult.message}
          </span>
        )}
      </div>

      <div className="relative mx-auto aspect-video max-w-3xl overflow-hidden rounded-xl bg-black">
        <video ref={videoRef} muted playsInline className="h-full w-full -scale-x-100 object-cover" />
        <canvas ref={canvasRef} className="absolute inset-0 h-full w-full -scale-x-100" />
      </div>
      <p className="mt-3 text-center text-xs text-gray-500 dark:text-gray-400">
        Identify a student (face or QR), then scan a book's QR code to borrow or return it.
      </p>
    </div>
  )
}

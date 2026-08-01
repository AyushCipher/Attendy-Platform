import { useCallback } from 'react'
import { Wifi, WifiOff } from 'lucide-react'
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

const STATUS_STYLE: Record<FaceResult['status'], { color: string; label: (f: FaceResult) => string }> = {
  unknown: { color: '#dc2626', label: () => 'Unknown' },
  recognizing: { color: '#f59e0b', label: () => 'Recognizing…' },
  confirmed: { color: '#16a34a', label: (f) => `${f.name} — marked present` },
  already_marked: { color: '#2563eb', label: (f) => `${f.name} — already marked today` },
}

const QR_STATUS_STYLE: Record<QRResult['status'], { color: string; label: (q: QRResult) => string }> = {
  unknown: { color: '#dc2626', label: () => 'Unrecognized QR' },
  confirmed: { color: '#16a34a', label: (q) => `${q.name} — marked present (QR)` },
  already_marked: { color: '#2563eb', label: (q) => `${q.name} — already marked today (QR)` },
}

export function AttendanceScanPage() {
  const handleMessage = useCallback((raw: unknown, video: HTMLVideoElement, canvas: HTMLCanvasElement) => {
    const data = raw as { faces: FaceResult[]; qr: QRResult | null }
    resizeCanvasToVideo(canvas, video)
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    for (const face of data.faces) {
      const [x1, y1, x2, y2] = face.bbox
      const style = STATUS_STYLE[face.status]
      ctx.strokeStyle = style.color
      ctx.lineWidth = 3
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)
      drawLabel(ctx, x1, y1 - 24, style.label(face), style.color)
    }

    if (data.qr?.points) {
      const style = QR_STATUS_STYLE[data.qr.status]
      const [p0, p1, p2, p3] = data.qr.points
      ctx.strokeStyle = style.color
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
      drawLabel(ctx, left, top - 24, style.label(data.qr), style.color)
    }
  }, [])

  const { videoRef, canvasRef, connected, cameraError } = useRecognitionSocket({
    mode: 'attendance',
    onMessage: handleMessage,
  })

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Attendance Scan</h1>
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

      <div className="relative mx-auto aspect-video max-w-3xl overflow-hidden rounded-xl bg-black">
        <video ref={videoRef} muted playsInline className="h-full w-full -scale-x-100 object-cover" />
        <canvas ref={canvasRef} className="absolute inset-0 h-full w-full -scale-x-100" />
      </div>
      <p className="mt-3 text-center text-xs text-gray-500 dark:text-gray-400">
        Attendance updates in real time on the Attendance page as students are confirmed. Either a
        recognized face or a scanned student QR code marks attendance.
      </p>
    </div>
  )
}

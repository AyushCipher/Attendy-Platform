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

const STATUS_STYLE: Record<FaceResult['status'], { color: string; label: (f: FaceResult) => string }> = {
  unknown: { color: '#dc2626', label: () => 'Unknown' },
  recognizing: { color: '#f59e0b', label: () => 'Recognizing…' },
  confirmed: { color: '#16a34a', label: (f) => `${f.name} — meal marked` },
  already_marked: { color: '#2563eb', label: (f) => `${f.name} — already marked today` },
}

export function MessScanPage() {
  const handleMessage = useCallback((raw: unknown, video: HTMLVideoElement, canvas: HTMLCanvasElement) => {
    const data = raw as { faces: FaceResult[] }
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
  }, [])

  const { videoRef, canvasRef, connected, cameraError } = useRecognitionSocket({
    mode: 'mess',
    onMessage: handleMessage,
  })

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Mess Scan</h1>
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
        Face recognition only — meal marking has no QR fallback.
      </p>
    </div>
  )
}

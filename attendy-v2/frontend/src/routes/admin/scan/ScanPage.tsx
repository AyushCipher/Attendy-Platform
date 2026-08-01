import { useEffect, useRef, useState } from 'react'
import { Wifi, WifiOff } from 'lucide-react'
import { useAuthStore } from '../../../store/authStore'

interface FaceResult {
  bbox: [number, number, number, number]
  status: 'unknown' | 'recognizing' | 'confirmed' | 'already_marked'
  name: string | null
  similarity: number
  live: boolean
}

const CAPTURE_INTERVAL_MS = 200

const STATUS_STYLE: Record<FaceResult['status'], { color: string; label: (f: FaceResult) => string }> = {
  unknown: { color: '#dc2626', label: () => 'Unknown' },
  recognizing: { color: '#f59e0b', label: () => 'Recognizing…' },
  confirmed: { color: '#16a34a', label: (f) => `${f.name} — marked present` },
  already_marked: { color: '#2563eb', label: (f) => `${f.name} — already marked today` },
}

export function ScanPage() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const captureCanvasRef = useRef<HTMLCanvasElement>(document.createElement('canvas'))
  const inFlightRef = useRef(false)

  const [connected, setConnected] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const accessToken = useAuthStore((s) => s.accessToken)

  useEffect(() => {
    let stream: MediaStream | null = null
    let intervalId: number | undefined

    async function start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: 'user' },
        })
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
      } catch {
        setCameraError('Could not access the camera. Check browser permissions.')
        return
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/recognize?token=${accessToken}`)
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => setConnected(false)
      ws.onerror = () => setConnected(false)
      ws.onmessage = (event) => {
        inFlightRef.current = false
        try {
          const data = JSON.parse(event.data) as { faces: FaceResult[] }
          drawOverlay(data.faces)
        } catch {
          // ignore malformed frame
        }
      }

      intervalId = window.setInterval(() => captureAndSend(), CAPTURE_INTERVAL_MS)
    }

    function captureAndSend() {
      const video = videoRef.current
      const ws = wsRef.current
      if (!video || !ws || ws.readyState !== WebSocket.OPEN) return
      if (inFlightRef.current) return // drop this tick if the previous frame hasn't been acked yet

      const canvas = captureCanvasRef.current
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.drawImage(video, 0, 0)

      canvas.toBlob(
        (blob) => {
          if (blob && ws.readyState === WebSocket.OPEN) {
            inFlightRef.current = true
            ws.send(blob)
          }
        },
        'image/jpeg',
        0.7,
      )
    }

    function drawOverlay(faces: FaceResult[]) {
      const canvas = canvasRef.current
      const video = videoRef.current
      if (!canvas || !video) return
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      for (const face of faces) {
        const [x1, y1, x2, y2] = face.bbox
        const style = STATUS_STYLE[face.status]
        ctx.strokeStyle = style.color
        ctx.lineWidth = 3
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

        const label = style.label(face)
        ctx.font = '16px system-ui'
        const textWidth = ctx.measureText(label).width
        ctx.fillStyle = style.color
        ctx.fillRect(x1, y1 - 24, textWidth + 12, 24)
        ctx.fillStyle = '#fff'
        ctx.fillText(label, x1 + 6, y1 - 6)
      }
    }

    start()

    return () => {
      if (intervalId) window.clearInterval(intervalId)
      wsRef.current?.close()
      stream?.getTracks().forEach((t) => t.stop())
    }
  }, [accessToken])

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Live Scan</h1>
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
        Attendance updates in real time on the Attendance page as students are confirmed.
      </p>
    </div>
  )
}

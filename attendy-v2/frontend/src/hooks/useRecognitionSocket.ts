import { useEffect, useRef, useState } from 'react'
import { useAuthStore } from '../store/authStore'

const CAPTURE_INTERVAL_MS = 200

export type ScanMode = 'attendance' | 'mess' | 'library'

interface UseRecognitionSocketOptions {
  mode: ScanMode
  // Receives the live video/canvas elements as arguments (rather than the caller
  // closing over refs returned by this hook) -- avoids a temporal-dead-zone
  // ordering problem: the hook must exist to produce the refs, but would otherwise
  // need the callback (which needs those same refs) before it can be called.
  onMessage: (data: unknown, video: HTMLVideoElement, canvas: HTMLCanvasElement) => void
}

/** Camera setup + WS connect (with ?mode=) + frame capture/send loop + cleanup --
 * shared by the attendance, mess, and library scan pages so each one only has to
 * own its own overlay-drawing/status UI, not re-implement getUserMedia/WS plumbing
 * three times. Extracted once a third real consumer (library) needed it. */
export function useRecognitionSocket({ mode, onMessage }: UseRecognitionSocketOptions) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const captureCanvasRef = useRef<HTMLCanvasElement>(document.createElement('canvas'))
  const inFlightRef = useRef(false)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const [connected, setConnected] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const accessToken = useAuthStore((s) => s.accessToken)

  useEffect(() => {
    let cancelled = false
    let stream: MediaStream | null = null
    let intervalId: number | undefined

    async function start() {
      try {
        const newStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: 'user' },
        })
        if (cancelled) {
          // Effect was torn down (e.g. React StrictMode's dev-only double-invoke)
          // while getUserMedia was still pending -- release it immediately instead
          // of leaving an orphaned camera handle or a stale error/success race.
          newStream.getTracks().forEach((t) => t.stop())
          return
        }
        stream = newStream
        setCameraError(null)
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
      } catch {
        if (!cancelled) setCameraError('Could not access the camera. Check browser permissions.')
        return
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(
        `${protocol}//${window.location.host}/ws/recognize?mode=${mode}&token=${accessToken}`,
      )
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => setConnected(false)
      ws.onerror = () => setConnected(false)
      ws.onmessage = (event) => {
        inFlightRef.current = false
        const video = videoRef.current
        const canvas = canvasRef.current
        if (!video || !canvas) return
        try {
          onMessageRef.current(JSON.parse(event.data), video, canvas)
        } catch {
          // ignore malformed frame
        }
      }

      intervalId = window.setInterval(captureAndSend, CAPTURE_INTERVAL_MS)
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

    start()

    return () => {
      cancelled = true
      if (intervalId) window.clearInterval(intervalId)
      wsRef.current?.close()
      stream?.getTracks().forEach((t) => t.stop())
    }
  }, [accessToken, mode])

  return { videoRef, canvasRef, connected, cameraError }
}

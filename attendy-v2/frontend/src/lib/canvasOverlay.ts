/** Draws a filled label box + text at (x, y). The scan pages' <canvas> is
 * CSS-mirrored (-scale-x-100) to match the selfie-view video, which also mirrors
 * anything drawn on it -- including text, making it read backwards. Pre-mirroring
 * just the glyphs here means the outer CSS flip cancels it back out to normal,
 * readable text. */
export function drawLabel(ctx: CanvasRenderingContext2D, x: number, y: number, text: string, color: string) {
  ctx.font = '16px system-ui'
  const textWidth = ctx.measureText(text).width
  const boxW = textWidth + 12
  ctx.fillStyle = color
  ctx.fillRect(x, y, boxW, 24)

  ctx.save()
  ctx.translate(x + boxW, 0)
  ctx.scale(-1, 1)
  ctx.fillStyle = '#fff'
  ctx.fillText(text, 6, y + 18)
  ctx.restore()
}

export function resizeCanvasToVideo(canvas: HTMLCanvasElement, video: HTMLVideoElement) {
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
}

import { useRef, useState, useEffect } from 'preact/hooks'

// xy pad maps normalized x/y [0..1] to 16-bit pan/tilt values (0..65535)
const to16 = (n) => Math.max(0, Math.min(65535, Math.round(n * 65535)))
const from16 = (v) => Math.max(0, Math.min(65535, Number(v) || 0))

export default function XYPad({ pan16 = 0, tilt16 = 0, onChange }) {
  const ref = useRef(null)
  const draggingRef = useRef(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })

  useEffect(() => {
    const nx = from16(pan16) / 65535
    const ny = from16(tilt16) / 65535
    setPos({ x: nx, y: ny })
  }, [pan16, tilt16])

  const updateFromPointer = (clientX, clientY) => {
    const r = ref.current?.getBoundingClientRect()
    if (!r) return
    const x = Math.max(0, Math.min(1, (clientX - r.left) / r.width))
    const y = Math.max(0, Math.min(1, (clientY - r.top) / r.height))
    const pan = to16(x)
    const tilt = to16(y)
    setPos({ x, y })
    onChange?.(pan, tilt)
  }

  const handlePointerDown = (e) => {
    e.currentTarget.setPointerCapture(e.pointerId)
    draggingRef.current = true
    updateFromPointer(e.clientX, e.clientY)
  }
  const handlePointerMove = (e) => {
    if (!draggingRef.current) return
    updateFromPointer(e.clientX, e.clientY)
  }
  const handlePointerUp = (e) => {
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch (err) {
      /* ignore */
    }
    draggingRef.current = false
  }

  return (
    <div class="xyPad" ref={ref} onPointerDown={handlePointerDown} onPointerMove={handlePointerMove} onPointerUp={handlePointerUp} onPointerCancel={handlePointerUp}>
      <div class="xyPadCrosshair" style={{ left: `${pos.x * 100}%`, top: `${pos.y * 100}%` }} />
      <div class="xyPadMarker" style={{ left: `${pos.x * 100}%`, top: `${pos.y * 100}%` }} />
    </div>
  )
}

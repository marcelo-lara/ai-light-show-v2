import { useRef } from 'preact/hooks'

function clampUnit(value) {
  return Math.max(0, Math.min(1, value))
}

export default function XYPad({ pan16, tilt16, onChange }) {
  const draggingRef = useRef(false)

  const emitFromPointer = (target, clientX, clientY) => {
    const rect = target.getBoundingClientRect()
    if (!rect.width || !rect.height) return

    const x = clampUnit((clientX - rect.left) / rect.width)
    const y = clampUnit((clientY - rect.top) / rect.height)
    const nextPan = Math.round(x * 65535)
    const nextTilt = Math.round(y * 65535)
    onChange?.(nextPan, nextTilt)
  }

  const onPointerDown = (e) => {
    draggingRef.current = true
    e.currentTarget.setPointerCapture(e.pointerId)
    emitFromPointer(e.currentTarget, e.clientX, e.clientY)
  }

  const onPointerMove = (e) => {
    if (!draggingRef.current) return
    emitFromPointer(e.currentTarget, e.clientX, e.clientY)
  }

  const onPointerEnd = (e) => {
    draggingRef.current = false
    if (e.currentTarget.hasPointerCapture?.(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId)
    }
  }

  const xPercent = Math.max(0, Math.min(100, (Number(pan16 || 0) / 65535) * 100))
  const yPercent = Math.max(0, Math.min(100, (Number(tilt16 || 0) / 65535) * 100))

  return (
    <div class="xyPadWrap">
      <div
        class="xyPad"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerEnd}
        onPointerCancel={onPointerEnd}
        role="application"
        aria-label="Pan tilt pad"
      >
        <div class="xyPadCrosshair xyPadCrosshairX" />
        <div class="xyPadCrosshair xyPadCrosshairY" />
        <div class="xyPadMarker" style={{ left: `${xPercent}%`, top: `${yPercent}%` }} />
      </div>
      <div class="xyPadReadout muted">
        Pan {Math.round(Number(pan16 || 0))} / Tilt {Math.round(Number(tilt16 || 0))}
      </div>
    </div>
  )
}

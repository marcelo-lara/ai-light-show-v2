import { useEffect, useMemo, useState } from 'preact/hooks'

export default function WheelButtonRow({ label, channelNum, valueMappings = [], currentValue, onSelect }) {
  if (!channelNum || !Array.isArray(valueMappings) || valueMappings.length === 0) return null

  const PAGE_SIZE = 8
  const totalPages = Math.max(1, Math.ceil(valueMappings.length / PAGE_SIZE))
  const [page, setPage] = useState(0)

  // ensure the active value is visible when currentValue changes
  useEffect(() => {
    const idx = valueMappings.findIndex((v) => v.value === currentValue)
    if (idx >= 0) {
      const p = Math.floor(idx / PAGE_SIZE)
      if (p !== page) setPage(p)
    }
  }, [currentValue, valueMappings])

  const pageSlice = useMemo(() => {
    const start = page * PAGE_SIZE
    return valueMappings.slice(start, start + PAGE_SIZE)
  }, [page, valueMappings])

  const prev = () => setPage((s) => Math.max(0, s - 1))
  const next = () => setPage((s) => Math.min(totalPages - 1, s + 1))

  return (
    <div class="wheelRow">
      <div style={{ width: '120px', fontSize: '13px', fontWeight: 600 }}>{label}</div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {pageSlice.map((opt) => {
            const active = currentValue === opt.value
            return (
              <button
                class={`wheelButton ${active ? 'wheelButtonActive' : ''}`}
                title={opt.label ?? String(opt.value)}
                onClick={() => onSelect?.(opt.value)}
                aria-pressed={active}
              >
                <span class="wheelButtonLabel">{opt.label ?? opt.value}</span>
              </button>
            )
          })}
        </div>

        {totalPages > 1 ? (
          <div class="wheelPager">
            <button class="wheelPagerButton" onClick={prev} disabled={page === 0} aria-label="Previous page">◀</button>
            <div class="wheelPagerIndicator">{page + 1}/{totalPages}</div>
            <button class="wheelPagerButton" onClick={next} disabled={page === totalPages - 1} aria-label="Next page">▶</button>
          </div>
        ) : null}
      </div>
    </div>
  )
}

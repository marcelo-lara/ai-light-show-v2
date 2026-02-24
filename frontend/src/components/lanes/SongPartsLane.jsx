export default function SongPartsLane({ song, timecode, onSeek }) {
  if (!song) {
    return (
      <div class="panel">
        <div class="panelHeader">
          <h3>Song parts</h3>
        </div>
        <div class="panelBody muted">No song loaded</div>
      </div>
    )
  }

  const parts = song.metadata.parts || {}
  const partEntries = Object.entries(parts)
    .map(([name, range], index) => {
      if (!Array.isArray(range) || !range.length) return null
      const start = Number(range[0])
      const end = Number(range.length > 1 ? range[1] : range[0])
      if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null
      return {
        id: `${name}-${index}`,
        name,
        start,
        end,
      }
    })
    .filter(Boolean)
    .sort((a, b) => a.start - b.start)

  return (
    <div class="panel">
      <div class="panelHeader">
        <h3>Song parts</h3>
      </div>
      <div class="panelBody">
        {partEntries.length === 0 ? (
          <div class="muted">No parts found in metadata</div>
        ) : (
          partEntries.map((part) => {
            const isActive = timecode >= part.start && timecode < part.end
            return (
              <button
                key={part.id}
                class="card"
                type="button"
                style={{
                  borderColor: isActive ? '#4a9eff' : '#333',
                  textAlign: 'left',
                  width: '100%',
                }}
                onClick={() => onSeek?.(part.start)}
              >
                <div class="cardTitle">{part.name}</div>
                <div class="muted">Start: {part.start.toFixed(2)}s</div>
                <div class="muted">End: {part.end.toFixed(2)}s</div>
                <div class="muted">Duration: {(part.end - part.start).toFixed(2)}s</div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}

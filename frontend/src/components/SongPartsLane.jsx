export default function SongPartsLane({ song, timecode }) {
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

  return (
    <div class="panel">
      <div class="panelHeader">
        <h3>Song parts</h3>
      </div>
      <div class="panelBody">
        {Object.keys(parts).length === 0 ? (
          <div class="muted">No parts found in metadata</div>
        ) : (
          Object.entries(parts).map(([type, times]) =>
            times.map((time, index) => (
              <div
                key={`${type}-${index}`}
                class="card"
                style={{
                  borderColor: Math.abs(timecode - time) < 0.5 ? '#4a9eff' : '#333',
                }}
                onClick={() => {
                  console.log('Seek to', time)
                }}
              >
                <div class="cardTitle">{type}</div>
                <div class="muted">Time: {time.toFixed(2)}s</div>
                <div class="muted">
                  Duration: {((times[index + 1] || song.metadata.duration || 0) - time).toFixed(2)}s
                </div>
              </div>
            ))
          )
        )}
      </div>
    </div>
  )
}
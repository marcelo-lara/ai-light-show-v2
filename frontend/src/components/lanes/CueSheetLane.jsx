export default function CueSheetLane({ cues, timecode }) {
  return (
    <div class="panel">
      <div class="panelHeader">
        <h3>DMX Cue Sheet</h3>
      </div>
      <div class="panelBody">
        {cues.length === 0 ? (
          <div class="muted">No cues yet</div>
        ) : (
          cues.map((cue, index) => (
            <div
              key={index}
              class="card"
              style={{
                borderColor: Math.abs(timecode - cue.time) < 0.5 ? '#4a9eff' : '#333',
                cursor: 'pointer',
              }}
              onClick={() => {
                console.log('Seek to cue', cue.time)
              }}
            >
              <div class="cardTitle">{cue.name || `Cue ${index + 1}`}</div>
              <div class="muted">Time: {cue.time.toFixed(2)}s</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

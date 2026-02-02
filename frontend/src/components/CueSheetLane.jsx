export default function CueSheetLane({ cues, timecode }) {
  return (
    <div style={{ flex: 1, borderRight: '1px solid #333', padding: '10px', overflowY: 'auto' }}>
      <h3>Cue Sheet</h3>
      {cues.map((cue, index) => (
        <div
          key={index}
          style={{
            padding: '5px',
            margin: '5px 0',
            background: Math.abs(timecode - cue.timecode) < 0.5 ? '#4a9eff' : '#333',
            cursor: 'pointer'
          }}
          onClick={() => {
            console.log('Seek to cue', cue.timecode)
          }}
        >
          <div>Time: {cue.timecode.toFixed(2)}s</div>
          <div>Name: {cue.name || `Cue ${index + 1}`}</div>
        </div>
      ))}
    </div>
  )
}
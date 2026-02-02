export default function SongPartsLane({ song, timecode }) {
  if (!song) return <div style={{ flex: 1, borderRight: '1px solid #333', padding: '10px' }}>No song loaded</div>

  const parts = song.metadata.parts || {}

  return (
    <div style={{ flex: 1, borderRight: '1px solid #333', padding: '10px', overflowY: 'auto' }}>
      <h3>Song Parts</h3>
      {Object.entries(parts).map(([type, times]) => (
        times.map((time, index) => (
          <div
            key={`${type}-${index}`}
            style={{
              padding: '5px',
              margin: '5px 0',
              background: timecode >= time && timecode < (times[index + 1] || Infinity) ? '#4a9eff' : '#333',
              cursor: 'pointer'
            }}
            onClick={() => {
              // Seek to time
              // This would need to be passed down
              console.log('Seek to', time)
            }}
          >
            <div>Time: {time.toFixed(2)}s</div>
            <div>Type: {type}</div>
            <div>Duration: {((times[index + 1] || song.metadata.duration || 0) - time).toFixed(2)}s</div>
          </div>
        ))
      ))}
    </div>
  )
}
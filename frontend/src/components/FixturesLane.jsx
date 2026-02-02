export default function FixturesLane({ fixtures, dmxValues, onDmxChange, onAddCue, timecode }) {
  return (
    <div style={{ flex: 1, padding: '10px', overflowY: 'auto' }}>
      <h3>Fixtures</h3>
      {fixtures.map((fixture) => (
        <div key={fixture.id} style={{ marginBottom: '20px' }}>
          <h4>{fixture.name}</h4>
          {Object.entries(fixture.channels).map(([channelName, channelNum]) => (
            <div key={channelName} style={{ marginBottom: '10px' }}>
              <label>{channelName}: {dmxValues[channelNum] || 0}</label>
              <input
                type="range"
                min="0"
                max="255"
                value={dmxValues[channelNum] || 0}
                onInput={(e) => onDmxChange(channelNum, parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
          ))}
        </div>
      ))}
      <button onClick={() => onAddCue(timecode)}>Add to Cue</button>
    </div>
  )
}
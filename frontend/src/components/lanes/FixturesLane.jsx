import CustomRangeSlider from '../ui/CustomRangeSlider.jsx'

export default function FixturesLane({ fixtures, dmxValues, onDmxChange, timecode }) {
  return (
    <div class="panel">
      <div class="panelHeader">
        <h3>DMX fixtures (plain control)</h3>
      </div>
      <div class="panelBody">
        {fixtures.length === 0 ? (
          <div class="muted">No fixtures loaded</div>
        ) : (
          fixtures.map((fixture) => (
            <div key={fixture.id} class="card">
              <div class="cardTitle">{fixture.name}</div>
              {Object.entries(fixture.channels).map(([channelName, channelNum]) => (
                <div key={channelName} style={{ marginBottom: '10px' }}>
                  <div
                    class="muted"
                    style={{ display: 'flex', justifyContent: 'space-between', gap: '10px' }}
                  >
                    <span>{channelName}</span>
                    <span>Ch {channelNum}</span>
                  </div>
                  <CustomRangeSlider
                    min={0}
                    max={255}
                    value={dmxValues[channelNum] || 0}
                    ariaLabel={`${fixture.name} ${channelName}`}
                    onInput={(nextValue) => onDmxChange(channelNum, nextValue)}
                  />
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

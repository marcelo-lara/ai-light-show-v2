import DmxSlider from '../dmx/DmxSlider.jsx'
import EffectPreviewControls from '../dmx/EffectPreviewControls.jsx'

export default function FixturesLane({ fixtures, dmxValues, onDmxChange, onPreviewEffect, isPlaybackActive }) {
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
                  <DmxSlider
                    label={`${channelName} (Ch ${channelNum})`}
                    value={dmxValues[channelNum] || 0}
                    onInput={(nextValue) => onDmxChange(channelNum, nextValue)}
                    disabled={isPlaybackActive}
                  />
                </div>
              ))}
              <EffectPreviewControls
                fixture={fixture}
                disabled={isPlaybackActive}
                onPreview={onPreviewEffect}
              />
            </div>
          ))
        )}
      </div>
    </div>
  )
}

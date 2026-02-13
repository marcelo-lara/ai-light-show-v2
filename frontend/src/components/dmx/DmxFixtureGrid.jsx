import MovingHeadCard from './MovingHeadCard'
import RgbParCard from './RgbParCard'

export default function DmxFixtureGrid({ fixtures = [], dmxValues = {}, onDmxChange }) {
  if (!fixtures || fixtures.length === 0) {
    return (
      <div class="card">
        <div class="cardTitle">No fixtures</div>
        <div class="muted">Add fixtures in the backend fixtures JSON or wait for the WebSocket initial payload.</div>
      </div>
    )
  }

  return (
    <div class="dmxGrid">
      {fixtures.map((f) => {
        if (f.type === 'moving_head') {
          return <MovingHeadCard fixture={f} dmxValues={dmxValues} onDmxChange={onDmxChange} />
        }
        if (f.type === 'rgb' || f.type === 'par') {
          return <RgbParCard fixture={f} dmxValues={dmxValues} onDmxChange={onDmxChange} />
        }
        // fallback: generic card showing first few channels
        return (
          <div class="dmxCard">
            <div class="dmxCardHeader">
              <div style={{ fontWeight: 700 }}>{f.name}</div>
              <div></div>
            </div>
            <div class="dmxCardBody">
              <div class="muted">No specific control implemented for fixture type: {f.type}</div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

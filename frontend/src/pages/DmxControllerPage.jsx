import { useAppState } from '../app/state'
import DmxFixtureGrid from '../components/dmx/DmxFixtureGrid'

export default function DmxControllerPage() {
  const { fixtures, dmxValues, actions } = useAppState()

  return (
    <div class="page dmxPage">
      <div class="pageHeader dmxHeader">
        <h2>DMX Controller</h2>
        <div class="muted">POIs, wheel presets, and per-fixture controls.</div>
      </div>
      <div class="pageBody">
        <DmxFixtureGrid fixtures={fixtures} dmxValues={dmxValues} onDmxChange={actions.handleDmxChange} />
      </div>
    </div>
  )
}

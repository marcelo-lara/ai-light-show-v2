import { useAppState } from '../app/state.jsx'
import DmxFixtureGrid from '../components/dmx/DmxFixtureGrid.jsx'

export default function DmxControllerPage() {
  const { fixtures, pois, dmxValues, actions, status } = useAppState()

  return (
    <div class="page dmxPage">
      <div class="pageHeader dmxHeader">
        <h2>DMX Control</h2>
        <div class="muted">Fixture-first controls with XY pan/tilt, wheel mapping, presets, and direct DMX.</div>
      </div>
      <div class="pageBody dmxBody">
        <DmxFixtureGrid
          fixtures={fixtures}
          pois={pois}
          dmxValues={dmxValues}
          onDmxChange={actions.handleDmxChange}
          onPreviewEffect={actions.handlePreviewEffect}
          onSavePoiTarget={actions.handleSavePoiTarget}
          isPlaybackActive={!!status?.isPlaying}
        />
      </div>
    </div>
  )
}

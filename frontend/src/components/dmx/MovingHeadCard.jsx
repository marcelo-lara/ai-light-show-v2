import DmxSlider from './DmxSlider.jsx'
import EffectPreviewControls from './EffectPreviewControls.jsx'
import WheelButtonRow from './WheelButtonRow.jsx'
import XYPad from './XYPad.jsx'
import {
  applyArmValues,
  compose16,
  getWheelOptions,
  readChannel,
  resolvePoiPanTilt16,
  write16,
  writeChannel,
} from './dmxUtils.js'

export default function MovingHeadCard({
  fixture,
  pois,
  dmxValues,
  onDmxChange,
  onPreviewEffect,
  onSavePoiTarget,
  disabled = false,
}) {
  const channels = fixture?.channels || {}
  const poiList = Array.isArray(pois) ? pois : []
  const sortedPoiList = [...poiList].sort((a, b) => {
    const aName = String(a?.name || a?.id || '')
    const bName = String(b?.name || b?.id || '')
    const byName = aName.localeCompare(bName, undefined, { sensitivity: 'base' })
    if (byName !== 0) return byName
    const aId = String(a?.id || '')
    const bId = String(b?.id || '')
    return aId.localeCompare(bId, undefined, { sensitivity: 'base' })
  })
  const poiTargets = fixture?.poi_targets && typeof fixture.poi_targets === 'object' ? fixture.poi_targets : {}

  const panMsbChannel = channels.pan_msb
  const panLsbChannel = channels.pan_lsb
  const tiltMsbChannel = channels.tilt_msb
  const tiltLsbChannel = channels.tilt_lsb

  const pan16 = compose16(readChannel(dmxValues, panMsbChannel), readChannel(dmxValues, panLsbChannel))
  const tilt16 = compose16(
    readChannel(dmxValues, tiltMsbChannel),
    readChannel(dmxValues, tiltLsbChannel)
  )

  const colorChannel = channels.color
  const goboChannel = channels.gobo

  const colorOptions = getWheelOptions(fixture, 'color')
  const goboOptions = getWheelOptions(fixture, 'gobo')

  const sliderChannels = Object.entries(channels).filter(([channelName]) => {
    return !['pan_msb', 'pan_lsb', 'tilt_msb', 'tilt_lsb', 'color', 'gobo'].includes(channelName)
  })

  const handlePadChange = (nextPan, nextTilt) => {
    write16(onDmxChange, panMsbChannel, panLsbChannel, nextPan)
    write16(onDmxChange, tiltMsbChannel, tiltLsbChannel, nextTilt)
  }

  const handlePoiClick = (event, poi) => {
    const poiId = String(poi?.id || '')
    if (!poiId) return

    if (event?.shiftKey) {
      onSavePoiTarget?.({
        fixtureId: fixture?.id,
        poiId,
        pan16,
        tilt16,
      })
      return
    }

    const target = resolvePoiPanTilt16(poiTargets[poiId])
    if (!target) return

    write16(onDmxChange, panMsbChannel, panLsbChannel, target.pan16)
    write16(onDmxChange, tiltMsbChannel, tiltLsbChannel, target.tilt16)
  }

  return (
    <section class="dmxCard">
      <header class="dmxCardHeader">
        <h3>{fixture?.name || 'Moving Head'}</h3>
        <button
          type="button"
          class="dmxArmButton"
          onClick={() => applyArmValues(fixture, onDmxChange)}
          disabled={disabled}
        >
          Arm
        </button>
      </header>

      <div class="dmxCardBody movingHeadLayout">
        <div class="movingHeadLeft">
          <XYPad pan16={pan16} tilt16={tilt16} onChange={handlePadChange} disabled={disabled} />
          <div class="poiGrid">
            {sortedPoiList.length === 0 ? (
              <div class="muted">No POI presets</div>
            ) : (
              sortedPoiList.map((poi) => {
                const poiId = String(poi?.id || '')
                const hasMapping = !!resolvePoiPanTilt16(poiTargets[poiId])
                return (
                  <button
                    type="button"
                    key={`${fixture.id}-${poiId}`}
                    class={`poiButton ${hasMapping ? '' : 'poiButtonUnmapped'}`.trim()}
                    onClick={(event) => handlePoiClick(event, poi)}
                    disabled={disabled}
                  >
                    {poi?.name || poiId}
                  </button>
                )
              })
            )}
          </div>
        </div>

        <div class="movingHeadRight">
          <WheelButtonRow
            label="Color"
            currentValue={readChannel(dmxValues, colorChannel)}
            options={colorOptions}
            onSelect={(value) => writeChannel(onDmxChange, colorChannel, value)}
            disabled={disabled}
          />
          <WheelButtonRow
            label="Gobo"
            currentValue={readChannel(dmxValues, goboChannel)}
            options={goboOptions}
            onSelect={(value) => writeChannel(onDmxChange, goboChannel, value)}
            disabled={disabled}
          />

          {sliderChannels.map(([channelName, channelNum]) => (
            <DmxSlider
              key={`${fixture.id}-${channelName}`}
              label={channelName}
              value={readChannel(dmxValues, channelNum)}
              onInput={(value) => writeChannel(onDmxChange, channelNum, value)}
              disabled={disabled}
            />
          ))}
        </div>

        <EffectPreviewControls
          fixture={fixture}
          pois={pois}
          disabled={disabled}
          onPreview={onPreviewEffect}
        />
      </div>
    </section>
  )
}

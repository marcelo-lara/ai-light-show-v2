import DmxSlider from './DmxSlider.jsx'
import WheelButtonRow from './WheelButtonRow.jsx'
import XYPad from './XYPad.jsx'
import {
  applyArmValues,
  applyPresetValues,
  compose16,
  getWheelOptions,
  readChannel,
  write16,
  writeChannel,
} from './dmxUtils.js'

export default function MovingHeadCard({ fixture, dmxValues, onDmxChange }) {
  const channels = fixture?.channels || {}
  const presets = Array.isArray(fixture?.presets) ? fixture.presets : []

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

  return (
    <section class="dmxCard">
      <header class="dmxCardHeader">
        <h3>{fixture?.name || 'Moving Head'}</h3>
        <button type="button" class="dmxArmButton" onClick={() => applyArmValues(fixture, onDmxChange)}>
          Arm
        </button>
      </header>

      <div class="dmxCardBody movingHeadLayout">
        <div class="movingHeadLeft">
          <XYPad pan16={pan16} tilt16={tilt16} onChange={handlePadChange} />
          <div class="poiGrid">
            {presets.length === 0 ? (
              <div class="muted">No POI presets</div>
            ) : (
              presets.map((preset) => (
                <button
                  type="button"
                  key={`${fixture.id}-${preset.name}`}
                  class="poiButton"
                  onClick={() => applyPresetValues(fixture, preset, onDmxChange)}
                >
                  {preset.name}
                </button>
              ))
            )}
          </div>
        </div>

        <div class="movingHeadRight">
          <WheelButtonRow
            label="Color"
            currentValue={readChannel(dmxValues, colorChannel)}
            options={colorOptions}
            onSelect={(value) => writeChannel(onDmxChange, colorChannel, value)}
          />
          <WheelButtonRow
            label="Gobo"
            currentValue={readChannel(dmxValues, goboChannel)}
            options={goboOptions}
            onSelect={(value) => writeChannel(onDmxChange, goboChannel, value)}
          />

          {sliderChannels.map(([channelName, channelNum]) => (
            <DmxSlider
              key={`${fixture.id}-${channelName}`}
              label={channelName}
              value={readChannel(dmxValues, channelNum)}
              onInput={(value) => writeChannel(onDmxChange, channelNum, value)}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

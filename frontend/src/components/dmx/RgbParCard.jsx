import ChannelSlider from './ChannelSlider.jsx'
import { applyArmValues, readChannel, writeChannel } from './dmxUtils.js'

const RGB_PRESETS = [
  { name: 'White', rgb: [255, 255, 255], swatch: '#d9d9d9' },
  { name: 'Red', rgb: [255, 0, 0], swatch: '#cc4040' },
  { name: 'Green', rgb: [0, 255, 0], swatch: '#3ea95a' },
  { name: 'Blue', rgb: [0, 0, 255], swatch: '#446ecc' },
  { name: 'Cyan', rgb: [0, 255, 255], swatch: '#47a7b7' },
  { name: 'Magenta', rgb: [255, 0, 255], swatch: '#b25ca9' },
  { name: 'Yellow', rgb: [255, 255, 0], swatch: '#b5aa4b' },
  { name: 'Off', rgb: [0, 0, 0], swatch: '#3b3b3b' },
]

export default function RgbParCard({ fixture, dmxValues, onDmxChange }) {
  const channels = fixture?.channels || {}

  const redChannel = channels.red
  const greenChannel = channels.green
  const blueChannel = channels.blue
  const strobeChannel = channels.strobe
  const dimmerChannel = channels.dim ?? channels.dimmer

  const applyRgbPreset = (preset) => {
    const [red, green, blue] = preset.rgb
    writeChannel(onDmxChange, redChannel, red)
    writeChannel(onDmxChange, greenChannel, green)
    writeChannel(onDmxChange, blueChannel, blue)

    if (dimmerChannel) {
      writeChannel(onDmxChange, dimmerChannel, preset.name === 'Off' ? 0 : 255)
    }
  }

  return (
    <section class="dmxCard">
      <header class="dmxCardHeader">
        <h3>{fixture?.name || 'RGB Fixture'}</h3>
        <button type="button" class="dmxArmButton" onClick={() => applyArmValues(fixture, onDmxChange)}>
          Arm
        </button>
      </header>

      <div class="dmxCardBody">
        <div class="rgbPresetGrid">
          {RGB_PRESETS.map((preset) => (
            <button
              key={`${fixture.id}-${preset.name}`}
              type="button"
              class="rgbPresetButton"
              style={{ '--preset-color': preset.swatch }}
              onClick={() => applyRgbPreset(preset)}
              title={preset.name}
            >
              <span>{preset.name}</span>
            </button>
          ))}
        </div>

        {redChannel ? (
          <ChannelSlider
            label="Red"
            channelNum={redChannel}
            value={readChannel(dmxValues, redChannel)}
            onInput={(value) => writeChannel(onDmxChange, redChannel, value)}
          />
        ) : null}
        {greenChannel ? (
          <ChannelSlider
            label="Green"
            channelNum={greenChannel}
            value={readChannel(dmxValues, greenChannel)}
            onInput={(value) => writeChannel(onDmxChange, greenChannel, value)}
          />
        ) : null}
        {blueChannel ? (
          <ChannelSlider
            label="Blue"
            channelNum={blueChannel}
            value={readChannel(dmxValues, blueChannel)}
            onInput={(value) => writeChannel(onDmxChange, blueChannel, value)}
          />
        ) : null}
        {strobeChannel ? (
          <ChannelSlider
            label="Strobe"
            channelNum={strobeChannel}
            value={readChannel(dmxValues, strobeChannel)}
            onInput={(value) => writeChannel(onDmxChange, strobeChannel, value)}
          />
        ) : null}
        {dimmerChannel ? (
          <ChannelSlider
            label="Dimmer"
            channelNum={dimmerChannel}
            value={readChannel(dmxValues, dimmerChannel)}
            onInput={(value) => writeChannel(onDmxChange, dimmerChannel, value)}
          />
        ) : null}
      </div>
    </section>
  )
}

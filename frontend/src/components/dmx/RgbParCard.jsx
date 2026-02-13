import DmxSlider from './DmxSlider.jsx'
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
  const redValue = readChannel(dmxValues, redChannel)
  const greenValue = readChannel(dmxValues, greenChannel)
  const blueValue = readChannel(dmxValues, blueChannel)
  const dimValue = readChannel(dmxValues, dimmerChannel)

  const selectedPreset =
    RGB_PRESETS.find((preset) => {
      const [red, green, blue] = preset.rgb
      if (preset.name === 'Off') {
        return redValue === 0 && greenValue === 0 && blueValue === 0 && dimValue === 0
      }
      return redValue === red && greenValue === green && blueValue === blue
    }) || null

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
        <div class="rgbPresetHeader">
          <span class="wheelRowLabel">Color Presets</span>
          <span class="muted">{selectedPreset ? selectedPreset.name : 'Custom'}</span>
        </div>
        <div class="rgbPresetGrid">
          {RGB_PRESETS.map((preset) => (
            <button
              key={`${fixture.id}-${preset.name}`}
              type="button"
              class={`rgbPresetButton ${selectedPreset?.name === preset.name ? 'rgbPresetButtonActive' : ''}`}
              style={{ '--preset-color': preset.swatch }}
              onClick={() => applyRgbPreset(preset)}
              title={preset.name}
              aria-pressed={selectedPreset?.name === preset.name}
            >
              <span>{preset.name}</span>
            </button>
          ))}
        </div>

        {redChannel ? (
          <DmxSlider
            label="Red"
            value={redValue}
            onInput={(value) => writeChannel(onDmxChange, redChannel, value)}
          />
        ) : null}
        {greenChannel ? (
          <DmxSlider
            label="Green"
            value={greenValue}
            onInput={(value) => writeChannel(onDmxChange, greenChannel, value)}
          />
        ) : null}
        {blueChannel ? (
          <DmxSlider
            label="Blue"
            value={blueValue}
            onInput={(value) => writeChannel(onDmxChange, blueChannel, value)}
          />
        ) : null}
        {strobeChannel ? (
          <DmxSlider
            label="Strobe"
            value={readChannel(dmxValues, strobeChannel)}
            onInput={(value) => writeChannel(onDmxChange, strobeChannel, value)}
          />
        ) : null}
        {dimmerChannel ? (
          <DmxSlider
            label="Dimmer"
            value={dimValue}
            onInput={(value) => writeChannel(onDmxChange, dimmerChannel, value)}
          />
        ) : null}
      </div>
    </section>
  )
}

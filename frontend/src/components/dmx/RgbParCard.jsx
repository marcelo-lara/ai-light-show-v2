import DmxSlider from './DmxSlider.jsx'
import EffectPreviewControls from './EffectPreviewControls.jsx'
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

export default function RgbParCard({ fixture, dmxValues, onDmxChange, onPreviewEffect, disabled = false }) {
  const channels = fixture?.channels || {}

  const redChannel = channels.red
  const greenChannel = channels.green
  const blueChannel = channels.blue
  const dimChannel = channels.dim
  const redValue = readChannel(dmxValues, redChannel)
  const greenValue = readChannel(dmxValues, greenChannel)
  const blueValue = readChannel(dmxValues, blueChannel)
  const dimValue = readChannel(dmxValues, dimChannel)

  const sliderChannels = Object.entries(channels).filter(
    ([channelName]) => !['red', 'green', 'blue'].includes(channelName)
  )

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

    if (dimChannel) {
      writeChannel(onDmxChange, dimChannel, preset.name === 'Off' ? 0 : 255)
    }
  }

  return (
    <section class="dmxCard">
      <header class="dmxCardHeader">
        <h3>{fixture?.name || 'RGB Fixture'}</h3>
        <button
          type="button"
          class="dmxArmButton"
          onClick={() => applyArmValues(fixture, onDmxChange)}
          disabled={disabled}
        >
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
              disabled={disabled}
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
            disabled={disabled}
          />
        ) : null}
        {greenChannel ? (
          <DmxSlider
            label="Green"
            value={greenValue}
            onInput={(value) => writeChannel(onDmxChange, greenChannel, value)}
            disabled={disabled}
          />
        ) : null}
        {blueChannel ? (
          <DmxSlider
            label="Blue"
            value={blueValue}
            onInput={(value) => writeChannel(onDmxChange, blueChannel, value)}
            disabled={disabled}
          />
        ) : null}
        {sliderChannels.map(([channelName, channelNum]) => (
          <DmxSlider
            key={`${fixture.id}-${channelName}`}
            label={channelName}
            value={readChannel(dmxValues, channelNum)}
            onInput={(value) => writeChannel(onDmxChange, channelNum, value)}
            disabled={disabled}
          />
        ))}

        <EffectPreviewControls
          fixture={fixture}
          disabled={disabled}
          onPreview={onPreviewEffect}
        />
      </div>
    </section>
  )
}

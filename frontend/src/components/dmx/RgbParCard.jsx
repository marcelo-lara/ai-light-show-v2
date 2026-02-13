import ChannelSlider from './ChannelSlider'
import { writeChannel, readChannel } from './dmxUtils'

const PRESETS = [
  { name: 'White', rgb: [255, 255, 255] },
  { name: 'Red', rgb: [255, 0, 0] },
  { name: 'Green', rgb: [0, 255, 0] },
  { name: 'Blue', rgb: [0, 0, 255] },
  { name: 'Cyan', rgb: [0, 255, 255] },
  { name: 'Magenta', rgb: [255, 0, 255] },
  { name: 'Yellow', rgb: [255, 255, 0] },
  { name: 'Off', rgb: [0, 0, 0] },
]

export default function RgbParCard({ fixture, dmxValues, onDmxChange }) {
  const ch = fixture.channels || {}
  const redCh = ch.red || ch.r
  const greenCh = ch.green || ch.g
  const blueCh = ch.blue || ch.b
  const strobeCh = ch.strobe
  const dimCh = ch.dimmer || ch.dim

  const handleArm = () => {
    const arm = fixture.arm || {}
    Object.keys(arm).forEach((k) => {
      const channelNum = fixture.channels?.[k]
      if (channelNum) onDmxChange(Number(channelNum), arm[k])
    })
  }

  const applyPreset = (rgb) => {
    if (redCh) writeChannel(onDmxChange, redCh, rgb[0])
    if (greenCh) writeChannel(onDmxChange, greenCh, rgb[1])
    if (blueCh) writeChannel(onDmxChange, blueCh, rgb[2])
  }

  return (
    <div class="dmxCard">
      <div class="dmxCardHeader">
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ fontWeight: 700 }}>{fixture.name}</div>
          <div class="muted">{fixture.type}</div>
        </div>
        <div>
          <button onClick={handleArm}>Arm</button>
        </div>
      </div>

      <div class="dmxCardBody">
        <div class="rgbPresetGrid">
          {PRESETS.map((p) => (
            <button class="rgbPresetButton" onClick={() => applyPreset(p.rgb)} style={{ background: `rgb(${p.rgb.join(',')})` }} aria-label={p.name} />
          ))}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {redCh ? <ChannelSlider label="Red" value={readChannel(dmxValues, redCh)} onInput={(v) => writeChannel(onDmxChange, redCh, v)} /> : null}
          {greenCh ? <ChannelSlider label="Green" value={readChannel(dmxValues, greenCh)} onInput={(v) => writeChannel(onDmxChange, greenCh, v)} /> : null}
          {blueCh ? <ChannelSlider label="Blue" value={readChannel(dmxValues, blueCh)} onInput={(v) => writeChannel(onDmxChange, blueCh, v)} /> : null}
          {strobeCh ? <ChannelSlider label="Strobe" value={readChannel(dmxValues, strobeCh)} onInput={(v) => writeChannel(onDmxChange, strobeCh, v)} /> : null}
          {dimCh ? <ChannelSlider label="Dimmer" value={readChannel(dmxValues, dimCh)} onInput={(v) => writeChannel(onDmxChange, dimCh, v)} /> : null}
        </div>
      </div>
    </div>
  )
}

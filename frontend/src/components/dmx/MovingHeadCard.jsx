import { useMemo } from 'preact/hooks'
import { compose16, split16, getWheelOptions, write16, readChannel, writeChannel } from './dmxUtils'
import XYPad from './XYPad'
import WheelButtonRow from './WheelButtonRow'
import ChannelSlider from './ChannelSlider'

export default function MovingHeadCard({ fixture, dmxValues, onDmxChange }) {
  const ch = fixture.channels || {}

  const pan16 = compose16(readChannel(dmxValues, ch.pan_msb), readChannel(dmxValues, ch.pan_lsb))
  const tilt16 = compose16(readChannel(dmxValues, ch.tilt_msb), readChannel(dmxValues, ch.tilt_lsb))

  const colorOptions = getWheelOptions(fixture, 'color')
  const goboOptions = getWheelOptions(fixture, 'gobo')

  const prismCh = ch.prism
  const strobeCh = ch.strobe
  const dimCh = ch.dimmer || ch.dim

  const handleArm = () => {
    const arm = fixture.arm || {}
    Object.keys(arm).forEach((k) => {
      const channelNum = fixture.channels?.[k]
      if (channelNum) onDmxChange(Number(channelNum), arm[k])
    })
  }

  const handlePoi = (preset) => {
    Object.entries(preset.values || {}).forEach(([k, v]) => {
      const channelNum = fixture.channels?.[k]
      if (channelNum) onDmxChange(Number(channelNum), v)
    })
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
      <div class="dmxCardBody movingHeadLayout">
        <div>
          <XYPad
            pan16={pan16}
            tilt16={tilt16}
            onChange={(p, t) => {
              write16(onDmxChange, ch.pan_msb, ch.pan_lsb, p)
              write16(onDmxChange, ch.tilt_msb, ch.tilt_lsb, t)
            }}
          />
          <div class="poiGrid">
            {(fixture.presets || []).map((p) => (
              <button class="wheelButton" onClick={() => handlePoi(p)}>{p.name}</button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <WheelButtonRow
            label="Color"
            channelNum={ch.color}
            valueMappings={colorOptions}
            currentValue={readChannel(dmxValues, ch.color)}
            onSelect={(v) => writeChannel(onDmxChange, ch.color, v)}
          />

          <WheelButtonRow
            label="Gobo"
            channelNum={ch.gobo}
            valueMappings={goboOptions}
            currentValue={readChannel(dmxValues, ch.gobo)}
            onSelect={(v) => writeChannel(onDmxChange, ch.gobo, v)}
          />

          {prismCh ? (
            <ChannelSlider label="Prism" value={readChannel(dmxValues, prismCh)} onInput={(v) => writeChannel(onDmxChange, prismCh, v)} />
          ) : null}

          {strobeCh ? (
            <ChannelSlider label="Strobe" value={readChannel(dmxValues, strobeCh)} onInput={(v) => writeChannel(onDmxChange, strobeCh, v)} />
          ) : null}

          {dimCh ? (
            <ChannelSlider label="Dimmer" value={readChannel(dmxValues, dimCh)} onInput={(v) => writeChannel(onDmxChange, dimCh, v)} />
          ) : null}
        </div>
      </div>
    </div>
  )
}

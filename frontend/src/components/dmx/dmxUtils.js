export function clampByte(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return 0
  return Math.max(0, Math.min(255, Math.round(num)))
}

export function clamp16(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return 0
  return Math.max(0, Math.min(65535, Math.round(num)))
}

export function readChannel(dmxValues, channelNum) {
  if (!Number.isFinite(Number(channelNum))) return 0
  return clampByte(dmxValues?.[channelNum] ?? 0)
}

export function writeChannel(onDmxChange, channelNum, value) {
  const channel = Number(channelNum)
  if (!Number.isFinite(channel) || channel <= 0) return
  onDmxChange?.(channel, clampByte(value))
}

export function compose16(msb, lsb) {
  return (clampByte(msb) << 8) | clampByte(lsb)
}

export function split16(value16) {
  const value = clamp16(value16)
  return {
    msb: (value >> 8) & 255,
    lsb: value & 255,
  }
}

export function write16(onDmxChange, msbChannel, lsbChannel, value16) {
  const { msb, lsb } = split16(value16)
  writeChannel(onDmxChange, msbChannel, msb)
  writeChannel(onDmxChange, lsbChannel, lsb)
}

export function getWheelOptions(fixture, wheelName) {
  const mapping = fixture?.meta?.value_mappings?.[wheelName]
  if (!mapping || typeof mapping !== 'object') return []

  return Object.entries(mapping)
    .map(([value, label]) => ({
      value: clampByte(value),
      label: String(label),
    }))
    .sort((a, b) => a.value - b.value)
}

export function applyArmValues(fixture, onDmxChange) {
  const arm = fixture?.arm
  const channels = fixture?.channels || {}
  if (!arm || typeof arm !== 'object') return

  for (const [channelName, value] of Object.entries(arm)) {
    writeChannel(onDmxChange, channels[channelName], value)
  }
}

export function applyPresetValues(fixture, preset, onDmxChange) {
  const presetValues = preset?.values
  const channels = fixture?.channels || {}
  if (!presetValues || typeof presetValues !== 'object') return

  for (const [channelName, value] of Object.entries(presetValues)) {
    writeChannel(onDmxChange, channels[channelName], value)
  }
}

export function clampByte(v) {
  const n = Number(v) || 0
  return Math.max(0, Math.min(255, Math.round(n)))
}

export function readChannel(dmxValues, channelNum) {
  if (!dmxValues) return 0
  return clampByte(dmxValues[channelNum] ?? 0)
}

export function writeChannel(onDmxChange, channelNum, value) {
  if (!channelNum) return
  onDmxChange(Number(channelNum), clampByte(value))
}

export function compose16(msb, lsb) {
  const a = Number(msb) || 0
  const b = Number(lsb) || 0
  return ((a & 0xff) << 8) | (b & 0xff)
}

export function split16(value16) {
  const v = Number(value16) || 0
  return { msb: (v >> 8) & 0xff, lsb: v & 0xff }
}

export function write16(onDmxChange, msbChannel, lsbChannel, value16) {
  const { msb, lsb } = split16(value16)
  if (msbChannel) onDmxChange(Number(msbChannel), msb)
  if (lsbChannel) onDmxChange(Number(lsbChannel), lsb)
}

export function getWheelOptions(fixture, wheelName) {
  const map = fixture?.meta?.value_mappings?.[wheelName] || {}
  const entries = Object.keys(map)
    .map((k) => ({ value: Number(k), label: map[k] }))
    .sort((a, b) => a.value - b.value)
  return entries
}

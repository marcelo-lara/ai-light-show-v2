const SUPPORTED_EFFECTS_BY_TYPE = {
  moving_head: ['set_channels', 'move_to', 'seek', 'strobe', 'full', 'flash', 'sweep'],
  parcan: ['set_channels', 'flash', 'strobe', 'fade_in', 'full'],
  rgb: ['set_channels', 'flash', 'strobe', 'fade_in', 'full'],
}

const RGB_FIELDS = [
  { key: 'red', label: 'Red', kind: 'int', min: 0, max: 255, step: 1, defaultValue: 255 },
  { key: 'green', label: 'Green', kind: 'int', min: 0, max: 255, step: 1, defaultValue: 255 },
  { key: 'blue', label: 'Blue', kind: 'int', min: 0, max: 255, step: 1, defaultValue: 255 },
]

const PARAM_SCHEMAS = {
  moving_head: {
    move_to: [
      { key: 'pan', label: 'Pan', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
      { key: 'tilt', label: 'Tilt', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
    ],
    seek: [
      { key: 'pan', label: 'Pan', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
      { key: 'tilt', label: 'Tilt', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
    ],
    sweep: [
      { key: 'pan', label: 'Center Pan', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
      { key: 'tilt', label: 'Center Tilt', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
      { key: 'span_pan', label: 'Span Pan', kind: 'int', min: -65535, max: 65535, step: 1, defaultValue: 20000 },
      { key: 'span_tilt', label: 'Span Tilt', kind: 'int', min: -65535, max: 65535, step: 1, defaultValue: 0 },
    ],
    strobe: [
      { key: 'rate', label: 'Rate Hz', kind: 'float', min: 0.1, max: 30.0, step: 0.1, defaultValue: 10.0 },
    ],
  },
  parcan: {
    strobe: [
      { key: 'rate', label: 'Rate Hz', kind: 'float', min: 0.1, max: 30.0, step: 0.1, defaultValue: 10.0 },
    ],
    fade_in: RGB_FIELDS,
    full: RGB_FIELDS,
  },
  rgb: {
    strobe: [
      { key: 'rate', label: 'Rate Hz', kind: 'float', min: 0.1, max: 30.0, step: 0.1, defaultValue: 10.0 },
    ],
    fade_in: RGB_FIELDS,
    full: RGB_FIELDS,
  },
}

function normalizeType(type) {
  return String(type || '').trim().toLowerCase()
}

export function getPreviewEffectsForFixture(fixture) {
  const fixtureType = normalizeType(fixture?.type)
  const supported = new Set(SUPPORTED_EFFECTS_BY_TYPE[fixtureType] || ['set_channels'])
  const declared = Array.isArray(fixture?.effects)
    ? fixture.effects.map((effect) => String(effect || '').trim().toLowerCase()).filter(Boolean)
    : []

  if (declared.length === 0) {
    return Array.from(supported)
  }

  return declared.filter((effect) => supported.has(effect))
}

export function getEffectParameterSchema(fixtureType, effect) {
  const normalizedType = normalizeType(fixtureType)
  const normalizedEffect = String(effect || '').trim().toLowerCase()
  return PARAM_SCHEMAS[normalizedType]?.[normalizedEffect] || []
}

export function effectLabel(effect) {
  const normalized = String(effect || '').trim().toLowerCase()
  if (!normalized) return 'Effect'
  return normalized
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

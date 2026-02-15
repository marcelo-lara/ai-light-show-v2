const SUPPORTED_EFFECTS_BY_TYPE = {
  moving_head: ['set_channels', 'move_to', 'move_to_poi', 'seek', 'strobe', 'full', 'flash', 'sweep'],
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
    move_to_poi: [{ key: 'target_POI', label: 'Target POI', kind: 'string', defaultValue: '' }],
    seek: [
      { key: 'pan', label: 'Pan', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
      { key: 'tilt', label: 'Tilt', kind: 'int', min: 0, max: 65535, step: 1, defaultValue: 32768 },
    ],
    sweep: [
      { key: 'subject_POI', label: 'Subject POI', kind: 'string', defaultValue: 'piano' },
      { key: 'start_POI', label: 'Start POI', kind: 'string', defaultValue: 'table' },
      { key: 'end_POI', label: 'End POI (optional)', kind: 'string', defaultValue: '' },
      { key: 'duration', label: 'Duration (s)', kind: 'float', min: 0.05, max: 30.0, step: 0.05, defaultValue: 1.0 },
      { key: 'max_dim', label: 'Max Dim (0-1)', kind: 'float', min: 0, max: 1, step: 0.01, defaultValue: 1.0 },
      { key: 'easing', label: 'Easing (s)', kind: 'float', min: 0, max: 10, step: 0.05, defaultValue: 0.0 },
      { key: 'arc_strength', label: 'Arc Strength', kind: 'float', min: -0.1, max: 0.1, step: 0.001, defaultValue: 0.015 },
      { key: 'subject_close_ratio', label: 'Subject close ratio', kind: 'float', min: 0.01, max: 1.0, step: 0.01, defaultValue: 0.1 },
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

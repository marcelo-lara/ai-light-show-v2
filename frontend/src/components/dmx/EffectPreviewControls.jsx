import { useEffect, useMemo, useState } from 'preact/hooks'
import {
  effectLabel,
  getEffectParameterSchema,
  getPreviewEffectsForFixture,
} from './effectPreviewConfig.js'

function buildInitialParamValues(schema) {
  const next = {}
  for (const field of schema) {
    next[field.key] = String(field.defaultValue ?? '')
  }
  return next
}

function parseFieldValue(rawValue, field) {
  if (rawValue === '' || rawValue === null || rawValue === undefined) {
    return null
  }

  if (field.kind === 'string') {
    const text = String(rawValue).trim()
    return text ? text : null
  }

  const parsed = field.kind === 'int' ? parseInt(rawValue, 10) : parseFloat(rawValue)
  if (!Number.isFinite(parsed)) {
    return null
  }

  if (field.kind === 'int') {
    return Math.round(parsed)
  }
  return parsed
}

function isPoiField(field) {
  return String(field?.key || '').endsWith('_POI')
}

function buildPoiOptions(fixture, pois) {
  const targets = fixture?.poi_targets && typeof fixture.poi_targets === 'object' ? fixture.poi_targets : {}
  const targetKeys = Object.keys(targets)
  const poisList = Array.isArray(pois) ? pois : []

  const byId = new Map()
  for (const poi of poisList) {
    const id = String(poi?.id || '').trim()
    if (!id || !(id in targets)) continue
    const name = String(poi?.name || '').trim()
    byId.set(id, name ? `${name} (${id})` : id)
  }
  for (const id of targetKeys) {
    if (!byId.has(id)) {
      byId.set(id, id)
    }
  }

  return Array.from(byId.entries())
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }))
}

export default function EffectPreviewControls({ fixture, pois, disabled, onPreview }) {
  const availableEffects = useMemo(() => getPreviewEffectsForFixture(fixture), [fixture])
  const [selectedEffect, setSelectedEffect] = useState(availableEffects[0] || '')
  const [durationText, setDurationText] = useState('1.0')
  const poiOptions = useMemo(() => buildPoiOptions(fixture, pois), [fixture, pois])

  useEffect(() => {
    setSelectedEffect((current) => {
      if (current && availableEffects.includes(current)) {
        return current
      }
      return availableEffects[0] || ''
    })
  }, [availableEffects])

  const parameterSchema = useMemo(
    () => getEffectParameterSchema(fixture?.type, selectedEffect),
    [fixture?.type, selectedEffect]
  )

  const [parameterValues, setParameterValues] = useState(() => buildInitialParamValues(parameterSchema))

  useEffect(() => {
    const initialValues = buildInitialParamValues(parameterSchema)

    for (const field of parameterSchema) {
      if (!isPoiField(field)) continue
      if (initialValues[field.key]) continue
      if (field.key === 'end_POI') continue
      if (poiOptions.length > 0) {
        initialValues[field.key] = poiOptions[0].value
      }
    }

    setParameterValues(initialValues)

    const durationField = parameterSchema.find((field) => field.key === 'duration')
    if (durationField) {
      setDurationText(String(durationField.defaultValue ?? '1.0'))
    }
  }, [selectedEffect, parameterSchema, poiOptions])

  if (availableEffects.length === 0) {
    return <div class="muted">No preview effects available for this fixture.</div>
  }

  const handlePreview = () => {
    let parsedDuration = parseFloat(durationText)
    if (!Number.isFinite(parsedDuration) || parsedDuration <= 0) {
      return
    }

    const payload = {}
    for (const field of parameterSchema) {
      const parsed = parseFieldValue(parameterValues[field.key], field)
      if (parsed !== null) {
        payload[field.key] = parsed
      }
    }

    if (Number.isFinite(payload.duration) && payload.duration > 0) {
      parsedDuration = payload.duration
    }

    onPreview?.({
      fixtureId: fixture?.id,
      effect: selectedEffect,
      duration: parsedDuration,
      data: payload,
    })
  }

  return (
    <div class="fxPreviewBlock">
      <div class="fxPreviewTopRow">
        <div class="fxPreviewMainInputs">
          <label class="fxField">
            <span class="fxFieldLabel">Effect</span>
            <select
              class="fxSelect"
              value={selectedEffect}
              onInput={(event) => setSelectedEffect(event.currentTarget.value)}
              disabled={disabled}
            >
              {availableEffects.map((effect) => (
                <option key={`${fixture?.id}-${effect}`} value={effect}>
                  {effectLabel(effect)}
                </option>
              ))}
            </select>
          </label>

          <label class="fxField fxDurationField">
            <span class="fxFieldLabel">Duration (s)</span>
            <input
              type="number"
              class="fxInput"
              min="0.05"
              step="0.1"
              value={durationText}
              onInput={(event) => setDurationText(event.currentTarget.value)}
              disabled={disabled}
            />
          </label>
        </div>

        <div class="fxPreviewParams">
          {parameterSchema.length === 0 ? (
            <div class="muted">No parameters</div>
          ) : (
            parameterSchema.map((field) => (
              <label class="fxField" key={`${selectedEffect}-${field.key}`}>
                <span class="fxFieldLabel">{field.label}</span>
                {isPoiField(field) ? (
                  <select
                    class="fxSelect"
                    value={parameterValues[field.key] ?? ''}
                    onInput={(event) => {
                      const nextValue = event.currentTarget.value
                      setParameterValues((previous) => ({
                        ...previous,
                        [field.key]: nextValue,
                      }))
                    }}
                    disabled={disabled}
                  >
                    {field.key === 'end_POI' ? <option value="">None</option> : null}
                    {poiOptions.map((option) => (
                      <option key={`${field.key}-${option.value}`} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={field.kind === 'string' ? 'text' : 'number'}
                    class="fxInput"
                    min={field.kind === 'string' ? undefined : field.min}
                    max={field.kind === 'string' ? undefined : field.max}
                    step={field.kind === 'string' ? undefined : field.step}
                    value={parameterValues[field.key] ?? ''}
                    onInput={(event) => {
                      const nextValue = event.currentTarget.value
                      setParameterValues((previous) => ({
                        ...previous,
                        [field.key]: nextValue,
                      }))
                    }}
                    disabled={disabled}
                  />
                )}
              </label>
            ))
          )}
        </div>
      </div>

      <button type="button" class="fxPreviewButton" onClick={handlePreview} disabled={disabled || !selectedEffect}>
        Preview
      </button>
    </div>
  )
}

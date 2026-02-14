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

  const parsed = field.kind === 'int' ? parseInt(rawValue, 10) : parseFloat(rawValue)
  if (!Number.isFinite(parsed)) {
    return null
  }

  if (field.kind === 'int') {
    return Math.round(parsed)
  }
  return parsed
}

export default function EffectPreviewControls({ fixture, disabled, onPreview }) {
  const availableEffects = useMemo(() => getPreviewEffectsForFixture(fixture), [fixture])
  const [selectedEffect, setSelectedEffect] = useState(availableEffects[0] || '')
  const [durationText, setDurationText] = useState('1.0')

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
    setParameterValues(buildInitialParamValues(parameterSchema))
  }, [selectedEffect, parameterSchema])

  if (availableEffects.length === 0) {
    return <div class="muted">No preview effects available for this fixture.</div>
  }

  const handlePreview = () => {
    const parsedDuration = parseFloat(durationText)
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
                <input
                  type="number"
                  class="fxInput"
                  min={field.min}
                  max={field.max}
                  step={field.step}
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

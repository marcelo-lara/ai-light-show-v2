function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

export default function CustomRangeSlider({
  min = 0,
  max = 255,
  step = 1,
  value = 0,
  onInput,
  ariaLabel = 'Range slider',
  showValue = true,
}) {
  const numericMin = Number(min)
  const numericMax = Number(max)
  const numericValue = clamp(Number(value) || 0, numericMin, numericMax)
  const percent =
    numericMax === numericMin
      ? 0
      : ((numericValue - numericMin) / (numericMax - numericMin)) * 100

  const handleInput = (e) => {
    onInput?.(Number(e.currentTarget.value))
  }

  return (
    <div class="customRangeSlider">
      <input
        class="customRangeSliderInput"
        type="range"
        min={numericMin}
        max={numericMax}
        step={step}
        value={numericValue}
        aria-label={ariaLabel}
        onInput={handleInput}
        style={{ '--slider-fill': `${percent}%` }}
      />
      {showValue && <div class="customRangeSliderValue">{numericValue}</div>}
    </div>
  )
}

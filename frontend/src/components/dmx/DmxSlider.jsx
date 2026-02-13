import CustomRangeSlider from '../ui/CustomRangeSlider.jsx'

export default function DmxSlider({ label, value, onInput, min = 0, max = 255, step = 1 }) {
  const numericValue = Number.isFinite(Number(value)) ? Math.round(Number(value)) : 0

  return (
    <div class="dmxSlider">
      <div class="dmxSliderLabel">{label}</div>
      <div class="dmxSliderControl">
        <CustomRangeSlider
          min={min}
          max={max}
          step={step}
          value={numericValue}
          onInput={onInput}
          ariaLabel={label}
          showValue={false}
        />
        <span class="dmxSliderValue">{numericValue}</span>
      </div>
    </div>
  )
}

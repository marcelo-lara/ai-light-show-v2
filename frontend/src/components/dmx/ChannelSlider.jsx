import CustomRangeSlider from '../ui/CustomRangeSlider'

export default function ChannelSlider({ label, value = 0, onInput, min = 0, max = 255 }) {
  const handle = (v) => onInput?.(v)
  return (
    <div class="sliderRow">
      <div style={{ width: '120px', fontSize: '13px', fontWeight: 600 }}>{label}</div>
      <div style={{ flex: 1 }}>
        <CustomRangeSlider
          min={min}
          max={max}
          value={value}
          onInput={handle}
          ariaLabel={label}
          showValue={false}
        />
      </div>
      <div style={{ width: '48px', textAlign: 'right', fontWeight: 700 }}>{value}</div>
    </div>
  )
}

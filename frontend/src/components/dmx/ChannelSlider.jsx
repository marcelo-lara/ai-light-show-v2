import CustomRangeSlider from '../ui/CustomRangeSlider.jsx'

export default function ChannelSlider({ label, value, onInput, channelNum, min = 0, max = 255 }) {
  return (
    <div class="sliderRow">
      <div class="sliderRowHeader">
        <span>{label}</span>
        {channelNum ? <span class="muted">Ch {channelNum}</span> : null}
      </div>
      <CustomRangeSlider
        min={min}
        max={max}
        value={value}
        onInput={onInput}
        ariaLabel={label}
        showValue={true}
      />
    </div>
  )
}

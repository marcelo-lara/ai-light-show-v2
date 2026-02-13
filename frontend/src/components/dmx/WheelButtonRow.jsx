export default function WheelButtonRow({ label, currentValue, options, onSelect }) {
  if (!Array.isArray(options) || options.length === 0) return null

  return (
    <div class="wheelRow">
      <div class="wheelRowLabel">{label}</div>
      <div class="wheelButtonGrid">
        {options.map((option) => {
          const active = Number(currentValue) === Number(option.value)
          return (
            <button
              type="button"
              key={`${label}-${option.value}`}
              class={`wheelButton ${active ? 'wheelButtonActive' : ''}`}
              onClick={() => onSelect?.(option.value)}
              title={`${option.label} (${option.value})`}
              aria-pressed={active}
            >
              {option.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

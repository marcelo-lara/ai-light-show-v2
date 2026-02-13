export default function WheelButtonRow({ label, currentValue, options, onSelect }) {
  if (!Array.isArray(options) || options.length === 0) return null

  const selected = options.find((option) => Number(option.value) === Number(currentValue))

  return (
    <div class="wheelRow">
      <div class="wheelRowHeader">
        <div class="wheelRowLabel">{label}</div>
        <div class="wheelRowValue muted">
          {selected ? `${selected.label} (${selected.value})` : `Value ${Number(currentValue) || 0}`}
        </div>
      </div>
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

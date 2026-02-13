import DmxSlider from './DmxSlider.jsx'
import MovingHeadCard from './MovingHeadCard.jsx'
import RgbParCard from './RgbParCard.jsx'
import { readChannel, writeChannel } from './dmxUtils.js'

function GenericFixtureCard({ fixture, dmxValues, onDmxChange }) {
  return (
    <section class="dmxCard">
      <header class="dmxCardHeader">
        <h3>{fixture?.name || 'Fixture'}</h3>
      </header>
      <div class="dmxCardBody">
        {Object.entries(fixture?.channels || {}).map(([channelName, channelNum]) => (
          <DmxSlider
            key={`${fixture.id}-${channelName}`}
            label={channelName}
            value={readChannel(dmxValues, channelNum)}
            onInput={(value) => writeChannel(onDmxChange, channelNum, value)}
          />
        ))}
      </div>
    </section>
  )
}

export default function DmxFixtureGrid({ fixtures, dmxValues, onDmxChange }) {
  if (!Array.isArray(fixtures) || fixtures.length === 0) {
    return <div class="dmxEmpty muted">No fixtures loaded.</div>
  }

  return (
    <div class="dmxGrid">
      {fixtures.map((fixture) => {
        if (fixture?.type === 'moving_head') {
          return (
            <MovingHeadCard
              key={fixture.id}
              fixture={fixture}
              dmxValues={dmxValues}
              onDmxChange={onDmxChange}
            />
          )
        }

        if (fixture?.type === 'rgb') {
          return (
            <RgbParCard
              key={fixture.id}
              fixture={fixture}
              dmxValues={dmxValues}
              onDmxChange={onDmxChange}
            />
          )
        }

        return (
          <GenericFixtureCard
            key={fixture?.id || fixture?.name}
            fixture={fixture}
            dmxValues={dmxValues}
            onDmxChange={onDmxChange}
          />
        )
      })}
    </div>
  )
}

import { useEffect, useState } from 'preact/hooks'

export default function PlayerPanel({ song, timecode, playing, onSeekTo, onTogglePlay }) {
  const [localTime, setLocalTime] = useState(timecode || 0)

  useEffect(() => setLocalTime(timecode || 0), [timecode])

  const fmt = (t) => {
    if (typeof t !== 'number') return '0.000'
    const mins = Math.floor(t / 60)
    const secs = (t % 60).toFixed(3).padStart(6, '0')
    return `${mins}:${secs}`
  }

  const handlePlayPause = () => {
    onTogglePlay?.()
  }

  const handleSeekClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = e.clientX - rect.left
    const pct = Math.max(0, Math.min(1, px / rect.width))
    if (onSeekTo) onSeekTo(pct * (song?.duration || 1))
  }

  const progressPct =
    song && song.duration ? Math.max(0, Math.min(100, (localTime / song.duration) * 100)) : 0

  return (
    <div class="playerPanel" role="region" aria-label="Show player">
      <div class="playerRow">
        <button
          class="playerButton"
          onClick={handlePlayPause}
          aria-pressed={playing}
          aria-label="Play/Pause"
        >
          {playing ? '❚❚' : '►'}
        </button>
        <div class="playerTitle">{song?.name || song?.filename || 'No song'}</div>
      </div>

      <div
        class="playerSeek"
        onClick={handleSeekClick}
        role="slider"
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div class="playerSeekProgress" style={{ width: `${progressPct}%` }} />
      </div>

      <div class="playerTime">
        {fmt(localTime)}
        {song?.duration ? ` | ${fmt(song.duration)}` : ''}
      </div>
    </div>
  )
}

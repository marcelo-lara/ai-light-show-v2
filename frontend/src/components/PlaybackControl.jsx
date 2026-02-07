import { h } from 'preact'
import { useState, useEffect } from 'preact/hooks'

export default function PlaybackControl({ song, timecode, playing, onSeek, onPlaybackChange }) {
  const [localTime, setLocalTime] = useState(timecode || 0)

  useEffect(() => setLocalTime(timecode || 0), [timecode])

  const fmt = (t) => {
    if (typeof t !== 'number') return '0.000'
    const mins = Math.floor(t / 60)
    const secs = (t % 60).toFixed(3).padStart(6, '0')
    return `${mins}:${secs}`
  }

  const handlePlayPause = () => {
    onPlaybackChange(!playing)
  }

  const handleSeekClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = e.clientX - rect.left
    const pct = Math.max(0, Math.min(1, px / rect.width))
    // Assume song length unknown; send relative seek (frontend will compute absolute if available)
    if (onSeek) onSeek(pct * (song?.duration || 1))
  }

  return (
    <div class="playbackControl" role="region" aria-label="Playback control">
      <div class="pcLeft">
        <button class="pcButton" onClick={handlePlayPause} aria-pressed={playing} aria-label="Play/Pause">
          {playing ? '❚❚' : '►'}
        </button>
        <div class="pcTitle">{song?.name || 'No song'}</div>
      </div>
      <div class="pcCenter" onClick={handleSeekClick} role="slider" aria-valuemin={0} aria-valuemax={100}>
        <div class="pcProgress" style={{ width: `${(song && song.duration) ? Math.max(0, Math.min(100, (localTime / song.duration) * 100)) : 0}%` }} />
      </div>
      <div class="pcRight">
        <div class="pcTime">{fmt(localTime)}{song?.duration ? ` | ${fmt(song.duration)}` : ''}</div>
      </div>
    </div>
  )
}

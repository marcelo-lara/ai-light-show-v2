import { useEffect, useRef } from 'preact/hooks'
import WaveSurfer from 'wavesurfer.js'

const TIME_TICK_HZ = 20

export default function WaveformHeader({
  song,
  onTimecodeUpdate,
  onSeek,
  onPlaybackChange,
  onRegisterAudioControls,
}) {
  const waveformRef = useRef(null)
  const wavesurferRef = useRef(null)
  const onTimecodeUpdateRef = useRef(onTimecodeUpdate)
  const onSeekRef = useRef(onSeek)
  const onPlaybackChangeRef = useRef(onPlaybackChange)
  const lastSentRef = useRef(0)
  const isPlayingRef = useRef(false)

  onTimecodeUpdateRef.current = onTimecodeUpdate
  onSeekRef.current = onSeek
  onPlaybackChangeRef.current = onPlaybackChange

  useEffect(() => {
    if (waveformRef.current && !wavesurferRef.current) {
      wavesurferRef.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#4a9eff',
        progressColor: '#1e5eff',
        height: 80,
        normalize: true,
      })

      onRegisterAudioControls?.({
        playPause: () => wavesurferRef.current?.playPause?.(),
        seekTo: (time) => {
          const ws = wavesurferRef.current
          if (!ws) return

          if (typeof ws.setTime === 'function') {
            ws.setTime(time)
            return
          }

          // Fallback: if setTime isn't available, approximate with seekTo percent.
          const duration = typeof ws.getDuration === 'function' ? ws.getDuration() : 0
          if (duration > 0 && typeof ws.seekTo === 'function') {
            ws.seekTo(Math.max(0, Math.min(1, time / duration)))
          }
        },
      })

      const emitTime = () => {
        const ws = wavesurferRef.current
        if (!ws) return
        if (!isPlayingRef.current) return
        const currentTime = ws.getCurrentTime()
        const now = performance.now()
        const minDeltaMs = 1000 / TIME_TICK_HZ
        if (now - lastSentRef.current < minDeltaMs) return
        lastSentRef.current = now
        onTimecodeUpdateRef.current?.(currentTime)
      }

      const emitSeek = () => {
        const ws = wavesurferRef.current
        if (!ws) return
        const currentTime = ws.getCurrentTime()
        lastSentRef.current = performance.now()
        onSeekRef.current?.(currentTime)
      }

      wavesurferRef.current.on('audioprocess', emitTime)
      wavesurferRef.current.on('timeupdate', emitTime)
      wavesurferRef.current.on('seek', emitSeek)

      wavesurferRef.current.on('play', () => {
        isPlayingRef.current = true
        onPlaybackChangeRef.current?.(true)
      })
      wavesurferRef.current.on('pause', () => {
        isPlayingRef.current = false
        onPlaybackChangeRef.current?.(false)
      })
    }

    return () => {
      onRegisterAudioControls?.(null)
      if (wavesurferRef.current) {
        wavesurferRef.current.destroy()
        wavesurferRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (song && wavesurferRef.current) {
      const rawUrl = song.url || song.audioUrl
      const url = rawUrl?.startsWith('/') ? rawUrl : rawUrl

      if (url) {
        wavesurferRef.current.load(url)
      }
    }
  }, [song])

  return (
    <div class="waveHeader">
      <div class="waveTitle muted">{song ? song.filename : 'No song loaded'}</div>
      <div ref={waveformRef} class="waveform"></div>
    </div>
  )
}

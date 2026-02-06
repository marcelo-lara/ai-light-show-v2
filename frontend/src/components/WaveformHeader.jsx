import { useEffect, useRef } from 'preact/hooks'
import WaveSurfer from 'wavesurfer.js'

const TIME_TICK_HZ = 20

export default function WaveformHeader({ song, onTimecodeUpdate, onSeek, onPlaybackChange, onLoadSong }) {
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
      console.log('[WaveSurfer] init: container present', {
        hasContainer: !!waveformRef.current,
        width: waveformRef.current?.clientWidth,
        height: waveformRef.current?.clientHeight,
      })
      wavesurferRef.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#4a9eff',
        progressColor: '#1e5eff',
        height: 80,
        normalize: true,
      })

      wavesurferRef.current.on('ready', () => {
        console.log('[WaveSurfer] ready', {
          duration: wavesurferRef.current?.getDuration?.(),
        })
      })

      wavesurferRef.current.on('error', (err) => {
        console.log('[WaveSurfer] error', err)
      })

      wavesurferRef.current.on('loading', (progress) => {
        console.log('[WaveSurfer] loading', progress)
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

      // Use multiple events for broad compatibility across WaveSurfer versions.
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
      if (wavesurferRef.current) {
        wavesurferRef.current.destroy()
        wavesurferRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (song && wavesurferRef.current) {
      console.log('[WaveSurfer] load song', {
        filename: song?.filename,
        song,
      })
      // If a URL is ever provided by the backend, load it.
      // This keeps WaveSurfer initialized properly even when no audio endpoint exists yet.
      const rawUrl = song.url || song.audioUrl

      // nginx proxies /songs/ requests to the backend, so use relative URLs
      const url = rawUrl?.startsWith('/') ? rawUrl : rawUrl

      if (url) {
        console.log('[WaveSurfer] load url', url)
        wavesurferRef.current.load(url)
      } else {
        console.log('[WaveSurfer] no url provided for song')
      }
    }
  }, [song])

  const handlePlayPause = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause()
    }
  }

  const handleLoadSong = () => {
    const filename = prompt('Enter song filename (without extension):')
    if (filename) {
      onLoadSong(filename)
    }
  }

  return (
    <div class="waveHeader">
      <div class="waveControls">
        <button onClick={handleLoadSong}>Load Song</button>
        <button onClick={handlePlayPause}>Play/Pause</button>
        <div class="waveTitle muted">{song ? song.filename : 'No song loaded'}</div>
      </div>
      <div ref={waveformRef} class="waveform"></div>
    </div>
  )
}
import { useEffect, useRef } from 'preact/hooks'
import WaveSurfer from 'wavesurfer.js'

export default function WaveformHeader({ song, onTimecodeUpdate, onLoadSong }) {
  const waveformRef = useRef(null)
  const wavesurferRef = useRef(null)

  useEffect(() => {
    if (waveformRef.current && !wavesurferRef.current) {
      wavesurferRef.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#4a9eff',
        progressColor: '#1e5eff',
        height: 80,
        responsive: true,
      })

      wavesurferRef.current.on('ready', () => {
        console.log('WaveSurfer ready')
      })

      wavesurferRef.current.on('audioprocess', () => {
        const currentTime = wavesurferRef.current.getCurrentTime()
        onTimecodeUpdate(currentTime)
      })

      wavesurferRef.current.on('seek', () => {
        const currentTime = wavesurferRef.current.getCurrentTime()
        onTimecodeUpdate(currentTime)
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
      // Load song from backend API (assuming /api/song/{filename})
      // For now, placeholder
      console.log('Load song:', song.filename)
      // wavesurferRef.current.load(`/api/song/${song.filename}`)
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
    <div style={{ padding: '10px', borderBottom: '1px solid #333', background: '#252526' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
        <button onClick={handleLoadSong}>Load Song</button>
        <button onClick={handlePlayPause}>Play/Pause</button>
        <span>{song ? song.filename : 'No song loaded'}</span>
      </div>
      <div ref={waveformRef} style={{ width: '100%' }}></div>
    </div>
  )
}
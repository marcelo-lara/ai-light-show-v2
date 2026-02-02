import { useState, useEffect, useRef } from 'preact/hooks'
import WaveformHeader from './components/WaveformHeader.jsx'
import SongPartsLane from './components/SongPartsLane.jsx'
import CueSheetLane from './components/CueSheetLane.jsx'
import FixturesLane from './components/FixturesLane.jsx'
import ChatSidePanel from './components/ChatSidePanel.jsx'

export function App() {
  const [fixtures, setFixtures] = useState([])
  const [cues, setCues] = useState([])
  const [song, setSong] = useState(null)
  const [dmxValues, setDmxValues] = useState({})
  const [timecode, setTimecode] = useState(0)
  const wsRef = useRef(null)
  const isPlayingRef = useRef(false)

  useEffect(() => {
    // Connect to WebSocket
    const wsUrl =
      import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000/ws`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'initial') {
        setFixtures(data.fixtures || [])
        setCues(data.cues?.entries || [])
        setSong(data.song)
        isPlayingRef.current = !!data.playback?.isPlaying
      } else if (data.type === 'delta') {
        setDmxValues(prev => ({ ...prev, [data.channel]: data.value }))
      } else if (data.type === 'dmx_frame') {
        // Backend sends full-frame snapshots only for paused seek-preview / initialization.
        // Never animate sliders during playback.
        if (isPlayingRef.current) return
        const values = Array.isArray(data.values) ? data.values : []
        const next = {}
        for (let i = 0; i < values.length; i++) {
          next[i + 1] = values[i]
        }
        setDmxValues(next)
        if (typeof data.time === 'number') {
          setTimecode(data.time)
        }
      } else if (data.type === 'cues_updated') {
        setCues(data.cues?.entries || [])
      }
    }

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }

    return () => {
      ws.close()
    }
  }, [])

  const sendMessage = (message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }

  const handleDmxChange = (channel, value) => {
    setDmxValues(prev => ({ ...prev, [channel]: value }))
    sendMessage({ type: 'delta', channel, value })
  }

  const handleLoadSong = (filename) => {
    sendMessage({ type: 'load_song', filename })
  }

  const handleTimecodeUpdate = (time) => {
    setTimecode(time)
    sendMessage({ type: 'timecode', time })
  }

  const handleSeek = (time) => {
    setTimecode(time)
    sendMessage({ type: 'seek', time })
  }

  const handlePlaybackChange = (playing) => {
    isPlayingRef.current = !!playing
    sendMessage({ type: 'playback', playing })
  }

  return (
    <div class="appRoot">
      <div class="mainColumn">
        <WaveformHeader
          song={song}
          onTimecodeUpdate={handleTimecodeUpdate}
          onSeek={handleSeek}
          onPlaybackChange={handlePlaybackChange}
          onLoadSong={handleLoadSong}
        />
        <div class="lanesGrid">
          <SongPartsLane song={song} timecode={timecode} />
          <CueSheetLane cues={cues} timecode={timecode} />
          <FixturesLane fixtures={fixtures} dmxValues={dmxValues} onDmxChange={handleDmxChange} timecode={timecode} />
        </div>
      </div>
      <ChatSidePanel onSendMessage={(msg) => sendMessage({ type: 'chat', message: msg })} />
    </div>
  )
}
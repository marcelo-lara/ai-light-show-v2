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

  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws')
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'initial') {
        setFixtures(data.fixtures || [])
        setCues(data.cues?.entries || [])
        setSong(data.song)
      } else if (data.type === 'delta') {
        setDmxValues(prev => ({ ...prev, [data.channel]: data.value }))
      } else if (data.type === 'cue_added') {
        setCues(prev => [...prev, data.entry])
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

  const handleAddCue = (timecode, name) => {
    sendMessage({ type: 'add_cue', time: timecode, name })
  }

  const handleLoadSong = (filename) => {
    sendMessage({ type: 'load_song', filename })
  }

  const handleTimecodeUpdate = (time) => {
    setTimecode(time)
    sendMessage({ type: 'timecode', time })
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#1e1e1e', color: 'white' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <WaveformHeader
          song={song}
          onTimecodeUpdate={handleTimecodeUpdate}
          onLoadSong={handleLoadSong}
        />
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <SongPartsLane song={song} timecode={timecode} />
          <CueSheetLane cues={cues} timecode={timecode} />
          <FixturesLane
            fixtures={fixtures}
            dmxValues={dmxValues}
            onDmxChange={handleDmxChange}
            onAddCue={handleAddCue}
            timecode={timecode}
          />
        </div>
      </div>
      <ChatSidePanel onSendMessage={(msg) => sendMessage({ type: 'chat', message: msg })} />
    </div>
  )
}
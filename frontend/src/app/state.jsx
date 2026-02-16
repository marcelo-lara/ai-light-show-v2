import { createContext } from 'preact'
import { useContext, useEffect, useMemo, useRef, useState } from 'preact/hooks'

const AppStateContext = createContext(null)

export function AppStateProvider({ children }) {
  const [fixtures, setFixtures] = useState([])
  const [cues, setCues] = useState([])
  const [song, setSong] = useState(null)
  const [dmxValues, setDmxValues] = useState({})
  const [timecode, setTimecode] = useState(0)
  const [playing, setPlaying] = useState(false)

  const wsRef = useRef(null)
  const isPlayingRef = useRef(false)
  const audioControlsRef = useRef(null)

  useEffect(() => {
    const wsUrl =
      import.meta.env.VITE_WS_URL || `${window.location.origin.replace(/^http/, 'ws')}/ws`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'initial') {
        setFixtures(data.fixtures || [])
        setCues(data.cues?.entries || [])
        setSong(data.song)
        isPlayingRef.current = !!data.playback?.isPlaying
        setPlaying(!!data.playback?.isPlaying)
      } else if (data.type === 'delta') {
        setDmxValues((prev) => ({ ...prev, [data.channel]: data.value }))
      } else if (data.type === 'dmx_frame') {
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
    setDmxValues((prev) => ({ ...prev, [channel]: value }))
    sendMessage({ type: 'delta', channel, value })
  }

  const handleTimecodeUpdate = (time) => {
    setTimecode(time)
    sendMessage({ type: 'timecode', time })
  }

  const handleSeek = (time) => {
    setTimecode(time)
    sendMessage({ type: 'seek', time })
  }

  const handlePlaybackChange = (nextPlaying) => {
    isPlayingRef.current = !!nextPlaying
    setPlaying(!!nextPlaying)
    sendMessage({ type: 'playback', playing: nextPlaying })
  }

  const registerAudioControls = (controls) => {
    audioControlsRef.current = controls
  }

  const togglePlay = () => {
    const controls = audioControlsRef.current
    if (controls?.playPause) {
      controls.playPause()
      return
    }
    handlePlaybackChange(!playing)
  }

  const seekTo = (time) => {
    const controls = audioControlsRef.current
    if (controls?.seekTo) {
      controls.seekTo(time)
      return
    }
    handleSeek(time)
  }

  const value = useMemo(
    () => ({
      fixtures,
      cues,
      song,
      dmxValues,
      timecode,
      playing,
      sendMessage,
      actions: {
        handleDmxChange,
        handleTimecodeUpdate,
        handleSeek,
        handlePlaybackChange,
        registerAudioControls,
        togglePlay,
        seekTo,
      },
    }),
    [fixtures, cues, song, dmxValues, timecode, playing]
  )

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
}

export function useAppState() {
  const ctx = useContext(AppStateContext)
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider')
  return ctx
}

import { createContext } from 'preact'
import { useContext, useEffect, useMemo, useRef, useState } from 'preact/hooks'

const AppStateContext = createContext(null)

export function AppStateProvider({ children }) {
  const [fixtures, setFixtures] = useState([])
  const [pois, setPois] = useState([])
  const [cues, setCues] = useState([])
  const [song, setSong] = useState(null)
  const [dmxValues, setDmxValues] = useState({})
  const [timecode, setTimecode] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [status, setStatus] = useState({ isPlaying: false, previewActive: false, preview: null })
  const [previewStatus, setPreviewStatus] = useState({ active: false, requestId: null, reason: null })

  const [analysis, setAnalysis] = useState({
    taskId: null,
    state: null,
    meta: null,
    result: null,
    error: null,
    updatedAt: null,
  })

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
        setPois(data.pois || [])
        setCues(data.cues?.entries || [])
        setSong(data.song)
        const nextStatus = data.status || {
          isPlaying: !!data.playback?.isPlaying,
          previewActive: false,
          preview: null,
        }
        isPlayingRef.current = !!nextStatus.isPlaying
        setPlaying(!!nextStatus.isPlaying)
        setStatus(nextStatus)
      } else if (data.type === 'delta') {
        setDmxValues((prev) => ({ ...prev, [data.channel]: data.value }))
      } else if (data.type === 'status') {
        const nextStatus = data.status || { isPlaying: false, previewActive: false, preview: null }
        isPlayingRef.current = !!nextStatus.isPlaying
        setPlaying(!!nextStatus.isPlaying)
        setStatus(nextStatus)
      } else if (data.type === 'preview_status') {
        setPreviewStatus({
          active: !!data.active,
          requestId: data.request_id || null,
          reason: data.reason || null,
        })
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
      } else if (data.type === 'fixtures_updated') {
        setFixtures(data.fixtures || [])
      } else if (data.type === 'task_submitted') {
        setAnalysis((prev) => ({
          ...prev,
          taskId: data.task_id || null,
          state: 'SUBMITTED',
          meta: null,
          result: null,
          error: null,
          updatedAt: Date.now(),
        }))
      } else if (data.type === 'analyze_progress') {
        setAnalysis((prev) => ({
          ...prev,
          taskId: data.task_id || prev.taskId || null,
          state: data.state || prev.state || null,
          meta: data.meta || null,
          error: null,
          updatedAt: Date.now(),
        }))
      } else if (data.type === 'analyze_result') {
        setAnalysis((prev) => ({
          ...prev,
          taskId: data.task_id || prev.taskId || null,
          state: data.state || 'SUCCESS',
          result: data.result ?? null,
          updatedAt: Date.now(),
        }))
      } else if (data.type === 'task_error') {
        setAnalysis((prev) => ({
          ...prev,
          taskId: data.task_id || prev.taskId || null,
          state: 'ERROR',
          error: data.message || 'Unknown error',
          updatedAt: Date.now(),
        }))
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
    if (isPlayingRef.current) return
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

  const handlePreviewEffect = ({ fixtureId, effect, duration, data }) => {
    if (isPlayingRef.current) return

    const requestId =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`

    sendMessage({
      type: 'preview_effect',
      request_id: requestId,
      fixture_id: fixtureId,
      effect,
      duration,
      data: data || {},
    })
  }

  const handleSavePoiTarget = ({ fixtureId, poiId, pan16, tilt16 }) => {
    sendMessage({
      type: 'save_poi_target',
      fixture_id: fixtureId,
      poi_id: poiId,
      pan: pan16,
      tilt: tilt16,
    })
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
      pois,
      cues,
      song,
      dmxValues,
      timecode,
      playing,
      analysis,
      status,
      previewStatus,
      sendMessage,
      actions: {
        handleDmxChange,
        handleTimecodeUpdate,
        handleSeek,
        handlePlaybackChange,
        handlePreviewEffect,
        handleSavePoiTarget,
        registerAudioControls,
        togglePlay,
        seekTo,
      },
    }),
    [fixtures, pois, cues, song, dmxValues, timecode, playing, analysis, status, previewStatus]
  )

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
}

export function useAppState() {
  const ctx = useContext(AppStateContext)
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider')
  return ctx
}

import { useEffect, useRef } from 'preact/hooks'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js'

const TIME_TICK_HZ = 20
const ZOOM_MIN = 20
const ZOOM_MAX = 240
const ZOOM_STEP = 20
const ANALYZER_BINS = 64

function createSilentWavBlob(durationSeconds, sampleRate = 8000) {
  const safeDuration = Math.max(1, Math.floor(Number(durationSeconds) || 1))
  const safeRate = Math.max(8000, Math.floor(Number(sampleRate) || 8000))
  const numChannels = 1
  const bitsPerSample = 16
  const bytesPerSample = bitsPerSample / 8
  const numSamples = safeDuration * safeRate
  const dataSize = numSamples * numChannels * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  const writeString = (offset, text) => {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, safeRate, true)
  view.setUint32(28, safeRate * numChannels * bytesPerSample, true)
  view.setUint16(32, numChannels * bytesPerSample, true)
  view.setUint16(34, bitsPerSample, true)
  writeString(36, 'data')
  view.setUint32(40, dataSize, true)

  return new Blob([buffer], { type: 'audio/wav' })
}

export default function WaveformHeader({
  song,
  onTimecodeUpdate,
  onSeek,
  onPlaybackChange,
  onRegisterAudioControls,
  sectionRegions = [],
  regionsEditable = false,
  onSectionRegionsChange,
}) {
  const waveformRef = useRef(null)
  const wavesurferRef = useRef(null)
  const regionsPluginRef = useRef(null)
  const analyzerCanvasRef = useRef(null)
  const audioContextRef = useRef(null)
  const analyzerNodeRef = useRef(null)
  const sourceNodeRef = useRef(null)
  const analyzerAnimationRef = useRef(0)
  const syncingRegionsRef = useRef(false)
  const syncReleaseTimerRef = useRef(0)
  const usedSilentFallbackRef = useRef(false)
  const mediaReadyRef = useRef(false)
  const mediaFallbackTimerRef = useRef(0)
  const onTimecodeUpdateRef = useRef(onTimecodeUpdate)
  const onSeekRef = useRef(onSeek)
  const onPlaybackChangeRef = useRef(onPlaybackChange)
  const onSectionRegionsChangeRef = useRef(onSectionRegionsChange)
  const lastSentRef = useRef(0)
  const isPlayingRef = useRef(false)
  const zoomLevelRef = useRef(0)

  onTimecodeUpdateRef.current = onTimecodeUpdate
  onSeekRef.current = onSeek
  onPlaybackChangeRef.current = onPlaybackChange
  onSectionRegionsChangeRef.current = onSectionRegionsChange

  useEffect(() => {
    if (waveformRef.current && !wavesurferRef.current) {
      wavesurferRef.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#4a9eff',
        progressColor: '#1e5eff',
        height: 80,
        normalize: true,
      })

      regionsPluginRef.current = wavesurferRef.current.registerPlugin(
        RegionsPlugin.create()
      )

      if (typeof window !== 'undefined') {
        window.__waveformTestHooks = {
          getRegionCount: () => {
            const plugin = regionsPluginRef.current
            if (!plugin || typeof plugin.getRegions !== 'function') return 0
            return plugin.getRegions().length
          },
          getRegions: () => {
            const plugin = regionsPluginRef.current
            if (!plugin || typeof plugin.getRegions !== 'function') return []
            return plugin
              .getRegions()
              .map((region) => ({
                id: String(region.id),
                start: Number(region.start),
                end: Number(region.end),
              }))
          },
          nudgeFirstRegion: (deltaSeconds = 0.5) => {
            const plugin = regionsPluginRef.current
            if (!plugin || typeof plugin.getRegions !== 'function') return false
            const regions = plugin.getRegions()
            if (!regions.length) return false
            const first = regions.slice().sort((a, b) => Number(a.start) - Number(b.start))[0]
            const delta = Number(deltaSeconds) || 0
            const nextStart = Math.max(0, Number(first.start) + delta)
            const nextEnd = Math.max(nextStart + 0.01, Number(first.end) + delta)
            if (typeof first.setOptions === 'function') {
              first.setOptions({ start: nextStart, end: nextEnd })
              return true
            }
            first.start = nextStart
            first.end = nextEnd
            if (typeof plugin.emit === 'function') {
              plugin.emit('region-updated', first)
            }
            return true
          },
        }
      }

      const emitRegions = () => {
        if (syncingRegionsRef.current) return
        const plugin = regionsPluginRef.current
        if (!plugin) return

        const nextRegions = plugin
          .getRegions()
          .map((region) => ({
            id: String(region.id),
            name: String(region.content?.textContent || region.id || ''),
            start: Number(region.start),
            end: Number(region.end),
          }))
          .filter((region) => Number.isFinite(region.start) && Number.isFinite(region.end) && region.end > region.start)
          .sort((a, b) => a.start - b.start)

        onSectionRegionsChangeRef.current?.(nextRegions)
      }

      regionsPluginRef.current.on('region-updated', emitRegions)
      regionsPluginRef.current.on('region-removed', emitRegions)
      regionsPluginRef.current.on('region-clicked', (region, event) => {
        event?.stopPropagation?.()
        const time = Number(region.start)
        if (!Number.isFinite(time)) return

        const ws = wavesurferRef.current
        if (ws && typeof ws.setTime === 'function') ws.setTime(time)
        onSeekRef.current?.(time)
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
      wavesurferRef.current.on('error', () => {
        const ws = wavesurferRef.current
        if (!ws || usedSilentFallbackRef.current) return

        const lengthHint = Number(song?.metadata?.length) || 180
        const silentBlob = createSilentWavBlob(lengthHint)
        usedSilentFallbackRef.current = true
        if (typeof ws.loadBlob === 'function') {
          ws.loadBlob(silentBlob)
        }
      })

      wavesurferRef.current.on('ready', () => {
        mediaReadyRef.current = true
        if (mediaFallbackTimerRef.current) {
          window.clearTimeout(mediaFallbackTimerRef.current)
          mediaFallbackTimerRef.current = 0
        }

        const ws = wavesurferRef.current
        const canvas = analyzerCanvasRef.current
        if (!ws || !canvas) return

        const media = typeof ws.getMediaElement === 'function' ? ws.getMediaElement() : null
        if (!media) return

        if (!audioContextRef.current) {
          const AudioContextCtor = window.AudioContext || window.webkitAudioContext
          if (!AudioContextCtor) return
          audioContextRef.current = new AudioContextCtor()
        }

        const audioContext = audioContextRef.current
        if (!analyzerNodeRef.current) {
          const analyzer = audioContext.createAnalyser()
          analyzer.fftSize = 256
          analyzer.smoothingTimeConstant = 0.8
          analyzerNodeRef.current = analyzer
        }

        if (!sourceNodeRef.current) {
          const source = audioContext.createMediaElementSource(media)
          source.connect(analyzerNodeRef.current)
          analyzerNodeRef.current.connect(audioContext.destination)
          sourceNodeRef.current = source
        }

        const analyzer = analyzerNodeRef.current
        const data = new Uint8Array(analyzer.frequencyBinCount)
        const draw = () => {
          const canvasNode = analyzerCanvasRef.current
          if (!canvasNode) return

          const ctx = canvasNode.getContext('2d')
          if (!ctx) return

          const width = canvasNode.clientWidth
          const height = canvasNode.clientHeight
          if (canvasNode.width !== width || canvasNode.height !== height) {
            canvasNode.width = width
            canvasNode.height = height
          }

          analyzer.getByteFrequencyData(data)

          ctx.clearRect(0, 0, width, height)
          ctx.fillStyle = '#101010'
          ctx.fillRect(0, 0, width, height)

          const bins = Math.min(ANALYZER_BINS, data.length)
          const gap = 1
          const barWidth = Math.max(1, Math.floor((width - gap * (bins - 1)) / bins))

          for (let i = 0; i < bins; i += 1) {
            const value = data[i] / 255
            const barHeight = Math.max(1, Math.floor(value * (height - 2)))
            const x = i * (barWidth + gap)
            const y = height - barHeight

            const isDownRange = i % 8 === 0
            ctx.fillStyle = isDownRange ? '#7b7fff' : '#4a9eff'
            ctx.fillRect(x, y, barWidth, barHeight)
          }

          analyzerAnimationRef.current = requestAnimationFrame(draw)
        }

        if (analyzerAnimationRef.current) {
          cancelAnimationFrame(analyzerAnimationRef.current)
        }
        draw()
      })
    }

    return () => {
      if (typeof window !== 'undefined' && window.__waveformTestHooks) {
        delete window.__waveformTestHooks
      }
      onRegisterAudioControls?.(null)
      if (analyzerAnimationRef.current) {
        cancelAnimationFrame(analyzerAnimationRef.current)
        analyzerAnimationRef.current = 0
      }
      if (mediaFallbackTimerRef.current) {
        window.clearTimeout(mediaFallbackTimerRef.current)
        mediaFallbackTimerRef.current = 0
      }
      if (syncReleaseTimerRef.current) {
        window.clearTimeout(syncReleaseTimerRef.current)
        syncReleaseTimerRef.current = 0
      }
      if (audioContextRef.current && typeof audioContextRef.current.close === 'function') {
        audioContextRef.current.close().catch(() => {})
        audioContextRef.current = null
      }
      analyzerNodeRef.current = null
      sourceNodeRef.current = null
      regionsPluginRef.current = null
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
      usedSilentFallbackRef.current = false
      mediaReadyRef.current = false

      if (url) {
        zoomLevelRef.current = 0
        if (typeof wavesurferRef.current.zoom === 'function') {
          wavesurferRef.current.zoom(0)
        }
        wavesurferRef.current.load(url)

        if (mediaFallbackTimerRef.current) {
          window.clearTimeout(mediaFallbackTimerRef.current)
        }
        mediaFallbackTimerRef.current = window.setTimeout(() => {
          const ws = wavesurferRef.current
          if (!ws || mediaReadyRef.current || usedSilentFallbackRef.current) return
          if (typeof ws.loadBlob === 'function') {
            const lengthHint = Number(song?.metadata?.length) || 180
            ws.loadBlob(createSilentWavBlob(lengthHint))
            usedSilentFallbackRef.current = true
          }
          mediaFallbackTimerRef.current = 0
        }, 1200)
      } else if (typeof wavesurferRef.current.loadBlob === 'function') {
        const lengthHint = Number(song?.metadata?.length) || 180
        wavesurferRef.current.loadBlob(createSilentWavBlob(lengthHint))
        usedSilentFallbackRef.current = true
      }
    }
  }, [song])

  useEffect(() => {
    const plugin = regionsPluginRef.current
    if (!plugin) return

    syncingRegionsRef.current = true
    plugin.clearRegions()

    sectionRegions.forEach((region, index) => {
      const start = Number(region.start)
      const end = Number(region.end)
      if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return

      plugin.addRegion({
        id: String(region.id || `${region.name}-${index}`),
        start,
        end,
        drag: !!regionsEditable,
        resize: !!regionsEditable,
        content: String(region.name || `Section ${index + 1}`),
        color: index % 2 === 0 ? 'rgba(74, 158, 255, 0.22)' : 'rgba(30, 94, 255, 0.18)',
      })
    })

    if (syncReleaseTimerRef.current) {
      window.clearTimeout(syncReleaseTimerRef.current)
    }
    syncReleaseTimerRef.current = window.setTimeout(() => {
      syncingRegionsRef.current = false
      syncReleaseTimerRef.current = 0
    }, 0)
  }, [sectionRegions, regionsEditable])

  const zoomIn = () => {
    const ws = wavesurferRef.current
    if (!ws || typeof ws.zoom !== 'function') return

    const next = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoomLevelRef.current + ZOOM_STEP))
    zoomLevelRef.current = next
    ws.zoom(next)
  }

  const zoomOut = () => {
    const ws = wavesurferRef.current
    if (!ws || typeof ws.zoom !== 'function') return

    const current = zoomLevelRef.current || ZOOM_MIN
    const next = Math.max(0, current - ZOOM_STEP)
    zoomLevelRef.current = next
    ws.zoom(next)
  }

  return (
    <div class="waveHeader">
      <div class="waveControls">
        <div class="waveTitle muted">{song ? song.filename : 'No song loaded'}</div>
        <div class="waveZoomControls">
          <button class="waveZoomButton" type="button" onClick={zoomOut} aria-label="Zoom out waveform">
            −
          </button>
          <button class="waveZoomButton" type="button" onClick={zoomIn} aria-label="Zoom in waveform">
            +
          </button>
        </div>
      </div>
      <div ref={waveformRef} class="waveform"></div>
      <canvas ref={analyzerCanvasRef} class="waveAnalyzerCanvas" aria-label="Audio visualizer"></canvas>
    </div>
  )
}

import { useMemo } from 'preact/hooks'

import { useAppState } from '../app/state.jsx'
import WaveformHeader from '../components/player/WaveformHeader.jsx'

function normalizeSongFilename(filename) {
  if (!filename) return ''
  return filename.endsWith('.mp3') ? filename.slice(0, -4) : filename
}

function computeProgressPercent(meta) {
  if (!meta || typeof meta !== 'object') return 0

  const numericProgress = Number(meta.progress ?? meta.percent ?? meta.pct)
  if (Number.isFinite(numericProgress)) {
    if (numericProgress > 1) return Math.max(0, Math.min(100, numericProgress))
    return Math.max(0, Math.min(100, numericProgress * 100))
  }

  const index = Number(meta.index)
  const total = Number(meta.total)
  if (Number.isFinite(index) && Number.isFinite(total) && total > 0) {
    return Math.max(0, Math.min(100, (index / total) * 100))
  }

  return 0
}

function collectNumericArray(...candidates) {
  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      const values = candidate
        .map((value) => Number(value))
        .filter((value) => Number.isFinite(value))
      if (values.length) return values
    }
  }
  return []
}

function chunk(values, size = 4) {
  const rows = []
  for (let i = 0; i < values.length; i += size) {
    rows.push(values.slice(i, i + size))
  }
  return rows
}

function toLabel(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value.toFixed(3)
  }
  return String(value)
}

function getSectionMarkers(parts) {
  if (!parts || typeof parts !== 'object') return []

  const markers = []
  for (const [name, times] of Object.entries(parts)) {
    if (!Array.isArray(times)) continue
    for (const time of times) {
      const numericTime = Number(time)
      if (!Number.isFinite(numericTime)) continue
      markers.push({ label: name, time: numericTime })
    }
  }

  return markers.sort((a, b) => a.time - b.time)
}

function findSectionTargets(markers, timecode) {
  if (!markers.length) return { prev: null, next: null }

  let currentIndex = -1
  for (let i = 0; i < markers.length; i++) {
    if (markers[i].time <= timecode) currentIndex = i
    else break
  }

  const prev = currentIndex > 0 ? markers[currentIndex - 1] : markers[0]
  const next = currentIndex >= 0 ? markers[currentIndex + 1] || null : markers[0]
  return { prev, next }
}

function findBeatTargets(beats, timecode) {
  if (!beats.length) return { prev: null, next: null }

  let currentIndex = -1
  for (let i = 0; i < beats.length; i++) {
    if (beats[i] <= timecode) currentIndex = i
    else break
  }

  const prev = currentIndex > 0 ? beats[currentIndex - 1] : beats[0]
  const next = currentIndex >= 0 ? beats[currentIndex + 1] ?? null : beats[0]
  return { prev, next }
}

function windowAround(values, timecode, count = 12) {
  if (!values.length) return []

  let nearestIndex = 0
  let nearestDelta = Math.abs(values[0] - timecode)

  for (let i = 1; i < values.length; i++) {
    const delta = Math.abs(values[i] - timecode)
    if (delta < nearestDelta) {
      nearestDelta = delta
      nearestIndex = i
    }
  }

  const half = Math.floor(count / 2)
  const start = Math.max(0, nearestIndex - half)
  const end = Math.min(values.length, start + count)
  return values.slice(start, end)
}

export default function SongAnalysisPage() {
  const { song, analysis, timecode, playing, sendMessage, actions } = useAppState()

  const sectionMarkers = useMemo(() => getSectionMarkers(song?.metadata?.parts), [song])

  const beats = useMemo(
    () =>
      collectNumericArray(
        analysis?.result?.downbeats,
        analysis?.result?.beats,
        song?.metadata?.hints?.downbeats,
        song?.metadata?.hints?.beats,
        song?.metadata?.drums?.downbeats,
        song?.metadata?.drums?.beats
      ),
    [analysis, song]
  )

  const beatWindow = useMemo(() => windowAround(beats, timecode, 12), [beats, timecode])

  const chordValues = useMemo(() => {
    const raw = analysis?.result?.chords
    if (!Array.isArray(raw)) return []

    return raw
      .map((entry) => {
        if (typeof entry === 'string') return entry
        if (entry && typeof entry === 'object') {
          return entry.label || entry.chord || entry.name || null
        }
        return null
      })
      .filter(Boolean)
      .slice(0, 12)
  }, [analysis])

  const sectionTargets = useMemo(
    () => findSectionTargets(sectionMarkers, timecode),
    [sectionMarkers, timecode]
  )
  const beatTargets = useMemo(() => findBeatTargets(beats, timecode), [beats, timecode])

  const progressPercent = computeProgressPercent(analysis?.meta)
  const progressLabel = `${Math.round(progressPercent)}%`
  const analysisState = analysis?.state || 'IDLE'
  const analysisStep = analysis?.meta?.step || analysis?.meta?.status || 'Waiting'
  const canStart = !!song?.filename && analysisState !== 'PENDING' && analysisState !== 'STARTED'

  const startAnalysis = () => {
    const filename = normalizeSongFilename(song?.filename)
    if (!filename) return
    sendMessage({ type: 'analyze_song', filename, overwrite: true })
  }

  return (
    <div class="page songAnalysisPage">
      <div class="pageHeader">
        <h2>Song Analysis</h2>
        <div class="muted">Analyze song structure and timing markers, then navigate sections and beats quickly.</div>
      </div>

      <div class="pageBody songAnalysisBody">
        <WaveformHeader
          song={song}
          onTimecodeUpdate={actions.handleTimecodeUpdate}
          onSeek={actions.handleSeek}
          onPlaybackChange={actions.handlePlaybackChange}
          onRegisterAudioControls={actions.registerAudioControls}
        />

        <div class="songAnalysisToolbar card">
          <div class="songAnalysisControlGroup">
            <button
              class="songAnalysisButton"
              onClick={() => sectionTargets.prev && actions.seekTo(sectionTargets.prev.time)}
              disabled={!sectionTargets.prev}
              type="button"
            >
              Prev Section
            </button>
            <button
              class="songAnalysisButton"
              onClick={() => beatTargets.prev != null && actions.seekTo(beatTargets.prev)}
              disabled={beatTargets.prev == null}
              type="button"
            >
              Prev Beat
            </button>
            <button class="songAnalysisButton" onClick={actions.togglePlay} type="button">
              {playing ? 'Stop' : 'Play'}
            </button>
            <button
              class="songAnalysisButton"
              onClick={() => beatTargets.next != null && actions.seekTo(beatTargets.next)}
              disabled={beatTargets.next == null}
              type="button"
            >
              Next Beat
            </button>
            <button
              class="songAnalysisButton"
              onClick={() => sectionTargets.next && actions.seekTo(sectionTargets.next.time)}
              disabled={!sectionTargets.next}
              type="button"
            >
              Next Section
            </button>
          </div>

          <div class="songAnalysisProgressWrap">
            <button
              class="songAnalysisButton"
              onClick={startAnalysis}
              disabled={!canStart}
              type="button"
            >
              Start Analysis
            </button>
            <div class="songAnalysisProgressBlock">
              <div class="songAnalysisProgressLabel muted">
                <span>{analysisStep}</span>
                <span>{progressLabel}</span>
              </div>
              <div class="songAnalysisProgressTrack" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(progressPercent)}>
                <div class="songAnalysisProgressFill" style={{ width: `${progressPercent}%` }}></div>
              </div>
            </div>
          </div>
        </div>

        <div class="songAnalysisGrid">
          <div class="card songAnalysisCard">
            <div class="cardTitle">Downbeats / Beats</div>
            <div class="songAnalysisBeatGrid">
              {chunk(beatWindow, 4).length ? (
                chunk(beatWindow, 4).map((row, rowIndex) => (
                  <div class="songAnalysisBeatRow" key={`row-${rowIndex}`}>
                    {row.map((value, valueIndex) => (
                      <button
                        key={`${value}-${valueIndex}`}
                        class="songAnalysisBeatCell"
                        type="button"
                        onClick={() => actions.seekTo(value)}
                      >
                        {toLabel(value)}
                      </button>
                    ))}
                  </div>
                ))
              ) : (
                <div class="muted">No beat markers available.</div>
              )}
            </div>
          </div>

          <div class="card songAnalysisCard">
            <div class="cardTitle">Sections</div>
            <div class="songAnalysisTagList">
              {sectionMarkers.length ? (
                sectionMarkers.slice(0, 18).map((marker, index) => (
                  <button
                    key={`${marker.label}-${marker.time}-${index}`}
                    class="songAnalysisTag"
                    type="button"
                    onClick={() => actions.seekTo(marker.time)}
                  >
                    <span>{marker.label}</span>
                    <span>{toLabel(marker.time)}</span>
                  </button>
                ))
              ) : (
                <div class="muted">No section markers available.</div>
              )}
            </div>
          </div>

          <div class="card songAnalysisCard">
            <div class="cardTitle">Analysis Status</div>
            <div class="songAnalysisMetaList">
              <div>
                <span class="muted">Song:</span> {song?.filename || 'None'}
              </div>
              <div>
                <span class="muted">State:</span> {analysisState}
              </div>
              <div>
                <span class="muted">Task ID:</span> {analysis?.taskId || '—'}
              </div>
              <div>
                <span class="muted">Updated:</span>{' '}
                {analysis?.updatedAt ? new Date(analysis.updatedAt).toLocaleTimeString() : '—'}
              </div>
              {analysis?.error ? <div class="songAnalysisError">{analysis.error}</div> : null}
            </div>

            <div class="cardTitle">Chords</div>
            <div class="songAnalysisChordGrid">
              {chordValues.length ? (
                chordValues.map((chord, index) => (
                  <div class="songAnalysisChordCell" key={`${chord}-${index}`}>
                    {chord}
                  </div>
                ))
              ) : (
                <div class="muted">No chord data available.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

import { useEffect, useMemo, useRef, useState } from 'preact/hooks'

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

function parseSections(parts) {
  if (!parts || typeof parts !== 'object') return []

  const sections = []
  for (const [name, times] of Object.entries(parts)) {
    if (!Array.isArray(times) || !times.length) continue
    const numeric = times.map((value) => Number(value)).filter((value) => Number.isFinite(value))
    if (!numeric.length) continue

    const start = numeric[0]
    const end = numeric.length >= 2 ? numeric[1] : numeric[0]
    sections.push({
      id: `${name}-${start}-${end}`,
      name,
      start,
      end,
    })
  }

  return sections.sort((a, b) => a.start - b.start)
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

function buildBeatEntries(downbeats, beats) {
  const markDownbeats = new Set(downbeats.map((value) => Number(value).toFixed(6)))
  const merged = Array.from(new Set([...downbeats, ...beats]))
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))
    .sort((a, b) => a - b)

  return merged.map((time) => ({
    time,
    isDownbeat: markDownbeats.has(Number(time).toFixed(6)),
  }))
}

export default function SongAnalysisPage() {
  const { song, analysis, timecode, playing, sendMessage, actions } = useAppState()
  const beatsPanelRef = useRef(null)
  const sectionListRef = useRef(null)
  const [visibleBeatCount, setVisibleBeatCount] = useState(0)
  const [sectionDraft, setSectionDraft] = useState([])
  const [sectionError, setSectionError] = useState('')
  const [sectionsDirty, setSectionsDirty] = useState(false)

  const sectionMarkers = useMemo(() => getSectionMarkers(song?.metadata?.parts), [song])
  const sections = useMemo(() => parseSections(song?.metadata?.parts), [song])
  const effectiveSectionDraft = useMemo(() => {
    if (sectionDraft.length) return sectionDraft
    return sections.map((section, index) => ({
      id: section.id || `section-${index}`,
      name: section.name,
      start: String(section.start),
      end: String(section.end),
    }))
  }, [sectionDraft, sections])
  const sectionRegions = useMemo(
    () =>
      effectiveSectionDraft
        .map((entry, index) => {
          const start = Number(entry.start)
          const end = Number(entry.end)
          if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null
          return {
            id: String(entry.id || `section-${index}`),
            name: String(entry.name || `Section ${index + 1}`),
            start,
            end,
          }
        })
        .filter(Boolean)
        .sort((a, b) => a.start - b.start),
      [effectiveSectionDraft]
  )

  const downbeats = useMemo(
    () =>
      collectNumericArray(
        song?.metadata?.hints?.downbeats,
        song?.metadata?.drums?.downbeats,
        analysis?.result?.downbeats
      ),
    [analysis, song]
  )

  const beats = useMemo(
    () =>
      collectNumericArray(
        song?.metadata?.hints?.beats,
        song?.metadata?.drums?.beats,
        analysis?.result?.beats
      ),
    [analysis, song]
  )

  const beatEntries = useMemo(() => buildBeatEntries(downbeats, beats), [downbeats, beats])
  const effectiveVisibleBeatCount =
    visibleBeatCount > 0 ? visibleBeatCount : Math.min(40, beatEntries.length)
  const visibleBeatEntries = useMemo(
    () => beatEntries.slice(0, Math.max(effectiveVisibleBeatCount, 0)),
    [beatEntries, effectiveVisibleBeatCount]
  )
  const currentBeatIndex = useMemo(() => {
    if (!beatEntries.length) return -1

    let low = 0
    let high = beatEntries.length - 1
    let result = -1

    while (low <= high) {
      const mid = Math.floor((low + high) / 2)
      if (beatEntries[mid].time <= timecode) {
        result = mid
        low = mid + 1
      } else {
        high = mid - 1
      }
    }

    return result < 0 ? 0 : result
  }, [beatEntries, timecode])

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
  const beatPhasePercent = useMemo(() => {
    const prev = beatTargets.prev
    const next = beatTargets.next
    if (prev == null || next == null) return 0

    const span = Number(next) - Number(prev)
    if (!Number.isFinite(span) || span <= 0) return 0

    const offset = Number(timecode) - Number(prev)
    if (!Number.isFinite(offset)) return 0
    return Math.max(0, Math.min(100, (offset / span) * 100))
  }, [beatTargets, timecode])
  const barBeatLabel = useMemo(() => {
    if (!beats.length || !downbeats.length) return '—.—'

    let downbeatIndex = -1
    for (let i = 0; i < downbeats.length; i++) {
      if (downbeats[i] <= timecode) downbeatIndex = i
      else break
    }

    const bar = downbeatIndex >= 0 ? downbeatIndex + 1 : 1
    const barStart = downbeatIndex >= 0 ? downbeats[downbeatIndex] : downbeats[0]
    const nextBarStart = downbeats[downbeatIndex + 1] ?? Number.POSITIVE_INFINITY

    let beat = 0
    for (let i = 0; i < beats.length; i++) {
      const value = beats[i]
      if (value < barStart) continue
      if (value >= nextBarStart) break
      if (value <= timecode) beat += 1
      else break
    }

    return `${bar}.${Math.max(1, beat)}`
  }, [beats, downbeats, timecode])
  const activeSectionId = useMemo(() => {
    if (!effectiveSectionDraft.length) return null

    const normalized = effectiveSectionDraft
      .map((entry) => ({
        id: entry.id,
        start: Number(entry.start),
        end: Number(entry.end),
      }))
      .filter((entry) => Number.isFinite(entry.start) && Number.isFinite(entry.end) && entry.end > entry.start)
      .sort((a, b) => a.start - b.start)

    if (!normalized.length) return null

    const containing = normalized.find((entry) => timecode >= entry.start && timecode < entry.end)
    if (containing) return containing.id

    let latest = null
    for (const entry of normalized) {
      if (entry.start <= timecode) latest = entry
      else break
    }

    return latest?.id || normalized[0]?.id || null
  }, [effectiveSectionDraft, timecode])

  useEffect(() => {
    setSectionDraft(
      sections.map((section, index) => ({
        id: section.id || `section-${index}`,
        name: section.name,
        start: String(section.start),
        end: String(section.end),
      }))
    )
    setSectionsDirty(false)
    setSectionError('')
  }, [sections])

  useEffect(() => {
    setVisibleBeatCount(Math.min(Math.max(beatEntries.length, 0), 40))
  }, [song?.filename, beatEntries.length])

  useEffect(() => {
    const panel = beatsPanelRef.current
    if (!panel || !beatEntries.length) return

    const ensureFilled = () => {
      const rowHeight = 34
      const rowsToFill = Math.max(3, Math.ceil(panel.clientHeight / rowHeight))
      const itemsNeeded = rowsToFill * 4
      setVisibleBeatCount((prev) => Math.min(beatEntries.length, Math.max(prev, itemsNeeded)))
    }

    ensureFilled()
    window.addEventListener('resize', ensureFilled)
    return () => window.removeEventListener('resize', ensureFilled)
  }, [beatEntries.length])

  useEffect(() => {
    if (currentBeatIndex < 0) return
    const required = currentBeatIndex + 16
    setVisibleBeatCount((prev) => Math.min(beatEntries.length, Math.max(prev, required)))
  }, [currentBeatIndex, beatEntries.length])

  useEffect(() => {
    if (!playing || !activeSectionId) return
    const container = sectionListRef.current
    if (!container) return
    const activeRow = container.querySelector(`[data-section-id="${activeSectionId}"]`)
    if (!activeRow) return

    const rowTop = activeRow.offsetTop
    const rowBottom = rowTop + activeRow.offsetHeight
    const viewTop = container.scrollTop
    const viewBottom = viewTop + container.clientHeight

    if (rowTop < viewTop || rowBottom > viewBottom) {
      const target = Math.max(0, rowTop - Math.floor(container.clientHeight * 0.35))
      container.scrollTop = target
    }
  }, [activeSectionId, playing])

  const loadMoreBeats = () => {
    if (visibleBeatCount >= beatEntries.length) return
    setVisibleBeatCount((prev) => Math.min(beatEntries.length, prev + 40))
  }

  const handleBeatScroll = (event) => {
    const node = event.currentTarget
    const remaining = node.scrollHeight - node.scrollTop - node.clientHeight
    if (remaining < 120) loadMoreBeats()
  }

  const markSectionsDirty = () => {
    setSectionsDirty(true)
    setSectionError('')
  }

  const addSectionRow = () => {
    markSectionsDirty()
    setSectionDraft((prev) => {
      const next = [
        ...prev,
        {
          id: `new-${Date.now()}-${prev.length}`,
          name: '',
          start: String(Number(timecode).toFixed(3)),
          end: String(Number((timecode || 0) + 8).toFixed(3)),
        },
      ]
      return next
    })
  }

  const updateSectionField = (id, field, value) => {
    markSectionsDirty()
    setSectionDraft((prev) => prev.map((entry) => (entry.id === id ? { ...entry, [field]: value } : entry)))
  }

  const removeSectionRow = (id) => {
    markSectionsDirty()
    setSectionDraft((prev) => prev.filter((entry) => entry.id !== id))
  }

  const setSectionTimeFromPlayback = (id, field) => {
    updateSectionField(id, field, Number(timecode).toFixed(3))
  }

  const normalizeSectionsForSave = () => {
    const normalized = []

    for (const row of effectiveSectionDraft) {
      const name = String(row.name || '').trim()
      const start = Number(row.start)
      const end = Number(row.end)

      if (!name) return { ok: false, message: 'Section name is required.' }
      if (!Number.isFinite(start) || !Number.isFinite(end)) {
        return { ok: false, message: `Section "${name}" has invalid start/end.` }
      }
      if (end <= start) {
        return { ok: false, message: `Section "${name}" must have end > start.` }
      }

      normalized.push({
        name,
        start,
        end,
      })
    }

    normalized.sort((a, b) => a.start - b.start)

    for (let i = 1; i < normalized.length; i++) {
      if (normalized[i].start < normalized[i - 1].end) {
        return {
          ok: false,
          message: `Sections overlap: "${normalized[i - 1].name}" and "${normalized[i].name}".`,
        }
      }
    }

    return { ok: true, sections: normalized }
  }

  const saveSections = () => {
    const normalized = normalizeSectionsForSave()
    if (!normalized.ok) {
      setSectionError(normalized.message)
      return
    }

    sendMessage({
      type: 'save_sections',
      sections: normalized.sections,
    })
    setSectionsDirty(false)
    setSectionError('')
  }

  const handleRegionsChange = (regions) => {
    if (!Array.isArray(regions) || regions.length === 0) return
    markSectionsDirty()
    setSectionDraft((prev) => {
      const byId = new Map(prev.map((entry) => [String(entry.id), entry]))
      const next = regions.map((region, index) => {
        const existing = byId.get(String(region.id))
        return {
          id: String(region.id || `region-${index}`),
          name: String(region.name || existing?.name || `Section ${index + 1}`),
          start: Number(region.start).toFixed(3),
          end: Number(region.end).toFixed(3),
        }
      })
      return next
    })
  }

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
          sectionRegions={sectionRegions}
          regionsEditable
          onSectionRegionsChange={handleRegionsChange}
        />

        <div class="songAnalysisToolbar card">
          <div class="songAnalysisBeatBarWrap">
            <div class="songAnalysisBeatBarLabel muted">
              <span>Beat Bar</span>
              <span>{barBeatLabel}</span>
            </div>
            <div class="songAnalysisBeatBarTrack" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(beatPhasePercent)}>
              <div class="songAnalysisBeatBarFill" style={{ width: `${beatPhasePercent}%` }}></div>
            </div>
          </div>

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
            <div
              class="songAnalysisBeatGrid"
              ref={beatsPanelRef}
              onScroll={handleBeatScroll}
            >
              {chunk(visibleBeatEntries, 4).length ? (
                chunk(visibleBeatEntries, 4).map((row, rowIndex) => (
                  <div class="songAnalysisBeatRow" key={`row-${rowIndex}`}>
                    {row.map((value, valueIndex) => (
                      <button
                        key={`${value.time}-${valueIndex}`}
                        class={`songAnalysisBeatCell ${value.isDownbeat ? 'songAnalysisBeatCellDownbeat' : ''} ${valueIndex + rowIndex * 4 === currentBeatIndex ? 'songAnalysisBeatCellCurrent' : ''}`}
                        type="button"
                        onClick={() => actions.seekTo(value.time)}
                      >
                        {value.isDownbeat ? 'D ' : 'B '}
                        {toLabel(value.time)}
                      </button>
                    ))}
                  </div>
                ))
              ) : (
                <div class="muted">No beat markers available.</div>
              )}
              {visibleBeatCount < beatEntries.length ? (
                <div class="muted">Scroll to load more…</div>
              ) : null}
            </div>
          </div>

          <div class="card songAnalysisCard">
            <div class="cardTitle">Sections</div>
            <div class="songAnalysisSectionActions">
              <button class="songAnalysisButton" type="button" onClick={addSectionRow}>
                Add Section
              </button>
              <button class="songAnalysisButton" type="button" onClick={saveSections} disabled={!sectionsDirty}>
                Save Sections
              </button>
            </div>
            {sectionError ? <div class="songAnalysisError">{sectionError}</div> : null}
            <div class="songAnalysisSectionList" ref={sectionListRef}>
              {effectiveSectionDraft.length ? (
                effectiveSectionDraft.map((section) => (
                  <div
                    class={`songAnalysisSectionRow ${section.id === activeSectionId ? 'songAnalysisSectionRowActive' : ''}`}
                    key={section.id}
                    data-section-id={section.id}
                  >
                    <input
                      class="songAnalysisSectionInput"
                      value={section.name}
                      onInput={(event) => updateSectionField(section.id, 'name', event.currentTarget.value)}
                      placeholder="Name"
                    />
                    <input
                      class="songAnalysisSectionInput"
                      type="number"
                      step="0.001"
                      value={section.start}
                      onInput={(event) => updateSectionField(section.id, 'start', event.currentTarget.value)}
                      placeholder="Start"
                    />
                    <input
                      class="songAnalysisSectionInput"
                      type="number"
                      step="0.001"
                      value={section.end}
                      onInput={(event) => updateSectionField(section.id, 'end', event.currentTarget.value)}
                      placeholder="End"
                    />
                    <button class="songAnalysisButton" type="button" onClick={() => setSectionTimeFromPlayback(section.id, 'start')}>
                      Set Start
                    </button>
                    <button class="songAnalysisButton" type="button" onClick={() => setSectionTimeFromPlayback(section.id, 'end')}>
                      Set End
                    </button>
                    <button class="songAnalysisButton" type="button" onClick={() => actions.seekTo(Number(section.start) || 0)}>
                      Go
                    </button>
                    <button class="songAnalysisButton" type="button" onClick={() => removeSectionRow(section.id)}>
                      Delete
                    </button>
                  </div>
                ))
              ) : (
                <div class="muted">No sections available.</div>
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

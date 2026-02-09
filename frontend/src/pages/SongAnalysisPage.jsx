import { useMemo } from 'preact/hooks'

import { useAppState } from '../app/state.jsx'

export default function SongAnalysisPage() {
  const { song, analysis, sendMessage } = useAppState()

  const songFilename = song?.filename

  const progressPct = useMemo(() => {
    const raw = analysis?.meta?.progress
    if (typeof raw === 'number' && Number.isFinite(raw)) return Math.max(0, Math.min(100, raw))
    return null
  }, [analysis?.meta])

  const isRunning = analysis?.state && !['SUCCESS', 'FAILURE', 'REVOKED', 'ERROR'].includes(analysis.state)

  const canStart = !!songFilename && !isRunning

  const startAnalysis = () => {
    if (!songFilename) return
    sendMessage({ type: 'analyze_song', filename: songFilename })
  }

  return (
    <div class="page">
      <div class="pageHeader">
        <h2>Song Analysis</h2>
        <div class="muted">Pick a song, request analysis, review plots + metadata.</div>
      </div>
      <div class="pageBody">
        <div class="card">
          <div class="cardTitle">Start analysis</div>
          <div class="muted">Current song: {songFilename || 'No song loaded'}</div>

          <div style="margin-top:10px; display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
            <button type="button" onClick={startAnalysis} disabled={!canStart} aria-disabled={!canStart}>
              Start analysis
            </button>
            {!songFilename ? (
              <div class="muted">Load a song to enable analysis.</div>
            ) : null}
          </div>

          <div style="margin-top:12px; display:grid; gap:8px;">
            <div class="muted">
              Status: {analysis?.state || 'idle'}
              {analysis?.taskId ? ` (task ${analysis.taskId})` : ''}
            </div>

            {typeof progressPct === 'number' ? (
              <div>
                <div class="playerSeek" style="height:10px;">
                  <div class="playerSeekProgress" style={{ width: `${progressPct}%` }} />
                </div>
                <div class="muted" style="margin-top:6px;">
                  Progress: {progressPct}%
                  {analysis?.meta?.step ? ` • ${analysis.meta.step}` : ''}
                  {analysis?.meta?.status ? ` • ${analysis.meta.status}` : ''}
                </div>
              </div>
            ) : null}

            {analysis?.error ? <div class="muted">Error: {analysis.error}</div> : null}
          </div>
        </div>
      </div>
    </div>
  )
}

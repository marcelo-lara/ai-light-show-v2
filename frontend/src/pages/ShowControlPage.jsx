import { useAppState } from '../app/state.jsx'

import WaveformHeader from '../components/player/WaveformHeader.jsx'
import SongPartsLane from '../components/lanes/SongPartsLane.jsx'
import CueSheetLane from '../components/lanes/CueSheetLane.jsx'
import FixturesLane from '../components/lanes/FixturesLane.jsx'

export default function ShowControlPage() {
  const { fixtures, cues, song, dmxValues, timecode, actions, status } = useAppState()

  return (
    <div class="showControlPage">
      <div class="mainColumn">
        <WaveformHeader
          song={song}
          onTimecodeUpdate={actions.handleTimecodeUpdate}
          onSeek={actions.handleSeek}
          onPlaybackChange={actions.handlePlaybackChange}
          onRegisterAudioControls={actions.registerAudioControls}
        />
        <div class="lanesGrid">
          <SongPartsLane song={song} timecode={timecode} onSeek={actions.seekTo} />
          <CueSheetLane cues={cues} timecode={timecode} />
          <FixturesLane
            fixtures={fixtures}
            dmxValues={dmxValues}
            onDmxChange={actions.handleDmxChange}
            onPreviewEffect={actions.handlePreviewEffect}
            isPlaybackActive={!!status?.isPlaying}
          />
        </div>
      </div>
    </div>
  )
}

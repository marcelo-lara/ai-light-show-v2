import { useAppState } from '../app/state.jsx'

import PlayerPanel from '../components/player/PlayerPanel.jsx'
import ChatSidePanel from '../components/chat/ChatSidePanel.jsx'

export default function RightPanel() {
  const { song, timecode, playing, sendMessage, actions } = useAppState()

  return (
    <div class="rightPanelInner">

      <div class="rightPanelChat">
        <ChatSidePanel onSendMessage={(msg) => sendMessage({ type: 'chat', message: msg })} />
      </div>

      <div class="rightPanelPlayer">
        <PlayerPanel
          song={song}
          timecode={timecode}
          playing={playing}
          onSeekTo={actions.seekTo}
          onTogglePlay={actions.togglePlay}
        />
      </div>

    </div>
  )
}

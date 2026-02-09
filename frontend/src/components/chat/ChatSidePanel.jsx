import { useEffect, useRef, useState } from 'preact/hooks'

export default function ChatSidePanel({ onSendMessage }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages.length])

  const handleSend = () => {
    if (input.trim()) {
      setMessages((prev) => [...prev, { text: input, from: 'user' }])
      onSendMessage(input)
      setInput('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSend()
    }
  }

  return (
    <div class="chatPanel">
      <div class="chatHeader">
        <h3>LLM Chat</h3>
      </div>

      <div class="chatMessages">
        {messages.length === 0 ? (
          <div class="muted">Send a message to start.</div>
        ) : (
          messages.map((msg, index) => (
            <div
              key={index}
              style={{ marginBottom: '10px', textAlign: msg.from === 'user' ? 'right' : 'left' }}
            >
              <div
                style={{
                  display: 'inline-block',
                  padding: '6px 10px',
                  background: msg.from === 'user' ? '#4a9eff' : '#333',
                  borderRadius: '10px',
                  maxWidth: '85%',
                }}
              >
                {msg.text}
              </div>
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>

      <div class="chatComposer">
        <input
          class="chatInput"
          type="text"
          value={input}
          onInput={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
        />
        <button class="chatSendButton" type="button" onClick={handleSend} aria-label="Send">
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M3.4 20.6 21 12 3.4 3.4l.3 6.2L15.7 12 3.7 14.4l-.3 6.2z" fill="currentColor" />
          </svg>
        </button>
      </div>
    </div>
  )
}

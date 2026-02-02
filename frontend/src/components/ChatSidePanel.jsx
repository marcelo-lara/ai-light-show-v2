import { useState } from 'preact/hooks'

export default function ChatSidePanel({ onSendMessage }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')

  const handleSend = () => {
    if (input.trim()) {
      setMessages(prev => [...prev, { text: input, from: 'user' }])
      onSendMessage(input)
      setInput('')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend()
    }
  }

  // Mock receiving response
  // In real, would receive from WS
  const mockResponse = (msg) => {
    setTimeout(() => {
      setMessages(prev => [...prev, { text: `Echo: ${msg}`, from: 'bot' }])
    }, 1000)
  }

  return (
    <div style={{ width: '300px', borderLeft: '1px solid #333', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '10px', borderBottom: '1px solid #333' }}>
        <h3>AI Chat</h3>
      </div>
      <div style={{ flex: 1, padding: '10px', overflowY: 'auto' }}>
        {messages.map((msg, index) => (
          <div key={index} style={{ marginBottom: '10px', textAlign: msg.from === 'user' ? 'right' : 'left' }}>
            <div style={{
              display: 'inline-block',
              padding: '5px 10px',
              background: msg.from === 'user' ? '#4a9eff' : '#333',
              borderRadius: '5px'
            }}>
              {msg.text}
            </div>
          </div>
        ))}
      </div>
      <div style={{ padding: '10px', borderTop: '1px solid #333' }}>
        <input
          type="text"
          value={input}
          onInput={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type a message..."
          style={{ width: '100%', padding: '5px', marginBottom: '5px' }}
        />
        <button onClick={handleSend} style={{ width: '100%' }}>Send</button>
      </div>
    </div>
  )
}
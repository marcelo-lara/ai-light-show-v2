export async function installMockWebSocket(page, { initialState }) {
  await page.addInitScript(({ initialState: seed }) => {
    const OPEN = 1
    const CLOSED = 3

    const state = {
      fixtures: Array.isArray(seed?.fixtures) ? seed.fixtures : [],
      pois: Array.isArray(seed?.pois) ? seed.pois : [],
      cues: Array.isArray(seed?.cues) ? seed.cues : [],
      song: seed?.song || null,
      status: seed?.status || { isPlaying: false, previewActive: false, preview: null },
    }

    const clients = []
    const server = {
      sentMessages: [],
      serverMessages: [],
      getMessagesByType(type) {
        return this.sentMessages.filter((entry) => entry?.message?.type === type)
      },
      broadcast(payload) {
        this.serverMessages.push(payload)
        for (const client of clients) {
          if (client.readyState !== OPEN) continue
          client.onmessage?.({ data: JSON.stringify(payload) })
        }
      },
      sendInitial(client) {
        client.onmessage?.({
          data: JSON.stringify({
            type: 'initial',
            fixtures: state.fixtures,
            pois: state.pois,
            cues: { entries: state.cues },
            song: state.song,
            status: state.status,
          }),
        })
      },
      applySavePoiTarget(message) {
        state.fixtures = state.fixtures.map((fixture) => {
          if (fixture?.id !== message.fixture_id) return fixture
          return {
            ...fixture,
            poi_targets: {
              ...(fixture.poi_targets || {}),
              [message.poi_id]: {
                pan: message.pan,
                tilt: message.tilt,
              },
            },
          }
        })
        this.broadcast({ type: 'fixtures_updated', fixtures: state.fixtures })
      },
      applySaveSections(message) {
        const parts = {}
        for (const section of message.sections || []) {
          const name = String(section?.name || '').trim()
          const start = Number(section?.start)
          const end = Number(section?.end)
          if (!name || !Number.isFinite(start) || !Number.isFinite(end)) continue
          parts[name] = [start, end]
        }
        if (state.song && typeof state.song === 'object') {
          state.song = {
            ...state.song,
            metadata: {
              ...(state.song.metadata || {}),
              parts,
            },
          }
        }
        this.broadcast({ type: 'sections_updated', parts })
        this.broadcast({ type: 'sections_save_result', ok: true })
      },
      handleClientMessage(client, rawData) {
        let message = null
        try {
          message = JSON.parse(rawData)
        } catch {
          return
        }

        this.sentMessages.push({
          clientUrl: client.url,
          message,
        })

        if (message.type === 'playback') {
          state.status = {
            ...(state.status || {}),
            isPlaying: !!message.playing,
          }
          this.broadcast({ type: 'status', status: state.status })
          return
        }

        if (message.type === 'preview_effect') {
          this.broadcast({ type: 'preview_status', active: true, request_id: message.request_id || null })
          setTimeout(() => {
            this.broadcast({ type: 'preview_status', active: false, request_id: message.request_id || null })
          }, 50)
          return
        }

        if (message.type === 'save_poi_target') {
          this.applySavePoiTarget(message)
          return
        }

        if (message.type === 'save_sections') {
          this.applySaveSections(message)
          return
        }

        if (message.type === 'load_song') {
          this.sendInitial(client)
        }
      },
    }

    class MockWebSocket {
      constructor(url) {
        this.url = url
        this.readyState = 0
        this.onopen = null
        this.onmessage = null
        this.onerror = null
        this.onclose = null
        clients.push(this)

        setTimeout(() => {
          this.readyState = OPEN
          this.onopen?.()
          if (typeof this.url === 'string' && this.url.includes('/ws')) {
            server.sendInitial(this)
          }
        }, 0)
      }

      send(data) {
        if (this.readyState !== OPEN) return
        server.handleClientMessage(this, data)
      }

      close() {
        if (this.readyState === CLOSED) return
        this.readyState = CLOSED
        this.onclose?.()
      }
    }

    MockWebSocket.CONNECTING = 0
    MockWebSocket.OPEN = OPEN
    MockWebSocket.CLOSING = 2
    MockWebSocket.CLOSED = CLOSED

    window.__mockWsServer = server
    window.WebSocket = MockWebSocket
  }, { initialState })
}

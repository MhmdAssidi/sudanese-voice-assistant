import React, { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const API = '/api'
const DEFAULT_TOKEN = 'sudanvoice-3f8a1c'

const TABS = [
  { id: 'app', label: 'App', icon: 'phone' },
  { id: 'ussd', label: 'USSD', icon: 'hash' },
  { id: 'sms', label: 'SMS', icon: 'chat' },
  { id: 'voice', label: 'Voice', icon: 'call' },
  { id: 'web', label: 'Web', icon: 'globe' },
]

const STARTER_PROMPTS = [
  'Explain it like I am 5',
  'Convert 800 to EUR',
  'Practice quiz',
]

function timeLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const ICONS = {
  phone: (
    <>
      <rect x="6" y="2" width="12" height="20" rx="2.5" />
      <line x1="11" y1="18" x2="13" y2="18" />
    </>
  ),
  hash: (
    <>
      <line x1="4" y1="9" x2="20" y2="9" />
      <line x1="4" y1="15" x2="20" y2="15" />
      <line x1="10" y1="3" x2="8" y2="21" />
      <line x1="16" y1="3" x2="14" y2="21" />
    </>
  ),
  chat: (
    <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7A8.38 8.38 0 0 1 4 11.5 8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z" />
  ),
  call: (
    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.9.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" />
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <path d="M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z" />
    </>
  ),
  send: (
    <>
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </>
  ),
  mic: (
    <>
      <rect x="9" y="2" width="6" height="11" rx="3" />
      <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </>
  ),
  clip: (
    <path d="M21.44 11.05 12.25 20.24a5.5 5.5 0 0 1-7.78-7.78l9.19-9.19a3.67 3.67 0 0 1 5.19 5.19l-9.2 9.19a1.83 1.83 0 0 1-2.59-2.59l8.49-8.49" />
  ),
  more: (
    <g fill="currentColor" stroke="none">
      <circle cx="12" cy="5" r="1.9" />
      <circle cx="12" cy="12" r="1.9" />
      <circle cx="12" cy="19" r="1.9" />
    </g>
  ),
}

function Icon({ name }) {
  return (
    <span className="icon" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {ICONS[name] || null}
      </svg>
    </span>
  )
}

function PhoneStatus({ light = false }) {
  return (
    <div className={`phone-status ${light ? 'light' : ''}`}>
      <strong>{timeLabel()}</strong>
      <div className="phone-island" />
      <div className="status-icons">
        <svg className="stat-ic" viewBox="0 0 20 16" aria-hidden="true">
          <rect x="0" y="11" width="3.2" height="5" rx="1" fill="currentColor" />
          <rect x="5.6" y="8" width="3.2" height="8" rx="1" fill="currentColor" />
          <rect x="11.2" y="4.5" width="3.2" height="11.5" rx="1" fill="currentColor" />
          <rect x="16.8" y="1" width="3.2" height="15" rx="1" fill="currentColor" />
        </svg>
        <svg className="stat-ic" viewBox="0 0 20 16" aria-hidden="true">
          <path d="M10 3.2c3 0 5.8 1.2 7.9 3.2l-1.6 1.7A9 9 0 0 0 10 5.6 9 9 0 0 0 3.7 8.1L2.1 6.4A11.4 11.4 0 0 1 10 3.2z" fill="currentColor" />
          <path d="M10 7.6c1.9 0 3.6.7 4.9 2l-1.6 1.7A4.6 4.6 0 0 0 10 10a4.6 4.6 0 0 0-3.3 1.3L5.1 9.6A6.9 6.9 0 0 1 10 7.6z" fill="currentColor" />
          <circle cx="10" cy="13.4" r="1.7" fill="currentColor" />
        </svg>
        <svg className="stat-ic stat-batt" viewBox="0 0 26 14" aria-hidden="true">
          <rect x="0.8" y="0.8" width="21" height="12.4" rx="3" fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.55" />
          <rect x="2.6" y="2.6" width="14" height="8.8" rx="1.6" fill="currentColor" />
          <rect x="23.2" y="4.6" width="1.8" height="4.8" rx="0.9" fill="currentColor" opacity="0.55" />
        </svg>
      </div>
    </div>
  )
}

function MessageBubble({ role, text }) {
  return (
    <div className={`bubble ${role}`}>
      <p dir="auto">{text}</p>
      <span>{timeLabel()}</span>
    </div>
  )
}

function TypingBubble() {
  return (
    <div className="bubble assistant typing" aria-label="Assistant is typing">
      <span className="typing-dots" aria-hidden="true"><i /><i /><i /></span>
    </div>
  )
}

function ModelName({ health }) {
  const name = health?.models?.llm || 'qwen3:32b'
  return name.includes('qwen') ? 'Qwen' : name.split('/').pop()?.split(':')[0] || 'Qwen'
}

async function readError(res) {
  const raw = await res.text()
  try {
    const parsed = JSON.parse(raw)
    return parsed.detail || raw
  } catch {
    return raw || `${res.status} ${res.statusText}`
  }
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)

  function writeString(offset, value) {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let i = 0; i < samples.length; i += 1, offset += 2) {
    const value = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, value < 0 ? value * 0x8000 : value * 0x7fff, true)
  }

  return new Blob([view], { type: 'audio/wav' })
}

async function convertRecordingToWav(blob) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext
  if (!AudioContextClass) {
    throw new Error('browser cannot convert microphone audio to WAV')
  }
  const context = new AudioContextClass()
  try {
    const audioBuffer = await context.decodeAudioData(await blob.arrayBuffer())
    const channels = audioBuffer.numberOfChannels
    const length = audioBuffer.length
    const mono = new Float32Array(length)

    for (let channel = 0; channel < channels; channel += 1) {
      const data = audioBuffer.getChannelData(channel)
      for (let i = 0; i < length; i += 1) {
        mono[i] += data[i] / channels
      }
    }

    return encodeWav(mono, audioBuffer.sampleRate)
  } finally {
    context.close?.()
  }
}

export default function App() {
  const [tab, setTab] = useState('app')
  const [token] = useState(localStorage.getItem('voice_token') || DEFAULT_TOKEN)
  const [health, setHealth] = useState(null)
  const [busy, setBusy] = useState(false)
  const [recording, setRecording] = useState(false)
  const [recordingStartedAt, setRecordingStartedAt] = useState(0)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [text, setText] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "Hi, I'm iKnow AI. Send me a message and I will help you out.",
    },
  ])
  const [lastVoice, setLastVoice] = useState({ user: '', reply: '' })
  const [lastRecordingUrl, setLastRecordingUrl] = useState('')
  const [voiceDebug, setVoiceDebug] = useState('Tap the mic, speak for 4 seconds, then tap again.')
  const [ussdCode, setUssdCode] = useState('*123#')
  const [ussdChoice, setUssdChoice] = useState('')
  const [notice, setNotice] = useState('')

  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const audioRef = useRef(null)
  const fileRef = useRef(null)
  const messagesRef = useRef(null)

  useEffect(() => {
    localStorage.setItem('voice_token', token)
    checkHealth()
  }, [token])

  useEffect(() => {
    if (!recording) {
      setRecordingSeconds(0)
      return undefined
    }
    const timer = window.setInterval(() => {
      setRecordingSeconds(Math.max(0, Math.round((Date.now() - recordingStartedAt) / 1000)))
    }, 250)
    return () => window.clearInterval(timer)
  }, [recording, recordingStartedAt])

  // Keep the chat pinned to the newest message (and the typing indicator).
  useEffect(() => {
    const el = messagesRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [messages, busy, tab])

  const online = health?.status === 'ok'
  const modelLabel = <ModelName health={health} />
  const screenTitle = useMemo(() => {
    if (tab === 'sms') return 'iKnow AI'
    if (tab === 'voice') return 'Voice AI'
    if (tab === 'web') return 'iKnow Web'
    return 'iKnow'
  }, [tab])

  function authHeaders(extra = {}) {
    return { 'X-Auth-Token': token, ...extra }
  }

  function showNotice(message) {
    setNotice(message)
    window.clearTimeout(showNotice.timer)
    showNotice.timer = window.setTimeout(() => setNotice(''), 3600)
  }

  async function checkHealth() {
    try {
      const res = await fetch(`${API}/health`)
      setHealth(await res.json())
    } catch (error) {
      setHealth({ error: error.message })
    }
  }

  async function askAssistant(inputText = text, source = tab) {
    const trimmed = inputText.trim()
    if (!trimmed || busy) return
    setBusy(true)
    setText('')
    setMessages((items) => [...items, { role: 'user', text: trimmed }])

    try {
      const res = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ text: trimmed }),
      })
      if (!res.ok) throw new Error(await readError(res))
      const data = await res.json()
      const reply = data.reply_text || '...'
      setMessages((items) => [...items, { role: 'assistant', text: reply }])
      if (source === 'app') speakText(reply, false)
    } catch (error) {
      showNotice(`Chat failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function speakText(value, lock = true) {
    const speech = value.trim()
    if (!speech || (lock && busy)) return
    if (lock) setBusy(true)
    try {
      const res = await fetch(`${API}/speak`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ text: speech }),
      })
      if (!res.ok) throw new Error(await readError(res))
      playBlob(await res.blob())
    } catch (error) {
      showNotice(`Speech failed: ${error.message}`)
    } finally {
      if (lock) setBusy(false)
    }
  }

  function playBlob(blob) {
    const url = URL.createObjectURL(blob)
    if (audioRef.current) {
      audioRef.current.src = url
      audioRef.current.play().catch(() => {})
    }
  }

  async function startRecording() {
    if (busy || recording) return
    if (!navigator.mediaDevices?.getUserMedia) {
      showNotice('Microphone is unavailable in this browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []
      const mimeType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
      ].find((type) => MediaRecorder.isTypeSupported(type))
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      recorderRef.current = recorder
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data)
      }
      recorder.onstop = submitVoice
      recorder.start(250)
      setRecordingStartedAt(Date.now())
      setVoiceDebug(`Recording from ${stream.getAudioTracks()[0]?.label || 'microphone'}...`)
      setRecording(true)
    } catch (error) {
      showNotice(`Mic error: ${error.message}`)
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state !== 'recording') return
    const elapsed = Date.now() - recordingStartedAt
    if (elapsed < 900) {
      showNotice('Speak for at least one second.')
      window.setTimeout(() => recorderRef.current?.stop(), 700)
      return
    }
    recorderRef.current.stop()
  }

  async function submitVoice() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    setRecording(false)
    setBusy(true)
    try {
      const blobType = recorderRef.current?.mimeType || 'audio/webm'
      const browserBlob = new Blob(chunksRef.current, { type: blobType })
      const seconds = Math.max(0.1, (Date.now() - recordingStartedAt) / 1000)
      if (browserBlob.size < 6000) {
        throw new Error('browser recorded almost no audio. Check Windows mic input or Chrome microphone device.')
      }
      setVoiceDebug(`Captured ${Math.round(browserBlob.size / 1024)} KB in ${seconds.toFixed(1)}s. Converting to WAV...`)
      const wavBlob = await convertRecordingToWav(browserBlob)
      if (lastRecordingUrl) URL.revokeObjectURL(lastRecordingUrl)
      const recordingUrl = URL.createObjectURL(wavBlob)
      setLastRecordingUrl(recordingUrl)
      setVoiceDebug(`Captured ${Math.round(browserBlob.size / 1024)} KB, converted to ${Math.round(wavBlob.size / 1024)} KB WAV. Sending to Whisper...`)
      const form = new FormData()
      form.append('file', wavBlob, 'recording.wav')
      const res = await fetch(`${API}/voice`, {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      })
      if (!res.ok) throw new Error(await readError(res))
      const data = await res.json()
      const userText = data.user_text || ''
      const replyText = data.reply_text || ''
      setLastVoice({ user: userText, reply: replyText })
      setVoiceDebug(`Whisper heard ${userText.length} characters. Qwen reply is ready.`)
      setMessages((items) => [
        ...items,
        { role: 'user', text: userText },
        { role: 'assistant', text: replyText },
      ])
      if (audioRef.current) {
        // The backend tells us the format (opus is ~10x smaller than wav).
        const mime = data.audio_mime || 'audio/wav'
        audioRef.current.src = `data:${mime};base64,${data.audio_b64}`
        audioRef.current.play().catch(() => {})
      }
    } catch (error) {
      setVoiceDebug(`Failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  async function transcribeUpload(file) {
    if (!file || busy) return
    setBusy(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API}/transcribe`, {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      })
      if (!res.ok) throw new Error(await readError(res))
      const data = await res.json()
      setText(data.text || '')
      showNotice('Audio transcribed.')
    } catch (error) {
      showNotice(`Upload failed: ${error.message}`)
    } finally {
      setBusy(false)
    }
  }

  function pressUssd(key) {
    setUssdCode((value) => `${value}${key}`)
  }

  function submitUssdChoice() {
    if (ussdChoice === '1') {
      setTab('sms')
      askAssistant('I opened the AI Assistant from USSD. Greet me briefly.', 'sms')
      return
    }
    showNotice(ussdChoice ? `USSD option ${ussdChoice} selected.` : 'Enter a choice first.')
  }

  function renderAppHome() {
    return (
      <div className="app-screen blue-screen">
        <PhoneStatus light />
        <section className="home-hero">
          <div className="logo-mark">iK</div>
          <h1>iKnow</h1>
          <p>Your AI Assistant</p>
        </section>

        <section className="intro-card">
          Hello! I am iKnow, your AI assistant. I can help with information,
          calculations, translations, and more.
        </section>

        <div className="prompt-list">
          {STARTER_PROMPTS.map((prompt) => (
            <button key={prompt} onClick={() => askAssistant(prompt, 'app')}>
              {prompt}
            </button>
          ))}
        </div>

        <PromptBar
          placeholder="Ask me anything..."
          value={text}
          busy={busy}
          onChange={setText}
          onSend={() => askAssistant(text, 'app')}
          onMic={recording ? stopRecording : startRecording}
          onAttach={() => fileRef.current?.click()}
          recording={recording}
        />
      </div>
    )
  }

  function renderSms() {
    return (
      <div className="app-screen dark-screen">
        <PhoneStatus />
        <Header
          title={screenTitle}
          subtitle={online ? 'Online AI' : 'Connecting'}
          onCall={() => speakText(messages[messages.length - 1]?.text || '')}
        />
        <div className="day-label">Today</div>
        <div className="messages" ref={messagesRef}>
          {messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} {...message} />
          ))}
          {busy && <TypingBubble />}
        </div>
        <PromptBar
          placeholder="Type a message..."
          value={text}
          busy={busy}
          maxLength={160}
          onChange={setText}
          onSend={() => askAssistant(text, 'sms')}
          sendOnly
        />
      </div>
    )
  }

  function renderUssd() {
    return (
      <div className="app-screen ussd-screen">
        <PhoneStatus />
        <div className="ussd-top">
          <p>Enter USSD code</p>
          <strong dir="ltr">{ussdCode}</strong>
        </div>
        {ussdChoice ? (
          <section className="ussd-card">
            <h3>USSD SERVICE</h3>
            <p>Welcome to iKnow AI</p>
            <ol>
              <li>AI Assistant</li>
              <li>Check Balance</li>
              <li>Weather</li>
              <li>News Update</li>
              <li>Language: English</li>
            </ol>
            <input
              value={ussdChoice}
              onChange={(event) => setUssdChoice(event.target.value)}
              placeholder="Enter choice (1-5)"
              inputMode="numeric"
            />
            <div className="ussd-actions">
              <button onClick={() => setUssdChoice('')}>Cancel</button>
              <button onClick={submitUssdChoice}>Send</button>
            </div>
          </section>
        ) : (
          <>
            <div className="keypad">
              {['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'].map((key) => (
                <button key={key} onClick={() => pressUssd(key)}>{key}</button>
              ))}
            </div>
            <button className="call-button" onClick={() => setUssdChoice('1')}>
              <Icon name="call" />
            </button>
          </>
        )}
      </div>
    )
  }

  function renderVoice() {
    const status = recording ? 'Listening' : busy ? 'Thinking' : 'Ready'
    return (
      <div className="app-screen voice-screen">
        <PhoneStatus />
        <section className="voice-panel">
          <div className="logo-mark">iK</div>
          <h1>Voice AI</h1>
          <p>{recording ? `${status} ${recordingSeconds}s` : status}</p>

          <button
            className={`voice-orb ${recording ? 'recording' : ''}`}
            onClick={recording ? stopRecording : startRecording}
            disabled={busy && !recording}
            aria-label={recording ? 'Stop recording' : 'Start recording'}
          >
            <Icon name="mic" />
          </button>

          <div className="voice-wave" aria-hidden="true">
            <i /><i /><i /><i /><i />
          </div>
        </section>

        <section className="voice-result">
          {lastRecordingUrl && (
            <div className="recording-preview">
              <span>Last browser recording</span>
              <audio controls src={lastRecordingUrl} />
            </div>
          )}
          <div>
            <span>You said</span>
            <p dir="auto">{lastVoice.user || 'Your transcript will appear here.'}</p>
          </div>
          <div>
            <span>Qwen replied</span>
            <p dir="auto">{lastVoice.reply || 'The spoken reply will appear here.'}</p>
          </div>
          <small>{voiceDebug}</small>
        </section>
      </div>
    )
  }

  function renderWeb() {
    return (
      <div className="app-screen web-screen">
        <PhoneStatus />
        <section className="web-panel">
          <div className="logo-mark">iK</div>
          <h1>iKnow Web</h1>
          <p>{modelLabel} is online</p>
        </section>
        <div className="messages web-messages" ref={messagesRef}>
          {messages.slice(-4).map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} {...message} />
          ))}
          {busy && <TypingBubble />}
        </div>
        <PromptBar
          placeholder="Search or ask..."
          value={text}
          busy={busy}
          onChange={setText}
          onSend={() => askAssistant(text, 'web')}
          sendOnly
        />
      </div>
    )
  }

  return (
    <main className="ik-page">
      <section className="demo-stage">
        <nav className="mode-tabs" aria-label="Demo modes">
          {TABS.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? 'active' : ''}
              onClick={() => setTab(item.id)}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="phone-shell">
          {tab === 'app' && renderAppHome()}
          {tab === 'sms' && renderSms()}
          {tab === 'ussd' && renderUssd()}
          {tab === 'voice' && renderVoice()}
          {tab === 'web' && renderWeb()}
        </div>
      </section>

      <input
        ref={fileRef}
        hidden
        type="file"
        accept="audio/*"
        onChange={(event) => transcribeUpload(event.target.files?.[0])}
      />
      <audio ref={audioRef} hidden />
      {notice && <div className="toast">{notice}</div>}
    </main>
  )
}

function Header({ title, subtitle, onCall }) {
  return (
    <header className="chat-header">
      <div className="logo-mark small">iK</div>
      <div className="chat-title">
        <h2>{title}</h2>
        <p><span /> {subtitle}</p>
      </div>
      <button onClick={onCall} aria-label="Play last reply">
        <Icon name="call" />
      </button>
      <button aria-label="More">
        <Icon name="more" />
      </button>
    </header>
  )
}

function PromptBar({
  placeholder,
  value,
  busy,
  recording,
  sendOnly,
  maxLength,
  onChange,
  onSend,
  onMic,
  onAttach,
}) {
  function submit(event) {
    event.preventDefault()
    onSend()
  }

  return (
    <form className="prompt-bar" onSubmit={submit}>
      {!sendOnly && (
        <button type="button" onClick={onAttach} disabled={busy} aria-label="Attach audio">
          <Icon name="clip" />
        </button>
      )}
      <input
        value={value}
        onChange={(event) =>
          onChange(maxLength ? event.target.value.slice(0, maxLength) : event.target.value)
        }
        placeholder={placeholder}
        disabled={busy}
        maxLength={maxLength}
        dir="auto"
      />
      {maxLength ? (
        <span
          aria-live="polite"
          style={{
            fontSize: '11px',
            opacity: 0.65,
            alignSelf: 'center',
            padding: '0 6px',
            whiteSpace: 'nowrap',
          }}
        >
          {value.length}/{maxLength}
        </span>
      ) : null}
      {sendOnly ? (
        <button type="submit" disabled={busy || !value.trim()} aria-label="Send">
          <Icon name="send" />
        </button>
      ) : (
        <button
          type={value.trim() ? 'submit' : 'button'}
          onClick={value.trim() ? undefined : onMic}
          disabled={busy && !recording}
          className={recording ? 'recording' : ''}
          aria-label={value.trim() ? 'Send' : 'Record'}
        >
          <Icon name={value.trim() ? 'send' : 'mic'} />
        </button>
      )}
    </form>
  )
}

# Sudanese Voice Assistant

An AI assistant that speaks and understands **Sudanese Arabic**, demoed across five
mobile channels: **App, USSD, SMS, Voice, and Web**.

- **Frontend** (`webui/`) — React + Vite. A phone-mockup UI with the five channel tabs.
- **Backend** (`serve.py`) — FastAPI. Speech-to-text → LLM → text-to-speech, plus live web search.

## How it works

```
Browser (webui)
   └── /api/  ──►  serve.py (FastAPI)
                      ├── Whisper large-v3   — speech to text
                      ├── Qwen3 via Ollama   — the reply
                      ├── XTTS               — text to speech
                      └── Serper.dev         — live web search (weather, scores, news)
```

The LLM has a training cutoff, so it cannot know today's events. When a question
looks time-sensitive, the backend searches the web first and hands the results to
the model, which answers in the **user's own language**.

## Requirements

The backend needs a **GPU machine** (Whisper + XTTS + a 32B LLM). The frontend runs anywhere.

## Setup

**1. Configure secrets** — create a `.env` (never commit it):

```
SERPER_API_KEY=your_serper_key
VOICE_TOKEN=your_shared_token
QWEN_MODEL=qwen3:32b
```

**2. Backend** (on the GPU machine):

```bash
pip install -r requirements.txt
python -m uvicorn serve:app --host 127.0.0.1 --port 8770
```

**3. Frontend**:

```bash
cd webui
npm install
npm run dev      # development
npm run build    # production -> dist/
```

For production, serve `webui/dist/` with nginx and proxy `/api/` to the backend.

> **Note:** the microphone only works over **HTTPS** (or `localhost`) — browsers block
> it on plain HTTP. Serve the site over HTTPS for voice input to work.

## Credits

The original Sudanese Voice Assistant — the backend and the web UI — was created by
**[rabbato](https://github.com/rabbato/sudan-LLM)**. This repository builds on that work.

My contributions: live web search integration (Serper.dev), model evaluation
(Qwen3 vs Fanar vs Jais across 200 Sudanese/Arabic/English prompts), deployment
(nginx + tunnels), and UI refinement.

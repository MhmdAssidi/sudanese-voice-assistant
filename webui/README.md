# Sudanese Voice Assistant Console

React + Vite UI for the RunPod voice assistant service.

The browser talks to the Vite dev server at `http://localhost:5173`. Vite proxies
`/api/*` to the pod service at `127.0.0.1:8770` through your SSH tunnel. This keeps
the microphone working in the browser and avoids CORS issues.

## Backend Flow

- `POST /chat`: text -> Qwen -> text reply
- `POST /transcribe`: audio -> Whisper transcript
- `POST /speak`: text -> XTTS wav
- `POST /voice`: audio -> Whisper transcript -> Qwen reply -> XTTS audio
- `GET /health`: model and service status

## Start The Pod Service

On the pod, from the project directory:

```bash
bash run_voice.sh
```

The script expects:

- `/workspace/venv_xtts` with XTTS, faster-whisper, FastAPI, and uvicorn installed.
- Ollama running or installable on the pod.
- `qwen3:32b` available in Ollama.
- `/workspace/sudan_voice_app/tts/ref.wav` as the XTTS reference voice.

The service binds to:

```text
127.0.0.1:8770
```

## Open The SSH Tunnel

On your laptop, keep this running in a separate terminal:

```bash
ssh root@<POD_IP> -p <SSH_PORT> -i ~/Downloads/id_ed25519 -L 8770:127.0.0.1:8770 -N
```

Use RunPod's SSH over exposed TCP address and port.

## Run The UI

```bash
cd webui
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Default token:

```text
sudanvoice-3f8a1c
```

## Test Order

1. Click `Check status`.
2. Type Arabic text in Text Chat and click `Send`.
3. Click `Speak` to hear XTTS read the latest reply.
4. Use `Record` / `Stop` in Voice Chat to test the full fast turn-taking loop.
5. Watch System Log for latency and errors.

## V2 Direction

The current version is fast turn-taking. True live streaming should be a separate
v2 using WebSockets, chunked microphone audio, partial transcription, streaming
Qwen output, and chunked TTS playback.

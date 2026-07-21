#!/usr/bin/env bash
# Launch the Sudanese voice assistant service on the pod.
#
# Expected pod setup:
#   - Ollama is installed and has qwen3:32b.
#   - /workspace/venv_xtts contains faster-whisper, Coqui TTS, FastAPI, uvicorn.
#   - /workspace/tts_home contains the XTTS cache.
#   - /workspace/sudan_voice_app/tts/ref.wav exists as the XTTS reference voice.

set -u

PROJ="${PROJ:-/workspace/sudanese-speech}"
PORT="${PORT:-8770}"
TOKEN="${VOICE_TOKEN:-sudanvoice-3f8a1c}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
QWEN_MODEL="${QWEN_MODEL:-qwen3:32b}"
XTTS_REF="${XTTS_REF:-/workspace/sudan_voice_app/tts/ref.wav}"
XTTS_CHECKPOINT="${XTTS_CHECKPOINT:-}"
XTTS_CONFIG="${XTTS_CONFIG:-}"
XTTS_VOCAB="${XTTS_VOCAB:-}"
XTTS_SPEAKER_FILE="${XTTS_SPEAKER_FILE:-}"
VENV="${VENV:-/workspace/venv_xtts}"

ok() { echo "[ok]   $*"; }
info() { echo "[..]   $*"; }
fail() { echo "[FAIL] $*"; }

if [ -d /workspace/ollama-bin/bin ]; then
  export PATH="/workspace/ollama-bin/bin:$PATH"
fi

if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg present"
else
  info "ffmpeg missing -> installing"
  apt-get update -y >/dev/null 2>&1
  apt-get install -y ffmpeg >/dev/null 2>&1
  command -v ffmpeg >/dev/null 2>&1 || { fail "ffmpeg install failed"; exit 1; }
  ok "ffmpeg installed"
fi

if [ -f "$VENV/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  ok "venv activated: $VENV"
else
  fail "missing venv: $VENV"
  fail "create it first and install TTS, faster-whisper, fastapi, uvicorn, requests, soundfile"
  exit 1
fi

if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  ok "ollama already running"
else
  info "ollama down -> starting"
  nohup ollama serve >/workspace/ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1 || { fail "ollama did not start"; exit 1; }
  ok "ollama started"
fi

if curl -s "$OLLAMA_URL/api/tags" | grep -q "$QWEN_MODEL"; then
  ok "$QWEN_MODEL visible"
else
  fail "$QWEN_MODEL not found in ollama list"
  exit 1
fi

if [ -f "$XTTS_REF" ]; then
  ok "XTTS reference found: $XTTS_REF"
else
  fail "missing XTTS reference: $XTTS_REF"
  exit 1
fi

if [ -n "$XTTS_CHECKPOINT" ]; then
  [ -f "$XTTS_CHECKPOINT" ] || { fail "missing XTTS_CHECKPOINT: $XTTS_CHECKPOINT"; exit 1; }
  [ -f "$XTTS_CONFIG" ] || { fail "missing XTTS_CONFIG: $XTTS_CONFIG"; exit 1; }
  [ -f "$XTTS_VOCAB" ] || { fail "missing XTTS_VOCAB: $XTTS_VOCAB"; exit 1; }
  if [ -n "$XTTS_SPEAKER_FILE" ]; then
    [ -f "$XTTS_SPEAKER_FILE" ] || { fail "missing XTTS_SPEAKER_FILE: $XTTS_SPEAKER_FILE"; exit 1; }
  fi
  ok "fine-tuned XTTS checkpoint found: $XTTS_CHECKPOINT"
fi

export COQUI_TOS_AGREED=1
export TTS_HOME="${TTS_HOME:-/workspace/tts_home}"
export VOICE_TOKEN="$TOKEN"
export OLLAMA_URL
export QWEN_MODEL
export XTTS_REF
export XTTS_CHECKPOINT
export XTTS_CONFIG
export XTTS_VOCAB
export XTTS_SPEAKER_FILE

cd "$PROJ" || { fail "cannot cd $PROJ"; exit 1; }

info "starting serve.py on 127.0.0.1:$PORT"
nohup python -m uvicorn serve:app --host 127.0.0.1 --port "$PORT" >/workspace/voice.log 2>&1 &

for _ in $(seq 1 90); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
  sleep 2
done

if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  ok "service ready on 127.0.0.1:$PORT"
  echo
  echo "Laptop tunnel:"
  echo "  ssh root@<POD_IP> -p <SSH_PORT> -i ~/Downloads/id_ed25519 -L $PORT:127.0.0.1:$PORT -N"
  echo
  echo "Laptop UI:"
  echo "  cd webui && npm run dev"
  echo "  open http://localhost:5173"
  echo "  token: $TOKEN"
else
  fail "service not ready; check /workspace/voice.log"
fi

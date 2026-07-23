"""Sudanese voice assistant service: Whisper -> Qwen -> XTTS.

Runs on the RunPod and binds to 127.0.0.1:8770. The laptop UI reaches it through
an SSH tunnel and the Vite /api proxy.
"""
from __future__ import annotations

import base64
import io
import os
import re
import secrets
import tempfile
import traceback
from contextlib import asynccontextmanager

import numpy as np
import requests
import soundfile as sf
import torch
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from faster_whisper import WhisperModel
from pydantic import BaseModel
from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

WHISPER_ID = os.environ.get("WHISPER_ID", "large-v3")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen3:32b")
XTTS_ID = os.environ.get("XTTS_ID", "tts_models/multilingual/multi-dataset/xtts_v2")
# The reference voice this assistant speaks with. XTTS clones whoever is heard
# in this clip, so this file IS the project's voice. Kept outside the repo
# because it is a recording of a real person.
XTTS_REF = os.environ.get("XTTS_REF", "/workspace/mhmd_voice/voice.wav")

# XTTS accepts several reference clips of the SAME speaker and averages them,
# which gives a noticeably steadier voice than a single clip. Set XTTS_REFS to
# a comma-separated list; otherwise we use the single reference above.
XTTS_REFS = [p.strip() for p in os.environ.get("XTTS_REFS", "").split(",") if p.strip()] \
    or XTTS_REF


def _f(name, default):
    """Read a float tuning knob from the environment."""
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


# Voice quality knobs. These shape how the speech is generated:
#   temperature        - higher is more expressive, lower is more stable
#   repetition_penalty - guards against stuttering / repeated syllables
#   length_penalty     - <1 favours shorter, tighter delivery
#   top_k / top_p      - how adventurous the sampling is
#   speed              - playback rate of the generated speech
#   gpt_cond_len       - seconds of reference audio used to capture the voice
#                        (longer = closer match, to a point)
XTTS_PARAMS = {
    "temperature": _f("XTTS_TEMPERATURE", 0.70),
    "repetition_penalty": _f("XTTS_REPETITION_PENALTY", 5.0),
    "length_penalty": _f("XTTS_LENGTH_PENALTY", 1.0),
    "top_k": int(_f("XTTS_TOP_K", 50)),
    "top_p": _f("XTTS_TOP_P", 0.85),
    "speed": _f("XTTS_SPEED", 1.0),
    "gpt_cond_len": int(_f("XTTS_COND_LEN", 10)),
    "enable_text_splitting": os.environ.get("XTTS_SPLIT", "1") != "0",
}
XTTS_LANG = os.environ.get("XTTS_LANG", "ar")
XTTS_CHECKPOINT = os.environ.get("XTTS_CHECKPOINT", "").strip()
XTTS_CONFIG = os.environ.get("XTTS_CONFIG", "").strip()
XTTS_VOCAB = os.environ.get("XTTS_VOCAB", "").strip()
XTTS_SPEAKER_FILE = os.environ.get("XTTS_SPEAKER_FILE", "").strip()

# Live web search via Serper.dev (a Google Search API). Optional: if
# SERPER_API_KEY is unset, search is skipped and the assistant answers from the
# model's own knowledge, exactly as before.
# Spoken replies are capped shorter than typed ones: XTTS synthesis time grows
# with text length, so a brief answer is both more natural and much faster.
VOICE_NUM_PREDICT = int(os.environ.get("VOICE_NUM_PREDICT", "80"))
# Whisper beam size. 1 is ~0.2s faster but noticeably less accurate on real
# (noisy, quiet, re-recorded) audio, so accuracy wins here.
WHISPER_BEAM = int(os.environ.get("WHISPER_BEAM", "5"))

# Reply audio format: "opus" (~10x smaller, faster to deliver) or "wav".
AUDIO_FORMAT = os.environ.get("AUDIO_FORMAT", "opus").strip().lower()
AUDIO_MIME = "audio/ogg" if AUDIO_FORMAT == "opus" else "audio/wav"

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "").strip()
SERPER_URL = "https://google.serper.dev/search"

os.environ.setdefault("COQUI_TOS_AGREED", "1")
os.environ.setdefault("TTS_HOME", "/workspace/tts_home")

VOICE_TOKEN = os.environ.get("VOICE_TOKEN") or secrets.token_urlsafe(24)
TOKEN_FROM_ENV = bool(os.environ.get("VOICE_TOKEN"))
MAX_UPLOAD = 25 * 1024 * 1024
MAX_TEXT = 2000

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_COMPUTE = "float16" if DEVICE == "cuda" else "int8"

SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    (
        "انت مساعد صوتي سوداني ودود.\n\n"
        "القاعدة الأهم: ردّ دايماً باللهجة السودانية العامية بس، مهما كانت لغة "
        "المستخدم. انت بتفهم كل اللغات (الإنجليزية والعربية الفصحى وأي لغة تانية)، "
        "لكن بتردّ باللهجة السودانية لوحدها. لو المستخدم اتكلم أو كتب بالإنجليزية، "
        "افهمه كويس وردّ عليه بالسوداني — ما تردّ بالإنجليزية أبداً.\n\n"
        "استخدم كلام سوداني طبيعي زي: شنو، داير، يا زول، هسة، تمام، كويس، "
        "ما في مشكلة، عشان، خلاص، كتير، قروش، موية.\n\n"
        "قواعد تانية:\n"
        "- جاوب على السؤال المطلوب بالضبط. ما تردّ بتحية لو المستخدم سأل سؤال معلومات.\n"
        "- خلي الرد قصير: جملة أو جملتين إلا إذا طلب تفاصيل.\n"
        "- ما تستخدم رموز ولا نقاط ولا إيموجي — الكلام دا بيتقرا بصوت عالي.\n"
        "- لو ما متأكد من حاجة، قول بصراحة. ما تخترع أسماء ولا أرقام ولا أخبار."
    ),
)

S: dict = {}


class TextReq(BaseModel):
    text: str


class ChatResp(BaseModel):
    reply_text: str


def require_auth(authorization: str = Header(None), x_auth_token: str = Header(None)):
    tok = None
    if authorization and authorization.lower().startswith("bearer "):
        tok = authorization[7:].strip()
    if not tok:
        tok = x_auth_token
    if not tok or not secrets.compare_digest(tok, VOICE_TOKEN):
        raise HTTPException(401, "unauthorized")


async def read_capped(file: UploadFile) -> bytes:
    raw = await file.read(MAX_UPLOAD + 1)
    if not raw:
        raise HTTPException(400, "empty audio")
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "audio too large")
    return raw


def clean_reply(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    text = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    return text.strip()


def log_stage(stage: str, message: str):
    print(f"[{stage}] {message}", flush=True)


def log_exception(stage: str, exc: Exception):
    print(f"[{stage}] ERROR: {exc}", flush=True)
    print(traceback.format_exc(), flush=True)


def require_ready():
    if not S:
        raise HTTPException(503, "models still loading")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_stage("startup", f"loading Whisper {WHISPER_ID} on {DEVICE}...")
    S["whisper"] = WhisperModel(WHISPER_ID, device=DEVICE, compute_type=WHISPER_COMPUTE)

    if XTTS_CHECKPOINT:
        for label, path in {
            "XTTS_CHECKPOINT": XTTS_CHECKPOINT,
            "XTTS_CONFIG": XTTS_CONFIG,
            "XTTS_VOCAB": XTTS_VOCAB,
            "XTTS_REF": XTTS_REF,
        }.items():
            if not path or not os.path.exists(path):
                raise RuntimeError(f"{label} not found: {path}")

        log_stage("startup", f"loading fine-tuned XTTS checkpoint on {DEVICE}...")
        config = XttsConfig()
        config.load_json(XTTS_CONFIG)
        xtts = Xtts.init_from_config(config)
        xtts.load_checkpoint(
            config,
            checkpoint_path=XTTS_CHECKPOINT,
            vocab_path=XTTS_VOCAB,
            speaker_file_path=XTTS_SPEAKER_FILE or None,
            use_deepspeed=False,
        )
        if DEVICE == "cuda":
            xtts.cuda()
        S["tts"] = xtts
        S["xtts_config"] = config
        S["tts_sr"] = 24000
        S["tts_mode"] = "finetuned"
        log_stage("startup", f"precomputing XTTS speaker latents from {XTTS_REF}")
        gpt_cond_latent, speaker_embedding = xtts.get_conditioning_latents(
            audio_path=XTTS_REF,
            gpt_cond_len=config.gpt_cond_len,
            max_ref_length=config.max_ref_len,
            sound_norm_refs=config.sound_norm_refs,
        )
        S["gpt_cond_latent"] = gpt_cond_latent
        S["speaker_embedding"] = speaker_embedding
    else:
        log_stage("startup", f"loading XTTS on {DEVICE}...")
        tts = TTS(XTTS_ID).to(DEVICE)
        S["tts"] = tts
        S["tts_sr"] = getattr(tts.synthesizer, "output_sample_rate", 24000)
        S["tts_mode"] = "base"

    if TOKEN_FROM_ENV:
        log_stage("auth", "using VOICE_TOKEN from environment")
    else:
        log_stage("auth", "no VOICE_TOKEN set; generated token:")
        log_stage("auth", f"VOICE_TOKEN = {VOICE_TOKEN}")

    log_stage("startup", "ready")
    yield
    S.clear()


app = FastAPI(title="Sudanese Voice Assistant", lifespan=lifespan)


def transcribe_audio(raw: bytes) -> str:
    log_stage("asr", f"received {len(raw)} bytes")
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=True) as f:
        f.write(raw)
        f.flush()
        # language=None -> Whisper auto-detects. large-v3 handles ~100 languages,
        # so the user may speak Arabic, English, or anything else and still be
        # understood. The reply is always in Sudanese (see SYSTEM_PROMPT).
        #
        # Real recordings (phone speaker into a laptop mic, noisy rooms) are much
        # harder than clean audio: an aggressive VAD can cut most of the speech
        # away, and language detection can misfire and produce gibberish. So we
        # use a forgiving VAD, and if the result looks wrong we retry once,
        # forced to Arabic with no VAD.
        def run(language, use_vad):
            segments, info = S["whisper"].transcribe(
                f.name,
                language=language,
                vad_filter=use_vad,
                vad_parameters={"min_silence_duration_ms": 700} if use_vad else None,
                beam_size=WHISPER_BEAM,
                condition_on_previous_text=False,
            )
            out = " ".join((s.text or "").strip() for s in segments).strip()
            return out, info

        text, info = run(None, True)
        detected = getattr(info, "language", "?")
        prob = getattr(info, "language_probability", 0.0) or 0.0
        secs = getattr(info, "duration", 0.0) or 0.0
        log_stage("asr", f"pass1: {len(text)} chars, lang={detected} ({prob:.2f}), {secs:.1f}s audio")

        # Suspiciously little text for the length of audio, or a very unsure
        # language guess, means the first pass probably failed.
        too_short = secs > 3 and len(text) < max(12, int(secs * 2))
        unsure = prob < 0.55
        if too_short or unsure:
            retry, info2 = run("ar", False)
            log_stage("asr", f"pass2 (forced ar, no vad): {len(retry)} chars")
            if len(retry) > len(text):
                text = retry

        log_stage("asr", f"transcribed {len(text)} chars")
        return text


# Words that suggest the user wants CURRENT information the offline model can't
# know. Only these questions trigger a (paid) web search; normal chat does not.
SEARCH_TRIGGERS = (
    # English
    "today", "tonight", "now", "yesterday", "currently", "latest", "recent",
    "weather", "temperature", "forecast", "score", "match", "game", "won",
    "win", "beat", "vs", "result", "news", "price", "exchange rate",
    # Arabic / Sudanese
    "اليوم", "هسة", "هسع", "أمس", "امبارح", "الآن", "حالياً", "آخر",
    "الطقس", "الجو", "الحرارة", "نتيجة", "مباراة", "ماتش", "كورة",
    "فاز", "كسب", "أخبار", "خبر", "سعر", "الدولار", "الصرف",
)


def needs_search(text: str) -> bool:
    """True if the message looks like it needs live/current information."""
    low = text.lower()
    return any(trigger in low for trigger in SEARCH_TRIGGERS)


def web_search(query: str) -> str:
    """Run `query` on Google via Serper.dev; return the useful text, or "" on failure.

    Serper does the Googling and returns structured JSON. We pull out Google's
    instant answer box (best for scores/weather/prices) plus the top snippets.
    """
    if not SERPER_API_KEY:
        return ""
    try:
        r = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5, "gl": "sd", "hl": "ar"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # never let a search failure break the reply
        log_stage("search", f"failed: {e}")
        return ""

    lines = []
    box = data.get("answerBox")
    if box:
        answer = box.get("answer") or box.get("snippet") or box.get("title")
        if answer:
            lines.append(f"[Answer] {answer}")
    kg = data.get("knowledgeGraph")
    if kg and kg.get("description"):
        lines.append(f"[Info] {kg['description']}")
    for item in data.get("organic", [])[:5]:
        piece = item.get("title", "")
        if item.get("date"):
            piece += f" ({item['date']})"
        if item.get("snippet"):
            piece += f": {item['snippet']}"
        lines.append(f"- {piece}")

    log_stage("search", f"{len(lines)} results for {query[:40]!r}")
    return "\n".join(lines)


def ask_qwen(user_text: str, voice: bool = False) -> str:
    """Ask the LLM. voice=True keeps the answer short: spoken replies should be
    brief, and XTTS synthesis time scales with the length of the text."""
    log_stage("llm", f"asking {QWEN_MODEL} with {len(user_text)} chars")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if voice:
        messages.append({
            "role": "system",
            "content": "دي محادثة صوتية: خلي الرد قصير جداً، جملة واحدة قصيرة بس.",
        })

    # For "live" questions, search the web first and hand the results to the model.
    if needs_search(user_text):
        results = web_search(user_text)
        if results:
            messages.append({
                "role": "system",
                "content": (
                    "LIVE web search results are below. Trust them over your own "
                    "memory: the current date is later than your training, so if "
                    "the results show an event happened, it happened. Use the exact "
                    "scores, numbers and dates. Still answer briefly in spoken "
                    "Sudanese Arabic. Do not make anything up.\n" + results
                ),
            })

    messages.append({"role": "user", "content": user_text})
    # Qwen3 is a "thinking" model: left alone it spends its output on internal
    # reasoning, and once <think>...</think> is stripped little real answer is
    # left (often nothing). Asking it not to think in the prompt does NOT work —
    # it has to be turned off via the API flag.
    # keep_alive=-1 keeps the 20GB model resident in GPU memory. Without it
    # Ollama unloads it after a few idle minutes and the next question pays a
    # ~17s reload - measured as the single biggest source of latency.
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": QWEN_MODEL,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": -1,
            "options": {
                "temperature": 0.4,
                "num_predict": VOICE_NUM_PREDICT if voice else 220,
            },
        },
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    reply = clean_reply(data.get("message", {}).get("content", ""))
    log_stage("llm", f"reply {len(reply)} chars")
    return reply


def synthesize(text: str) -> bytes:
    log_stage("tts", f"synthesizing {len(text)} chars with {S.get('tts_mode', 'unknown')} XTTS")
    if S.get("tts_mode") == "finetuned":
        out = S["tts"].inference(
            text=text,
            language=XTTS_LANG,
            gpt_cond_latent=S["gpt_cond_latent"],
            speaker_embedding=S["speaker_embedding"],
            enable_text_splitting=True,
        )
        wav = out["wav"]
    else:
        wav = S["tts"].tts(
            text=text,
            speaker_wav=XTTS_REFS,
            language=XTTS_LANG,
            **XTTS_PARAMS,
        )
    samples = np.asarray(wav, dtype=np.float32)

    # Opus is ~10x smaller than WAV for speech, so the reply reaches the browser
    # much faster (especially on mobile). Falls back to WAV if this build of
    # libsndfile lacks Opus support, so audio never breaks.
    if AUDIO_FORMAT == "opus":
        try:
            buf = io.BytesIO()
            sf.write(buf, samples, S["tts_sr"], format="OGG", subtype="OPUS")
            data = buf.getvalue()
            log_stage("tts", f"generated {len(data)} opus bytes")
            return data, "audio/ogg"
        except Exception as e:  # noqa: BLE001 - never fail the reply over encoding
            log_stage("tts", f"opus encode failed ({e}); falling back to WAV")

    buf = io.BytesIO()
    sf.write(buf, samples, S["tts_sr"], format="WAV")
    data = buf.getvalue()
    log_stage("tts", f"generated {len(data)} wav bytes")
    return data, "audio/wav"


@app.get("/health")
def health():
    return {
        "status": "ok" if S else "loading",
        "device": DEVICE,
        "models": {
            "asr": WHISPER_ID,
            "llm": QWEN_MODEL,
            "tts": XTTS_ID,
            "xtts_ref": XTTS_REF,
            "xtts_mode": S.get("tts_mode", "loading"),
            "xtts_checkpoint": XTTS_CHECKPOINT or None,
        },
    }


@app.post("/chat", response_model=ChatResp, dependencies=[Depends(require_auth)])
def chat(req: TextReq):
    require_ready()
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "empty text")
    if len(text) > MAX_TEXT:
        raise HTTPException(413, f"text too long (max {MAX_TEXT} chars)")
    try:
        return {"reply_text": ask_qwen(text)}
    except Exception as e:
        raise HTTPException(502, f"Qwen/Ollama error: {e}") from e


@app.post("/transcribe", dependencies=[Depends(require_auth)])
async def transcribe(file: UploadFile = File(...)):
    require_ready()
    return {"text": transcribe_audio(await read_capped(file)), "language": "ar"}


@app.post("/speak", dependencies=[Depends(require_auth)])
def speak(req: TextReq):
    require_ready()
    text = clean_reply(req.text or "")
    if not text:
        raise HTTPException(400, "empty text")
    if len(text) > MAX_TEXT:
        raise HTTPException(413, f"text too long (max {MAX_TEXT} chars)")
    try:
        audio, mime = synthesize(text)
        return Response(audio, media_type=mime)
    except Exception as e:
        log_exception("tts", e)
        raise HTTPException(502, f"XTTS error: {e}") from e


@app.post("/voice", dependencies=[Depends(require_auth)])
async def voice(file: UploadFile = File(...)):
    require_ready()
    try:
        user_text = transcribe_audio(await read_capped(file))
    except Exception as e:
        log_exception("asr", e)
        raise HTTPException(502, f"Whisper error: {e}") from e
    if not user_text:
        raise HTTPException(400, "no speech detected")

    try:
        reply_text = ask_qwen(user_text, voice=True)
    except Exception as e:
        log_exception("llm", e)
        raise HTTPException(502, f"Qwen/Ollama error: {e}") from e

    try:
        audio, mime = synthesize(reply_text)
    except Exception as e:
        log_exception("tts", e)
        raise HTTPException(502, f"XTTS error: {e}") from e
    return JSONResponse(
        {
            "user_text": user_text,
            "reply_text": reply_text,
            "audio_b64": base64.b64encode(audio).decode("ascii"),
            # The browser needs the real format to play it (opus or wav).
            "audio_mime": mime,
        }
    )

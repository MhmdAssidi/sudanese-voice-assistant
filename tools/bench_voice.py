# -*- coding: utf-8 -*-
"""Baseline timing for the voice pipeline: Whisper (ASR) / Qwen (LLM) / XTTS (TTS).

Runs ON THE POD against the local backend, so network latency is excluded and
we measure the models themselves. Prints a per-stage table + totals.
"""
import json
import statistics
import time
import urllib.request

BASE = "http://127.0.0.1:8771"
TOKEN = "sudanvoice-3f8a1c"

SENTENCES = [
    "شنو عاصمة السودان؟",
    "كيف الحال يا زول؟",
    "قول لي حاجة عن نهر النيل.",
]


def post_json(path, payload, raw=False):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "X-Auth-Token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
    return body if raw else json.loads(body)


def post_file(path, filename, content):
    boundary = "----bench" + str(len(content))
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BASE + path, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "X-Auth-Token": TOKEN},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def timed(fn):
    t0 = time.time()
    out = fn()
    return time.time() - t0, out


print("=" * 62)
print(" BASELINE - voice pipeline (measured on the pod)")
print("=" * 62)

rows = []
for i, sent in enumerate(SENTENCES, 1):
    print(f"\n[{i}/{len(SENTENCES)}] {sent}")

    # --- TTS: text -> audio (also gives us test audio for ASR) ---
    tts_s, wav = timed(lambda: post_json("/speak", {"text": sent}, raw=True))
    print(f"    TTS  (XTTS)    : {tts_s:6.2f}s   ({len(wav)/1024:.0f} KB audio)")

    # --- ASR: audio -> text ---
    asr_s, asr = timed(lambda: post_file("/transcribe", "s.wav", wav))
    heard = asr.get("text", "")
    print(f"    ASR  (Whisper) : {asr_s:6.2f}s   heard: {heard[:40]}")

    # --- LLM: text -> reply ---
    llm_s, chat = timed(lambda: post_json("/chat", {"text": sent}))
    reply = chat.get("reply_text", "")
    print(f"    LLM  (Qwen)    : {llm_s:6.2f}s   reply: {reply[:40]}")

    # --- Full /voice round trip ---
    full_s, _ = timed(lambda: post_file("/voice", "s.wav", wav))
    print(f"    FULL /voice    : {full_s:6.2f}s")

    rows.append({"sentence": sent, "tts": tts_s, "asr": asr_s,
                 "llm": llm_s, "full": full_s, "wav_kb": len(wav) / 1024,
                 "heard": heard, "reply": reply})

print("\n" + "=" * 62)
print(" AVERAGES")
print("=" * 62)
for key, label in [("asr", "ASR  (Whisper)"), ("llm", "LLM  (Qwen)"),
                   ("tts", "TTS  (XTTS)"), ("full", "FULL /voice")]:
    vals = [r[key] for r in rows]
    print(f"  {label:16s} {statistics.mean(vals):6.2f}s   "
          f"(min {min(vals):.2f} / max {max(vals):.2f})")
print(f"  {'audio size':16s} {statistics.mean([r['wav_kb'] for r in rows]):6.0f} KB  (WAV)")

with open("/workspace/baseline_voice.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
print("\nSaved -> /workspace/baseline_voice.json")

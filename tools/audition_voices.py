# -*- coding: utf-8 -*-
"""Speak the SAME Sudanese sentence with each candidate reference voice.

Produces one audio file per candidate so they can be compared fairly, plus a
small self-contained HTML player so you can listen and pick without any server.
"""
import base64
import json
import os
import time

import soundfile as sf
import torch
from TTS.api import TTS

CAND = "/workspace/mhmd-va/voices/candidates"
OUT = "/workspace/mhmd-va/voices/audition"
XTTS_ID = "tts_models/multilingual/multi-dataset/xtts_v2"

SENTENCE = "أهلا بيك، أنا المساعد الذكي السوداني. قول لي شنو داير وأنا أساعدك."

os.makedirs(OUT, exist_ok=True)
manifest = json.load(open(os.path.join(CAND, "manifest.json"), encoding="utf-8"))

print("loading XTTS...")
tts = TTS(XTTS_ID).to("cuda" if torch.cuda.is_available() else "cpu")

rows = []
for entry in manifest:
    vid, ref = entry["id"], entry["file"]
    dst = os.path.join(OUT, f"voice{vid}.ogg")
    t0 = time.time()
    wav = tts.tts(text=SENTENCE, speaker_wav=ref, language="ar")
    sf.write(dst, wav, 24000, format="OGG", subtype="OPUS")
    took = time.time() - t0
    size = os.path.getsize(dst)
    print(f"  voice{vid}: {took:5.2f}s  {size/1024:5.1f} KB  (ref: {entry['source']})")
    rows.append({"id": vid, "ogg": dst, "ref": ref, "source": entry["source"],
                 "secs": round(took, 2), "kb": round(size / 1024, 1),
                 "ref_text": entry.get("text", "")})

# --- build a standalone HTML player (audio embedded, works offline) ---
parts = [
    "<!doctype html><meta charset='utf-8'>",
    "<title>Choose your Sudanese voice</title>",
    "<style>body{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;"
    "padding:0 16px;background:#0f1531;color:#f8fafc}"
    "h1{font-size:22px}.s{background:#1b2350;border:1px solid #2c3670;border-radius:14px;"
    "padding:16px 18px;margin:14px 0}.n{font-weight:700;color:#ffaf21;font-size:17px}"
    "audio{width:100%;margin-top:10px}.m{color:#9aa4d0;font-size:13px;margin-top:8px}"
    "p.q{background:#182046;border-right:4px solid #ffaf21;padding:12px 14px;"
    "border-radius:8px;direction:rtl}</style>",
    "<h1>🎧 Choose your Sudanese voice</h1>",
    "<p class='q'>" + SENTENCE + "</p>",
    "<p>Every clip below says the sentence above. Listen and pick the one you like.</p>",
]
for r in rows:
    b64 = base64.b64encode(open(r["ogg"], "rb").read()).decode("ascii")
    parts.append(
        f"<div class='s'><div class='n'>Voice {r['id']}</div>"
        f"<audio controls src='data:audio/ogg;base64,{b64}'></audio>"
        f"<div class='m'>{r['secs']}s to generate &middot; {r['kb']} KB &middot; "
        f"source: {r['source']}</div></div>"
    )
html = os.path.join(OUT, "choose_voice.html")
open(html, "w", encoding="utf-8").write("\n".join(parts))

json.dump(rows, open(os.path.join(OUT, "audition.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\nplayer -> {html}")

# -*- coding: utf-8 -*-
"""Generate the same Sudanese sentences under different XTTS settings.

Produces one audio clip per (setting x sentence) plus a self-contained HTML
page, so the voice can be judged by listening instead of by guessing which
numbers "should" sound better. Also records how long each variant takes, so
quality can be weighed against speed.
"""
import base64
import json
import os
import time

import soundfile as sf
import torch
from TTS.api import TTS

OUT = "/workspace/voice_compare"
XTTS_ID = "tts_models/multilingual/multi-dataset/xtts_v2"
REF = "/workspace/mhmd_voice/voice.wav"
EXTRAS = [f"/workspace/mhmd_voice/voice_extra{i}.wav" for i in (1, 2, 3)]
MULTI = [REF] + [p for p in EXTRAS if os.path.exists(p)]

SENTENCES = [
    "أهلا بيك، أنا المساعد السوداني. قول لي شنو داير وأنا أساعدك.",
    "الخرطوم عاصمة السودان، وهي أكبر مدينة في البلد.",
]

# Each variant: what we are testing, the reference clips, and the knobs.
VARIANTS = [
    ("A. current (single clip, defaults)", [REF],
     {}),
    ("B. multi-clip, same settings", MULTI,
     {}),
    ("C. multi-clip, steadier", MULTI,
     {"temperature": 0.60, "repetition_penalty": 6.0, "top_k": 40, "top_p": 0.80,
      "gpt_cond_len": 12}),
    ("D. multi-clip, more expressive", MULTI,
     {"temperature": 0.80, "repetition_penalty": 4.0, "top_k": 60, "top_p": 0.90,
      "gpt_cond_len": 10}),
    ("E. multi-clip, longest conditioning", MULTI,
     {"temperature": 0.70, "repetition_penalty": 5.0, "top_k": 50, "top_p": 0.85,
      "gpt_cond_len": 30}),
]

os.makedirs(OUT, exist_ok=True)
print(f"reference clips available: {len(MULTI)}")
print("loading XTTS...")
tts = TTS(XTTS_ID).to("cuda" if torch.cuda.is_available() else "cpu")

rows = []
for vi, (label, refs, params) in enumerate(VARIANTS, 1):
    for si, sentence in enumerate(SENTENCES, 1):
        dst = os.path.join(OUT, f"v{vi}_s{si}.ogg")
        t0 = time.time()
        wav = tts.tts(text=sentence, speaker_wav=refs, language="ar",
                      enable_text_splitting=True, **params)
        sf.write(dst, wav, 24000, format="OGG", subtype="OPUS")
        took = time.time() - t0
        rows.append({"variant": vi, "label": label, "sentence": si,
                     "file": dst, "secs": round(took, 2),
                     "kb": round(os.path.getsize(dst) / 1024, 1),
                     "refs": len(refs), "params": params})
        print(f"  {label} | sentence {si}: {took:5.2f}s")

# --- standalone HTML player -------------------------------------------------
parts = [
    "<!doctype html><meta charset='utf-8'><title>Compare voice settings</title>",
    "<style>body{font-family:system-ui,sans-serif;max-width:820px;margin:36px auto;"
    "padding:0 16px;background:#0f1531;color:#f8fafc}h1{font-size:22px}"
    ".v{background:#1b2350;border:1px solid #2c3670;border-radius:14px;padding:16px 18px;margin:14px 0}"
    ".n{font-weight:800;color:#ffaf21;font-size:17px}"
    "audio{width:100%;margin-top:8px}.m{color:#9aa4d0;font-size:12.5px;margin-top:8px}"
    "p.q{background:#182046;border-right:4px solid #ffaf21;padding:10px 14px;"
    "border-radius:8px;direction:rtl;margin:6px 0}</style>",
    "<h1>🎧 Which voice setting sounds best?</h1>",
    "<p>Every option says the same two sentences. Listen and pick the letter you prefer.</p>",
]
for vi, (label, refs, params) in enumerate(VARIANTS, 1):
    mine = [r for r in rows if r["variant"] == vi]
    avg = round(sum(r["secs"] for r in mine) / max(1, len(mine)), 2)
    parts.append(f"<div class='v'><div class='n'>{label}</div>")
    for r in mine:
        b64 = base64.b64encode(open(r["file"], "rb").read()).decode("ascii")
        parts.append(f"<p class='q'>{SENTENCES[r['sentence'] - 1]}</p>"
                     f"<audio controls src='data:audio/ogg;base64,{b64}'></audio>")
    parts.append(f"<div class='m'>{len(refs)} reference clip(s) &middot; avg {avg}s to generate"
                 f"{' &middot; ' + json.dumps(params) if params else ' &middot; XTTS defaults'}</div></div>")

open(os.path.join(OUT, "compare.html"), "w", encoding="utf-8").write("\n".join(parts))
json.dump(rows, open(os.path.join(OUT, "compare.json"), "w"), ensure_ascii=False, indent=2)
print(f"\nplayer -> {OUT}/compare.html")

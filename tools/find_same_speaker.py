# -*- coding: utf-8 -*-
"""Find more clips of the SAME speaker as the project's reference voice.

XTTS clones a voice better when given several clips of one speaker instead of
a single clip. The dataset has no speaker labels, so we compare voices directly
using XTTS's own speaker encoder and keep the closest matches.
"""
import json
import os
import shutil

import numpy as np
import torch
from TTS.api import TTS

WAVS = "/workspace/sudan_dataset/xtts_dataset/wavs"
REF = os.environ.get("XTTS_REF", "/workspace/mhmd_voice/voice.wav")
OUT = "/workspace/mhmd_voice"
XTTS_ID = "tts_models/multilingual/multi-dataset/xtts_v2"

SCAN_LIMIT = int(os.environ.get("SCAN_LIMIT", "700"))  # clips to compare
KEEP = int(os.environ.get("KEEP", "3"))                # extra clips to keep
MIN_SEC, MAX_SEC = 6.0, 14.0


def embed(model, path):
    """Speaker embedding for one clip (None if it cannot be used)."""
    try:
        gpt_cond, spk = model.get_conditioning_latents(audio_path=[path])
        v = spk.detach().cpu().numpy().reshape(-1)
        n = np.linalg.norm(v)
        return v / n if n else None
    except Exception:
        return None


def main():
    print("loading XTTS speaker encoder...")
    api = TTS(XTTS_ID).to("cuda" if torch.cuda.is_available() else "cpu")
    model = api.synthesizer.tts_model

    ref_vec = embed(model, REF)
    if ref_vec is None:
        raise SystemExit(f"could not read reference voice: {REF}")
    print(f"reference: {REF}")

    import soundfile as sf
    files = sorted(f for f in os.listdir(WAVS) if f.endswith(".wav"))
    step = max(1, len(files) // SCAN_LIMIT)
    files = files[::step][:SCAN_LIMIT]
    print(f"comparing {len(files)} clips...")

    scored = []
    for i, name in enumerate(files):
        p = os.path.join(WAVS, name)
        try:
            info = sf.info(p)
            if not (MIN_SEC <= info.duration <= MAX_SEC):
                continue
        except Exception:
            continue
        v = embed(model, p)
        if v is None:
            continue
        sim = float(np.dot(ref_vec, v))       # cosine similarity
        scored.append((sim, name, round(info.duration, 2)))
        if (i + 1) % 100 == 0:
            print(f"  ...{i + 1}/{len(files)}")

    scored.sort(key=lambda x: -x[0])
    print(f"\ntop matches (1.00 = identical voice):")
    kept = []
    for sim, name, dur in scored[:KEEP + 2]:
        print(f"  {sim:.3f}  {dur:5.1f}s  {name}")

    # Keep the closest few, but only if they are genuinely similar.
    for sim, name, dur in scored:
        if len(kept) >= KEEP:
            break
        if sim < 0.75:            # too different - probably another speaker
            continue
        dst = os.path.join(OUT, f"voice_extra{len(kept) + 1}.wav")
        shutil.copy(os.path.join(WAVS, name), dst)
        kept.append({"file": dst, "source": name, "similarity": round(sim, 3),
                     "seconds": dur})

    refs = [REF] + [k["file"] for k in kept]
    json.dump({"reference": REF, "extras": kept, "XTTS_REFS": ",".join(refs)},
              open(os.path.join(OUT, "voice_set.json"), "w"), indent=2)

    print(f"\nkept {len(kept)} extra clip(s) of the same speaker")
    print("XTTS_REFS=" + ",".join(refs))


if __name__ == "__main__":
    main()

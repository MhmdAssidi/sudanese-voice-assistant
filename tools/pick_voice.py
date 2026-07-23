# -*- coding: utf-8 -*-
"""Find good XTTS reference-voice candidates in the Sudanese dataset.

XTTS clones whatever speaker it hears in the reference audio, so the quality of
that clip decides how good the assistant sounds. This scores every clip for
duration, loudness, clipping and silence, groups them so we do not offer five
clips of the same person, and writes the best candidates out for auditioning.
"""
import json
import os
import wave

import numpy as np
import soundfile as sf

WAVS = "/workspace/sudan_dataset/xtts_dataset/wavs"
META = "/workspace/sudan_dataset/xtts_dataset/metadata.csv"
OUT = "/workspace/mhmd-va/voices/candidates"

# XTTS works best with a clip long enough to capture the voice, but clean.
MIN_SEC, MAX_SEC = 7.0, 14.0
TOP_N = 8


def load_texts():
    texts = {}
    if os.path.exists(META):
        with open(META, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("|")
                if len(parts) >= 2:
                    texts[os.path.basename(parts[0])] = parts[1]
    return texts


def score(path):
    """Return (score, info) for one wav, or None if unusable."""
    try:
        with wave.open(path, "rb") as w:
            frames, rate = w.getnframes(), w.getframerate()
            dur = frames / float(rate)
        if not (MIN_SEC <= dur <= MAX_SEC):
            return None
        data, sr = sf.read(path, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if data.size == 0:
            return None

        peak = float(np.max(np.abs(data)))
        if peak < 1e-4:
            return None
        rms = float(np.sqrt(np.mean(data ** 2)))
        clipped = float(np.mean(np.abs(data) > 0.99))
        silence = float(np.mean(np.abs(data) < 0.005))

        # Prefer: healthy loudness, no clipping, not mostly silence.
        s = 0.0
        s += min(rms / 0.12, 1.0) * 40          # loudness (up to 40)
        s -= clipped * 300                       # clipping is very bad
        s -= max(0.0, silence - 0.35) * 60       # some silence ok, lots is not
        s += min(dur / MAX_SEC, 1.0) * 20        # longer (within range) is better
        if peak > 0.999:
            s -= 15
        return s, {"dur": round(dur, 2), "rms": round(rms, 4),
                   "clipped": round(clipped, 5), "silence": round(silence, 3),
                   "sr": sr}
    except Exception:
        return None


def main():
    texts = load_texts()
    files = sorted(os.listdir(WAVS))
    print(f"scanning {len(files)} clips (keeping {MIN_SEC}-{MAX_SEC}s)...")

    scored = []
    for i, name in enumerate(files):
        if not name.lower().endswith(".wav"):
            continue
        r = score(os.path.join(WAVS, name))
        if r:
            scored.append((r[0], name, r[1]))
        if (i + 1) % 800 == 0:
            print(f"  ...{i + 1}/{len(files)}  usable so far: {len(scored)}")

    scored.sort(key=lambda x: -x[0])
    print(f"\nusable clips: {len(scored)}")

    # Spread picks across the dataset so we are less likely to pick the same
    # speaker repeatedly (the dataset is ordered by source episode).
    chosen, seen_prefix = [], set()
    for s, name, info in scored:
        p = name[:2]
        if p in seen_prefix:
            continue
        seen_prefix.add(p)
        chosen.append((s, name, info))
        if len(chosen) >= TOP_N:
            break
    for s, name, info in scored:            # top up if we ran out of variety
        if len(chosen) >= TOP_N:
            break
        if all(name != c[1] for c in chosen):
            chosen.append((s, name, info))

    os.makedirs(OUT, exist_ok=True)
    manifest = []
    print(f"\n{'#':<3} {'score':>6}  {'sec':>5}  {'rms':>6}  file")
    for idx, (s, name, info) in enumerate(chosen, 1):
        src = os.path.join(WAVS, name)
        dst = os.path.join(OUT, f"voice{idx}.wav")
        data, sr = sf.read(src, dtype="float32")
        sf.write(dst, data, sr)
        print(f"{idx:<3} {s:6.1f}  {info['dur']:5.1f}  {info['rms']:6.4f}  {name}")
        manifest.append({"id": idx, "file": dst, "source": name,
                         "score": round(s, 2), **info,
                         "text": texts.get(name, "")})

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\ncopied {len(manifest)} candidates -> {OUT}")


if __name__ == "__main__":
    main()

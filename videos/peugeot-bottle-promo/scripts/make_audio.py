"""Promo soundtrack: synthesized 128 BPM bed (D minor) + bundled SFX on each visual hit.

Times below are the composition's own times in index.html (bar(b, beat) = b*BAR + beat*BEAT),
so every hit lands on the frame its animation fires.

Usage: python3 scripts/make_audio.py   (needs numpy + ffmpeg)
Output: assets/audio/promo-mix.wav (48 kHz, 16-bit stereo, 15.0 s)
"""

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT.parent.parent / ".agents/skills/media-use/audio/assets/sfx"
OUT = ROOT / "assets/audio/promo-mix.wav"

SR = 48000
BPM = 128
BEAT = 60 / BPM
BAR = 4 * BEAT
DURATION = 15.0
N = int(SR * DURATION)


def bar(b, beat=0.0):
    return b * BAR + beat * BEAT


# ── synthesis helpers ─────────────────────────────────────────────────────
def env_exp(n, decay):
    return np.exp(-np.arange(n) / SR / decay)


def noise(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def highpass(x, a=0.85):
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = a * (y[i - 1] + x[i] - x[i - 1])
    return y


def lowpass(x, a):
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def kick(sub=False):
    n = int((0.6 if sub else 0.32) * SR)
    t = np.arange(n) / SR
    freq = (38 if sub else 46) + 90 * np.exp(-t / 0.04)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env_exp(n, 0.28 if sub else 0.11)
    return body + np.exp(-t / 0.002) * 0.25


HAT = highpass(noise(int(0.04 * SR), 7)) * env_exp(int(0.04 * SR), 0.01)


def clap(seed):
    n = int(0.22 * SR)
    e = np.zeros(n)
    for k, off in enumerate((0.0, 0.011, 0.022)):
        i = int(off * SR)
        e[i:] += env_exp(n - i, 0.008 if k < 2 else 0.07)
    return highpass(noise(n, seed), 0.7) * e * 0.55


def saw(freq, n, harmonics=8):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * freq * h * t) / h for h in range(1, harmonics + 1)) * (2 / np.pi)


def bass_note(freq, length):
    n = int(length * SR)
    return lowpass(saw(freq, n), 0.07) * np.minimum(1, np.arange(n) / (0.004 * SR)) * env_exp(n, length * 0.55) * 0.9


def pad(freqs, length, attack=0.25):
    n = int(length * SR)
    tone = sum(lowpass(saw(f, n, 6) + saw(f * 1.004, n, 6), 0.03) for f in freqs) / (2 * len(freqs))
    env = np.minimum(1, np.arange(n) / (attack * SR)) * np.minimum(1, (n - np.arange(n)) / (0.4 * SR))
    return tone * env * 0.6


def splash(seed=11):
    """Water splash: filtered noise burst with a bubbly, decaying tail."""
    n = int(1.1 * SR)
    hit_ = highpass(noise(n, seed), 0.6) * env_exp(n, 0.09)
    tail = lowpass(noise(n, seed + 1), 0.25) * env_exp(n, 0.35) * 0.6
    t = np.arange(n) / SR
    bubbles = sum(
        np.sin(2 * np.pi * (500 + 900 * k / 7) * t * (1 + 0.6 * t)) * np.exp(-((t - 0.05 - 0.08 * k) ** 2) / 0.0006) * 0.18 for k in range(7)
    )
    return hit_ + tail + bubbles


# ── mixing ───────────────────────────────────────────────────────────────
bed = np.zeros(N)
sfx = np.zeros((N, 2))
events = []


def place(buf, sig, t, gain=1.0):
    i = int(round(t * SR))
    if i < 0:
        sig, i = sig[-i:], 0
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i : i + len(sig)] += gain * sig


_cache = {}


def load_sfx(name):
    if name not in _cache:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(SFX_DIR / f"{name}.mp3"), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
            check=True,
            capture_output=True,
        ).stdout
        _cache[name] = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    return _cache[name]


# Lead-in of each bundled file (measured: time to its first loud transient, or to the
# peak for whooshes) — subtracted so the audible hit lands on the visual frame.
LEAD = {"impact-bass-1": 0.050, "impact-bass-2": 0.023, "whoosh": 0.161, "whoosh-short": 0.161}


def hit(name, t, gain=0.6, trim=None, fade=0.05):
    t -= LEAD.get(name, 0.0)
    s = load_sfx(name).copy()
    if trim:
        s = s[: int(trim * SR)]
        f = min(len(s), int(fade * SR))
        s[-f:] *= np.linspace(1, 0, f)[:, None]
    place(sfx, s, t, gain)
    events.append({"sfx": name, "t": round(t, 3)})


def mono_hit(sig, t, gain, label):
    place(sfx, np.stack([sig, sig], axis=1), t, gain)
    events.append({"sfx": label, "t": round(t, 3)})


# ── bed: Dm  Bb  F  C  (intro 2 bars, groove 4 bars, outro 2 bars) ───────
D2, Bb1, F2, C2 = 73.42, 58.27, 87.31, 65.41
roots = [D2, D2, D2, Bb1, F2, C2, D2, D2]
chords = {
    "Dm": [293.66, 349.23, 440.0],
    "Bb": [233.08, 293.66, 349.23],
    "F": [261.63, 349.23, 440.0],
    "C": [261.63, 329.63, 392.0],
}
prog = ["Dm", "Dm", "Dm", "Bb", "F", "C", "Dm", "Dm"]

for b in range(8):
    b0 = bar(b)
    intro, outro = b < 2, b >= 6
    if intro:  # tension: sub pulse on 1 and 3, 16th ticks rising in level
        for beat in (0, 2):
            place(bed, kick(sub=True), bar(b, beat), 0.45)
        for k in range(16):
            place(bed, HAT, b0 + k * BEAT / 4, 0.05 + 0.1 * (b * 16 + k) / 32)
        place(bed, pad(chords["Dm"], BAR), b0, 0.35)
        continue
    if outro:
        if b == 6:
            place(bed, kick(sub=True), b0, 0.9)
            place(bed, pad(chords["Dm"], 2 * BAR, attack=0.05), b0, 0.6)
            place(bed, bass_note(D2, 2 * BAR), b0, 0.6)
        for k in range(8 if b == 6 else 4):
            place(bed, HAT, b0 + k * BEAT / 2, 0.08)
        continue
    for beat in range(4):
        t = bar(b, beat)
        place(bed, kick(), t, 0.95)
        if beat in (1, 3):
            place(bed, clap(b * 4 + beat), t, 0.7)
        for half in (0, 1):
            place(bed, HAT, t + half * BEAT / 2, 0.22 if half else 0.1)
        place(bed, bass_note(roots[b], BEAT / 2 * 0.95), t + BEAT / 2, 0.55)
    place(bed, pad(chords[prog[b]], BAR, attack=0.02), b0, 0.3)

# snare fill into the end card
for k in range(4):
    place(bed, clap(200 + k), bar(6) - BEAT + k * BEAT / 4, 0.3 + 0.12 * k)

# ── SFX on visual events (seconds = index.html timeline) ─────────────────
hit("whoosh-cinematic", 0.05, 0.35, trim=1.0, fade=0.4)  # light slit opens
hit("sparkle", bar(0, 1.2), 0.25, trim=0.8, fade=0.3)  # macro light sweep
hit("impact-bass-1", bar(0, 2), 0.5, trim=0.9)  # DRIVE
hit("whoosh-short", bar(1) - 0.05, 0.55)  # whip to cap
hit("whoosh", bar(1, 1) - 0.03, 0.4)  # YOUR
hit("impact-bass-1", bar(1, 1), 0.35, trim=0.6)
hit("whoosh-short", bar(1, 2) - 0.05, 0.55)  # whip to tagline
hit("impact-bass-2", bar(1, 3), 0.5, trim=0.9)  # FUTURE
riser = load_sfx("riser")
tail = riser[-int(1.4 * SR) :]
place(sfx, tail, bar(2) - len(tail) / SR, 0.35)  # riser into the flash
events.append({"sfx": "riser(tail)", "t": round(bar(2) - len(tail) / SR, 3)})
hit("impact-bass-2", bar(2), 0.85, trim=1.6, fade=0.6)  # flash / drop
hit("whoosh", bar(2) + 0.02, 0.5)  # bottle flies up
mono_hit(splash(), bar(2, 1) - 0.05, 0.55, "splash(synth)")  # landing splash
hit("impact-bass-1", bar(2, 1) - 0.03, 0.45, trim=0.9)
for i in range(7):
    hit("key-press", bar(2, 2) + i * 0.05, 0.16)  # wordmark letters
hit("chime", bar(3), 0.18, trim=1.2, fade=0.6)  # glint 1
hit("sparkle", bar(3, 3), 0.22, trim=0.9, fade=0.4)  # glint 2
hit("whoosh-short", bar(4), 0.45)  # bottle slides left for callouts
for i in range(3):
    hit("pop", bar(4) + 0.3 + i * BEAT * 0.5, 0.35)  # callout dots
    hit("click-soft", bar(4) + 0.6 + i * BEAT * 0.5, 0.3)  # labels
hit("whoosh-cinematic", bar(5) - 0.2, 0.5, trim=1.2, fade=0.5)  # zoom-out reveal
hit("sparkle", bar(5, 2), 0.25, trim=1.0, fade=0.4)  # light sweep
hit("whoosh", bar(6) - 0.2, 0.5)  # into end card
hit("impact-bass-2", bar(6), 0.8, trim=2.0, fade=0.8)
hit("whoosh-short", bar(6, 1), 0.3)  # PEUGEOT
for i in range(3):
    hit("click-soft", bar(6, 3) + i * 0.09, 0.3)  # tricolor
hit("chime", bar(7), 0.3, trim=2.0, fade=0.8)  # final glint

# ── master ───────────────────────────────────────────────────────────────
mix = np.stack([bed, bed], axis=1) * 0.5 + sfx
fade_n = int(0.5 * SR)
mix[-fade_n:] *= np.linspace(1, 0, fade_n)[:, None] ** 2
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= 0.6 / np.max(np.abs(mix))

OUT.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(OUT)],
    input=(mix * 32767).astype("<i2").tobytes(),
    check=True,
)
(ROOT / "assets/audio/events.json").write_text(json.dumps({"bpm": BPM, "bar": BAR, "events": events}, indent=1))
print(f"wrote {OUT.relative_to(ROOT)} · {DURATION}s · {len(events)} sfx hits")

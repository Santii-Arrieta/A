"""Build the reel soundtrack: a synthesized 144 BPM bed + bundled SFX hits.

Every SFX is placed at its visual event's source time (the 15 s authoring timeline in
index.html) mapped through the same piecewise-linear warp the composition uses, so each
hit lands on the frame its animation fires. Scene cuts fall on bar lines by construction.

Usage: python3 scripts/make_audio.py   (needs numpy + ffmpeg on PATH)
Output: assets/audio/reel-mix.wav (48 kHz, 16-bit, stereo, 10.0 s)
"""

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT.parent.parent / ".agents/skills/media-use/audio/assets/sfx"
OUT = ROOT / "assets/audio/reel-mix.wav"

SR = 48000
BPM = 144
BEAT = 60 / BPM
BAR = 4 * BEAT
DURATION = 10.0
N = int(SR * DURATION)

# Must match SCENES / SRC_KNOTS in index.html.
SRC_KNOTS = [0.0, 2.85, 5.75, 8.45, 10.85, 13.2, 15.0]
OUT_KNOTS = [i * BAR for i in range(len(SRC_KNOTS))]


def to_out(src_t):
    """Source (authoring) seconds → output seconds: inverse of the composition's warp."""
    return float(np.interp(src_t, SRC_KNOTS, OUT_KNOTS))


# ── synthesis helpers ─────────────────────────────────────────────────────
def env_exp(n, decay):
    t = np.arange(n) / SR
    return np.exp(-t / decay)


def kick(gain=1.0):
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    freq = 45 + 95 * np.exp(-t / 0.035)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    click = np.exp(-t / 0.002) * 0.3
    return gain * (np.sin(phase) * env_exp(n, 0.11) + click)


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


HAT = highpass(noise(int(0.045 * SR), 7)) * env_exp(int(0.045 * SR), 0.012)


def clap(seed):
    n = int(0.22 * SR)
    burst = highpass(noise(n, seed), 0.7)
    e = np.zeros(n)
    for k, off in enumerate((0.0, 0.011, 0.022)):  # three quick transients = a clap
        i = int(off * SR)
        e[i:] += env_exp(n - i, 0.008 if k < 2 else 0.06)
    return burst * e * 0.55


def saw(freq, n, harmonics=10):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * freq * h * t) / h for h in range(1, harmonics + 1)) * (2 / np.pi)


def bass_note(freq, length):
    n = int(length * SR)
    tone = lowpass(saw(freq, n, 8), 0.08)
    attack = np.minimum(1, np.arange(n) / (0.004 * SR))
    return tone * attack * env_exp(n, length * 0.55) * 0.9


def chord_stab(freqs, length):
    n = int(length * SR)
    tone = sum(lowpass(saw(f, n, 6), 0.05) for f in freqs) / len(freqs)
    attack = np.minimum(1, np.arange(n) / (0.01 * SR))
    return tone * attack * env_exp(n, length * 0.4) * 0.5


# ── mixing helpers ───────────────────────────────────────────────────────
bed = np.zeros(N)
sfx = np.zeros((N, 2))
events = []


def place(buf, sig, t, gain=1.0):
    i = int(round(t * SR))
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


def hit(name, src_t=None, gain=0.6, trim=None, out_t=None, offset=0.0, fade=0.05):
    """Place a bundled SFX at a source-time event (or an explicit output time)."""
    s = load_sfx(name)[int(offset * SR) :].copy()
    if trim:
        s = s[: int(trim * SR)]
        f = min(len(s), int(fade * SR))
        s[-f:] *= np.linspace(1, 0, f)[:, None]
    t = out_t if out_t is not None else to_out(src_t)
    place(sfx, s, t, gain)
    events.append({"sfx": name, "t": round(t, 3), "src": src_t})


# ── the bed: 6 bars, one per scene ───────────────────────────────────────
A1, F1, C2, G1 = 55.0, 43.65, 65.41, 49.0
roots = [A1, F1, C2, G1, A1, A1]
chords = [
    [220.0, 261.63, 329.63],  # Am
    [174.61, 220.0, 261.63],  # F
    [196.0, 261.63, 329.63],  # C
    [196.0, 246.94, 293.66],  # G
    [220.0, 261.63, 329.63],  # Am
    [220.0, 261.63, 329.63],  # Am (held under the lockup)
]
for bar in range(6):
    b0 = bar * BAR
    last = bar == 5
    for beat in range(4):
        t = b0 + beat * BEAT
        if not last or beat == 0:
            place(bed, kick(), t, 0.95)
        if beat in (1, 3) and not last:
            place(bed, clap(bar * 4 + beat), t, 0.8)
        for half in (0, 1):  # hats on every 8th, accented off-beats
            if last and beat > 0:
                continue
            place(bed, HAT, t + half * BEAT / 2, 0.22 if half else 0.1)
        # pumping bass on the off-beat 8ths
        if not last:
            place(bed, bass_note(roots[bar], BEAT / 2 * 0.95), t + BEAT / 2, 0.55)
    place(bed, chord_stab(chords[bar], BAR * (1.0 if last else 0.9)), b0, 0.45 if last else 0.28)
    if last:
        place(bed, bass_note(roots[bar], BAR), b0, 0.75)

# 16th-note snare fill into the final bar (under the overexposure flash)
for k in range(4):
    place(bed, clap(100 + k), 5 * BAR - BEAT + k * BEAT / 4, 0.35 + 0.12 * k)

# ── SFX on the visual events (source seconds from index.html) ────────────
# 01 kinetic type
hit("impact-bass-1", 0.15, 0.55, trim=0.9)  # MOTION slam
hit("whoosh-short", 0.75, 0.45)  # IS A side-snap
hit("glitch-3", 1.35, 0.4, trim=0.35)  # LANGUAGE. glitch-stretch
hit("click-soft", 1.75, 0.45)  # underline
hit("glitch-1", 2.2, 0.3, trim=0.16)  # emphasis burst
# 02 depth
hit("whoosh", 2.72, 0.55)  # zoom-through
hit("whoosh-cinematic", 2.9, 0.4, trim=1.1, fade=0.4)  # glyph cloud assembling
hit("impact-bass-2", 4.0, 0.45, trim=1.0)  # depth extrudes
for i in range(3):
    hit("key-press", 4.3 + i * 0.08, 0.3)  # meta lines
# 03 easing
hit("whoosh-short", 5.55, 0.55)  # block wipe in
hit("whoosh", 5.83, 0.4)  # block wipe out
hit("pop", 6.3, 0.45)  # puck appears
for k in range(11):  # one tick per onion-skin ghost (equal time steps, expo.out spacing)
    hit("click-soft", 6.65 + 1.3 * k / 10, 0.28)
hit("ping", 7.95, 0.4, trim=0.9)  # puck lands
# 04 data
hit("whoosh", 8.32, 0.55)
for k in range(1, 11):  # count-up ticks every 30 frames, timed on the power3.out ease
    p = k / 10
    x = 1 - (1 - p) ** (1 / 3)
    hit("key-press", 8.5 + 1.6 * x, 0.18 + 0.02 * k)
hit("pop", 9.7, 0.5)  # YOU ARE HERE pin
# 05 camera
hit("whoosh-cinematic", 10.72, 0.55, trim=1.2, fade=0.5)  # zoom-through + dive
hit("impact-bass-1", 11.3, 0.4, trim=0.9)  # landing
# riser into the flash: the tail of riser.mp3 ends exactly on the cut into scene 06
riser = load_sfx("riser")
tail = riser[-int(1.6 * SR) :]
place(sfx, tail, to_out(13.2) - len(tail) / SR, 0.35)
events.append({"sfx": "riser(tail)", "t": round(to_out(13.2) - len(tail) / SR, 3), "src": None})
# 06 signature
hit("impact-bass-2", 13.2, 0.85, trim=1.6, fade=0.6)  # the cut out of the flash
for i in range(6):
    hit("key-press", 13.3 + i * 0.055, 0.22)  # letters whip in
hit("whoosh-short", 13.75, 0.35)  # underline
hit("sparkle", 14.0, 0.45, trim=1.4, fade=0.5)  # confetti

# ── master ───────────────────────────────────────────────────────────────
mix = np.stack([bed, bed], axis=1) * 0.55 + sfx
fade_n = int(0.35 * SR)
mix[-fade_n:] *= np.linspace(1, 0, fade_n)[:, None]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # soft clip
mix *= 0.6 / np.max(np.abs(mix))  # ≈ -14 LUFS integrated, peak ≈ -4.4 dBFS

OUT.parent.mkdir(parents=True, exist_ok=True)
pcm = (mix * 32767).astype("<i2").tobytes()
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(OUT)],
    input=pcm,
    check=True,
)
(ROOT / "assets/audio/events.json").write_text(json.dumps({"bpm": BPM, "bar": BAR, "events": events}, indent=1))
print(f"wrote {OUT.relative_to(ROOT)} · {DURATION}s · {len(events)} sfx hits · bars at {[round(k, 3) for k in OUT_KNOTS]}")

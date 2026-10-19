"""Soundtrack for the Safe Query reel: dark 128 BPM electronic bed + SFX on the visual events.

16 bars × 1.875 s = 30 s, one plate = 2 bars. Arc: sparse intro (P1) → kick enters (P2) →
drop in the tunnel (P3–P4) → breakdown on the hash (P5) → rebuild (P6) → full with arp (P7) →
finale hits (P8). Event times mirror index.html (bar(b, beat) = b*BAR + beat*BEAT).

Usage: python3 scripts/make_audio.py   (needs numpy + ffmpeg)
Output: assets/audio/secure-query.wav (48 kHz, 16-bit stereo, 30.0 s)
"""

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT.parent.parent / ".agents/skills/media-use/audio/assets/sfx"
OUT = ROOT / "assets/audio/secure-query.wav"

SR = 48000
BPM = 128
BEAT = 60 / BPM
BAR = 4 * BEAT
DURATION = 30.0
N = int(SR * DURATION)


def bar(b, beat=0.0):
    return b * BAR + beat * BEAT


def plate(n):
    return bar(2 * (n - 1))


# ── synthesis ────────────────────────────────────────────────────────────
def env_exp(n, decay):
    return np.exp(-np.arange(n) / SR / decay)


def noise(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def hp(x, a=0.85):
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = a * (y[i - 1] + x[i] - x[i - 1])
    return y


def lp(x, a):
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def kick(sub=False):
    n = int((0.55 if sub else 0.32) * SR)
    t = np.arange(n) / SR
    f = (40 if sub else 47) + 110 * np.exp(-t / 0.035)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.26 if sub else 0.12) + np.exp(-t / 0.0015) * 0.3


HAT = hp(noise(int(0.035 * SR), 7)) * env_exp(int(0.035 * SR), 0.008)
OHAT = hp(noise(int(0.17 * SR), 8)) * env_exp(int(0.17 * SR), 0.05)


def clap(seed):
    n = int(0.2 * SR)
    e = np.zeros(n)
    for k, off in enumerate((0.0, 0.01, 0.02)):
        i = int(off * SR)
        e[i:] += env_exp(n - i, 0.007 if k < 2 else 0.06)
    return hp(noise(n, seed), 0.7) * e * 0.6


def saw(freq, n, h=10):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, h + 1)) * (2 / np.pi)


def bass(freq, length, cutoff=0.09):
    n = int(length * SR)
    return lp(saw(freq, n, 8), cutoff) * np.minimum(1, np.arange(n) / (0.002 * SR)) * env_exp(n, 0.08)


def pluck(freq, length=0.18):
    n = int(length * SR)
    tone = saw(freq, n, 7) * 0.6 + np.sign(np.sin(2 * np.pi * freq * np.arange(n) / SR)) * 0.2
    return lp(tone, 0.16) * env_exp(n, 0.07)


def pad(freqs, length, attack=0.3):
    n = int(length * SR)
    tone = sum(lp(saw(f, n, 6) + saw(f * 1.006, n, 6), 0.025) for f in freqs) / (2 * len(freqs))
    env = np.minimum(1, np.arange(n) / (attack * SR)) * np.minimum(1, (n - np.arange(n)) / (0.5 * SR))
    return tone * env


def tick_sweep(length, f0=900, f1=4200, rate0=8, rate1=40, seed=3):
    """A rolling counter: clicks that speed up and rise in pitch (for the 0→4096 rounds counter)."""
    n = int(length * SR)
    out = np.zeros(n)
    t = 0.0
    k = 0
    while t < length:
        p = t / length
        f = f0 + (f1 - f0) * p
        m = int(0.012 * SR)
        tt = np.arange(m) / SR
        click = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.003)
        i = int(t * SR)
        out[i : i + m] += click[: max(0, min(m, n - i))] * (0.5 + 0.5 * p)
        t += 1 / (rate0 + (rate1 - rate0) * p * p)
        k += 1
    return out


# ── buses ────────────────────────────────────────────────────────────────
drums = np.zeros(N)
music = np.zeros(N)
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


# ── arrangement: E minor, one chord per plate ────────────────────────────
E2, C2, D2, B1 = 82.41, 65.41, 73.42, 61.74
CH = {
    "Em": [329.63, 392.0, 493.88],
    "C": [261.63, 329.63, 392.0],
    "D": [293.66, 369.99, 440.0],
    "Bm": [246.94, 293.66, 369.99],
}
PLAN = {  # plate: (root, chord, kick, clap, bass16, arp)
    1: (E2, "Em", "sub", False, False, False),
    2: (E2, "Em", "four", False, True, False),
    3: (C2, "C", "four", True, True, False),
    4: (D2, "D", "four", True, True, False),
    5: (E2, "Em", None, False, False, True),
    6: (C2, "C", "four", True, True, False),
    7: (D2, "D", "four", True, True, True),
    8: (E2, "Em", "end", False, False, False),
}
ARP = [659.25, 783.99, 987.77, 783.99, 1318.51, 987.77, 783.99, 987.77]
kicks = []
for pl, (root, chord, kmode, clp, b16, arp) in PLAN.items():
    t0 = plate(pl)
    for b in range(8):  # 8 beats per plate
        t = t0 + b * BEAT
        if kmode == "four" or (kmode == "sub" and b % 2 == 0) or (kmode == "end" and b == 0):
            place(drums, kick(sub=kmode in ("sub", "end")), t, 1.0 if kmode == "four" else 0.8)
            kicks.append(t)
        if kmode == "four":
            place(drums, OHAT, t + BEAT / 2, 0.12)
            for s16 in range(4):
                place(drums, HAT, t + s16 * BEAT / 4, 0.14 if s16 % 2 else 0.06)
        elif pl in (1, 5):
            for s16 in range(4):
                place(drums, HAT, t + s16 * BEAT / 4, 0.05 + 0.04 * (s16 % 2))
        if clp and b % 2 == 1:
            place(drums, clap(pl * 10 + b), t, 0.7)
        if b16:
            for s16 in (1, 2, 3):
                place(music, bass(root, BEAT / 4, 0.07 + 0.03 * (pl >= 3)), t + s16 * BEAT / 4, 0.55)
        if arp:
            for s16 in range(4):
                place(music, pluck(ARP[(b * 4 + s16) % 8]), t + s16 * BEAT / 4, 0.13)
    place(music, pad(CH[chord], 2 * BAR, attack=0.6 if pl in (1, 5, 8) else 0.05), t0, 0.32 if pl in (1, 5, 8) else 0.2)
    if pl in (5, 8):
        place(music, pad([root * 2], 2 * BAR), t0, 0.35)  # low drone under the sparse plates

# snare rolls into the drop (P3) and the finale (P8)
for target in (plate(3), plate(8)):
    for k in range(8):
        place(drums, clap(500 + k + int(target)), target - BEAT * 2 + k * BEAT / 4, 0.18 + 0.08 * k)

# sidechain on the music bus
duck = np.ones(N)
dn = int(0.22 * SR)
shape = 1 - 0.6 * np.exp(-np.arange(dn) / SR / 0.06)
for t in kicks:
    i = int(t * SR)
    duck[i : i + dn] = np.minimum(duck[i : i + dn], shape[: max(0, min(dn, N - i))])
music *= duck

# ── SFX on visual events ─────────────────────────────────────────────────
# P1 departure
hit("impact-bass-1", 0.0, 0.35, trim=0.8)  # crop marks snap in
for i in range(8):
    hit("key-press", 0.15 + i * 0.08, 0.12)  # plotter strokes
hit("whoosh-short", bar(0, 3), 0.35)  # the spark leaves home
hit("impact-bass-1", bar(1), 0.45, trim=0.8)  # THE SAFE QUERY
# P2 handshake
hit("impact-bass-1", plate(2), 0.4, trim=0.6)
for i in range(4):
    hit("click-soft", plate(2) + (i + 1) * BEAT * 0.8, 0.35)  # each handshake message
hit("whoosh", bar(3, 0.5), 0.35)  # ECDHE halves meet
hit("ping", bar(3, 2), 0.3, trim=0.9, fade=0.4)  # lock closes
riser = load_sfx("riser")
for target, dur, g in ((plate(3), 0.9, 0.35), (plate(8), 1.6, 0.35)):
    tail = riser[-int(dur * SR) :]
    place(sfx, tail, target - len(tail) / SR, g)
    events.append({"sfx": "riser(tail)", "t": round(target - len(tail) / SR, 3)})
# P3 in transit
hit("impact-bass-2", plate(3), 0.8, trim=1.4, fade=0.6)
hit("glitch-3", plate(3), 0.25, trim=0.3)
hit("typing", plate(3) + 0.1, 0.25, trim=BEAT * 1.6, fade=0.1)
hit("glitch-2", bar(4, 2), 0.25, trim=BEAT * 2.0, fade=0.3)  # bytes scramble into ciphertext
hit("whoosh-short", bar(5), 0.35)  # eavesdropper tap
# P4 injection
hit("impact-bass-1", plate(4), 0.45, trim=0.7)
hit("typing", plate(4) + 0.05, 0.3, trim=BEAT * 1.5, fade=0.1)
hit("error", bar(6, 2), 0.18, trim=0.5, fade=0.2)  # every row comes back
hit("whoosh-short", bar(6, 3), 0.4)  # strike-through
hit("whoosh", bar(7), 0.35)  # parameterized card
hit("impact-bass-2", bar(7, 2.4) + 0.18, 0.85, trim=1.2, fade=0.5)  # stamp lands
# P5 hashed (breakdown)
hit("glitch-1", plate(5), 0.2, trim=0.25)
for i in range(4):
    hit("click-soft", plate(5) + i * BEAT, 0.3)
mono_hit(tick_sweep(BAR * 0.95), plate(5) + 3 * BEAT, 0.14, "rounds-counter(synth)")
hit("impact-bass-1", bar(9, 2), 0.5, trim=0.9)  # hash slab
# P6 least privilege
hit("impact-bass-1", plate(6), 0.45, trim=0.7)
for i in range(3):
    hit("whoosh-short", plate(6) + BEAT * 1.6 + i * BEAT * 0.7, 0.3)
    hit("pop", plate(6) + BEAT * 2.1 + i * BEAT * 0.7, 0.3)
hit("error", bar(11, 2), 0.3, trim=0.9, fade=0.3)  # permission denied
hit("glitch-2", bar(11, 2), 0.2, trim=0.25)
# P7 at rest / audited
hit("glitch-1", plate(7), 0.2, trim=0.25)
hit("sparkle", bar(12, 1), 0.25, trim=1.4, fade=0.5)  # encryption wave
hit("whoosh", bar(13), 0.4)  # key rotation
hit("ping", bar(13) + 0.3, 0.3, trim=0.9, fade=0.4)
for i in range(6):
    hit("key-press", plate(7) + 0.3 + i * BEAT * 0.9, 0.18)  # audit log lines
# P8 handled
hit("impact-bass-2", plate(8), 0.8, trim=1.2, fade=0.5)
hit("whoosh-short", plate(8), 0.35)
hit("impact-bass-1", bar(14, 2), 0.6, trim=0.9)  # DATA,
hit("impact-bass-2", bar(15), 0.95, trim=2.2, fade=1.0)  # HANDLED.
hit("chime", bar(15, 2.5), 0.25, trim=1.4, fade=0.6)

# ── master ───────────────────────────────────────────────────────────────
mono = drums * 0.6 + music * 0.5
mix = np.stack([mono, mono], axis=1) + sfx
fade_n = int(0.6 * SR)
mix[-fade_n:] *= np.linspace(1, 0, fade_n)[:, None] ** 2
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 0.6 / np.max(np.abs(mix))
OUT.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(OUT)],
    input=(mix * 32767).astype("<i2").tobytes(),
    check=True,
)
(ROOT / "assets/audio/events.json").write_text(json.dumps({"bpm": BPM, "bar": BAR, "events": events}, indent=1))
print(f"wrote {OUT.relative_to(ROOT)} · {DURATION}s · {len(events)} sfx hits")

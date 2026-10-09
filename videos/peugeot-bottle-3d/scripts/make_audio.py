"""Electronic 144 BPM soundtrack for the 3D promo, hits aligned to every cut in index.html.

Structure (9 bars × 1.667 s = 15 s): intro with kick + 16th hats from frame one, snare roll into
the drop at bar 2 (bottle drop), full drop with rolling bass + arp + sidechain for bars 2–6,
riser into the end card at bar 7, outro on bar 8.

Usage: python3 scripts/make_audio.py   (needs numpy + ffmpeg)
Output: assets/audio/promo-3d.wav (48 kHz, 16-bit stereo, 15.0 s)
"""

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT.parent.parent / ".agents/skills/media-use/audio/assets/sfx"
OUT = ROOT / "assets/audio/promo-3d.wav"

SR = 48000
BPM = 144
BEAT = 60 / BPM
BAR = 4 * BEAT
DURATION = 15.0
N = int(SR * DURATION)


def bar(b, beat=0.0):
    return b * BAR + beat * BEAT


# Must match CUT / LAND in index.html
CUT = {k: bar(*v) for k, v in {"B": (0, 2), "C": (1, 0), "D": (1, 2), "E": (2, 0), "F": (3, 0), "G": (4, 0), "H": (5, 0), "I": (6, 0), "J": (7, 0)}.items()}
LAND = bar(2, 1)


# ── synthesis ────────────────────────────────────────────────────────────
def env_exp(n, decay):
    return np.exp(-np.arange(n) / SR / decay)


def noise(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def onepole_hp(x, a=0.85):
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = a * (y[i - 1] + x[i] - x[i - 1])
    return y


def onepole_lp(x, a):
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def kick():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    f = 48 + 120 * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.12) + np.exp(-t / 0.0015) * 0.35


HAT = onepole_hp(noise(int(0.035 * SR), 7)) * env_exp(int(0.035 * SR), 0.008)
OPEN_HAT = onepole_hp(noise(int(0.16 * SR), 8)) * env_exp(int(0.16 * SR), 0.05)


def clap(seed):
    n = int(0.2 * SR)
    e = np.zeros(n)
    for k, off in enumerate((0.0, 0.01, 0.02)):
        i = int(off * SR)
        e[i:] += env_exp(n - i, 0.007 if k < 2 else 0.06)
    return onepole_hp(noise(n, seed), 0.7) * e * 0.6


def saw(freq, n, h=10):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, h + 1)) * (2 / np.pi)


def bass16(freq, length):
    n = int(length * SR)
    return onepole_lp(saw(freq, n, 8), 0.09) * np.minimum(1, np.arange(n) / (0.002 * SR)) * env_exp(n, 0.07)


def pluck(freq, length=0.16):
    n = int(length * SR)
    tone = saw(freq, n, 7) * 0.6 + np.sign(np.sin(2 * np.pi * freq * np.arange(n) / SR)) * 0.25
    return onepole_lp(tone, 0.18) * env_exp(n, 0.06)


def pad(freqs, length):
    n = int(length * SR)
    tone = sum(onepole_lp(saw(f, n, 6) + saw(f * 1.005, n, 6), 0.03) for f in freqs) / (2 * len(freqs))
    env = np.minimum(1, np.arange(n) / (0.15 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.5 * SR))
    return tone * env


def splash(seed=11):
    n = int(1.1 * SR)
    t = np.arange(n) / SR
    burst = onepole_hp(noise(n, seed), 0.6) * env_exp(n, 0.08)
    tail = onepole_lp(noise(n, seed + 1), 0.25) * env_exp(n, 0.3) * 0.5
    bubbles = sum(np.sin(2 * np.pi * (500 + 120 * k) * t * (1 + 0.6 * t)) * np.exp(-((t - 0.05 - 0.07 * k) ** 2) / 0.0005) * 0.15 for k in range(8))
    return burst + tail + bubbles


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


# Measured lead-in of bundled files (first loud transient, or peak for whooshes).
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


# ── arrangement ──────────────────────────────────────────────────────────
D2, F2, G2, A2, Bb1, C2 = 73.42, 87.31, 98.0, 110.0, 58.27, 65.41
roots = [D2, D2, D2, Bb1, C2, D2, F2, D2, D2]
chords = {
    D2: [293.66, 349.23, 440.0],
    Bb1: [233.08, 293.66, 349.23],
    C2: [261.63, 329.63, 392.0],
    F2: [261.63, 349.23, 440.0],
}
ARP = [587.33, 698.46, 880.0, 698.46, 1174.66, 880.0, 698.46, 880.0]  # D5 F5 A5 … 16ths
kick_times = []
for b in range(9):
    outro = b == 8
    for beat in range(4):
        t = bar(b, beat)
        if not outro or beat == 0:
            place(drums, kick(), t, 1.0)
            kick_times.append(t)
        for s16 in range(4):
            if outro and beat > 0:
                continue
            tt = t + s16 * BEAT / 4
            place(drums, HAT, tt, (0.16 if s16 % 2 else 0.08) * (0.6 if b < 2 else 1.0))
        if b >= 2 and not outro:
            place(drums, OPEN_HAT, t + BEAT / 2, 0.12)
            if beat in (1, 3):
                place(drums, clap(b * 4 + beat), t, 0.75)
            # rolling 16th bass, skipping the downbeat (kick owns it)
            for s16 in (1, 2, 3):
                place(music, bass16(roots[b], BEAT / 4), t + s16 * BEAT / 4, 0.55)
            if 3 <= b <= 6:
                for s16 in range(4):
                    place(music, pluck(ARP[(beat * 4 + s16) % 8]), t + s16 * BEAT / 4, 0.16)
        elif b < 2:
            place(music, bass16(D2, BEAT / 2), t + BEAT / 2, 0.35)  # intro: offbeat bass only
    if b < 8:
        place(music, pad(chords[roots[b]], BAR), bar(b), 0.22)
    else:
        place(music, pad(chords[D2], BAR), bar(b), 0.4)

# snare rolls into the two drops
for k in range(8):
    place(drums, clap(300 + k), CUT["E"] - BEAT * 2 + k * BEAT / 4, 0.2 + 0.08 * k)
for k in range(8):
    place(drums, clap(400 + k), CUT["J"] - BEAT * 2 + k * BEAT / 4, 0.2 + 0.08 * k)

# sidechain: duck the music bus on every kick
duck = np.ones(N)
dn = int(0.22 * SR)
shape = 1 - 0.65 * np.exp(-np.arange(dn) / SR / 0.06)
for t in kick_times:
    i = int(t * SR)
    duck[i : i + dn] = np.minimum(duck[i : i + dn], shape[: max(0, min(dn, N - i))])
music *= duck

# ── SFX on visual cuts ───────────────────────────────────────────────────
for c in ("B", "C", "D"):
    hit("impact-bass-1", CUT[c], 0.45, trim=0.7)
    hit("glitch-1", CUT[c], 0.22, trim=0.18)
hit("whoosh-cinematic", CUT["E"], 0.5, trim=0.6, fade=0.2)  # bottle falling
riser = load_sfx("riser")
tail = riser[-int(1.3 * SR) :]
place(sfx, tail, CUT["E"] - len(tail) / SR, 0.3)
place(sfx, np.stack([splash(), splash()], axis=1), LAND - 0.02, 0.55)
events.append({"sfx": "splash(synth)", "t": round(LAND - 0.02, 3)})
hit("impact-bass-2", LAND, 0.85, trim=1.4, fade=0.6)
hit("glitch-3", LAND, 0.25, trim=0.3)
hit("whoosh-cinematic", CUT["F"], 0.55, trim=1.6, fade=0.6)  # orbit
for i in range(4):  # snap spins
    hit("whoosh-short", bar(4, i), 0.4)
    hit("impact-bass-1", bar(4, i), 0.25, trim=0.4)
for i in range(3):  # split panels
    hit("whoosh-short", CUT["H"] + i * BEAT, 0.45)
    hit("click-soft", CUT["H"] + i * BEAT + 0.15, 0.3)
hit("glitch-2", CUT["I"], 0.3, trim=0.3)  # tunnel
tail2 = riser[-int(1.6 * SR) :]
place(sfx, tail2, CUT["J"] - len(tail2) / SR, 0.35)
hit("whoosh", CUT["J"] - 0.12, 0.5)  # tricolour wipe
hit("impact-bass-2", CUT["J"], 0.9, trim=2.0, fade=0.8)
for i in range(3):
    hit("click-soft", bar(7, 3) + i * 0.08, 0.3)
hit("chime", bar(8), 0.25, trim=1.6, fade=0.8)

# ── master ───────────────────────────────────────────────────────────────
mono = drums * 0.6 + music * 0.5
mix = np.stack([mono, mono], axis=1) + sfx
fade_n = int(0.45 * SR)
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

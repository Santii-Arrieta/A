"""Música de presentación para el video agro (60 s, instrumental, sin voz).

Re mayor, 120 BPM: 1 compás = 2 s, así cada corte de escena cae en un compás:
  S1 0–6 (c.0–2)  intro: pad + piano suelto
  S2 6–16 (c.3–7) caos: pulso en semicorcheas, bajo, hats; sube tensión, corte seco en 16
  S3 16–22 (c.8–10) pausa: sólo pad filtrado + campana en la pregunta
  S4 22–34 (c.11–16) convergencia: arpegio cálido, entra el bombo en 26, notas en cada widget
  S5 34–46 (c.17–22) dos accesos: groove completo y suave
  S6 46–54 (c.23–26) beneficios: arpegio una octava arriba, notas con cada tarjeta
  S7 54–60 (c.27–29) cierre: acorde final que se apaga; 58–60 cola casi en silencio

Uso: python3 scripts/make_music.py   (numpy + scipy)
Salida: assets/audio/agro-musica.wav (48 kHz, 16 bit, estéreo, 60,0 s)
"""

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/audio/agro-musica.wav"
SR = 48000
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
DUR = 60.0
N = int(SR * DUR)


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def t_of(bar, beat=0.0):
    return bar * BAR + beat * BEAT


def rng(seed):
    return np.random.default_rng(seed)


def filt(x, kind, f):
    sos = butter(2, f, btype=kind, fs=SR, output="sos")
    return sosfilt(sos, x)


class Bus:
    def __init__(self):
        self.l = np.zeros(N)
        self.r = np.zeros(N)

    def add(self, sig, t, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= N:
            return
        sig = sig[: N - i] * gain
        gl = np.cos((pan + 1) * np.pi / 4)
        gr = np.sin((pan + 1) * np.pi / 4)
        self.l[i : i + len(sig)] += sig * gl * 1.414
        self.r[i : i + len(sig)] += sig * gr * 1.414


# ── instrumentos ─────────────────────────────────────────────────────────
def adsr(n, a, d, s, r_len, hold):
    env = np.zeros(n)
    ia, idd, ih = int(a * SR), int(d * SR), int(hold * SR)
    ir = int(r_len * SR)
    t = np.arange(n)
    env[:ia] = t[:ia] / max(ia, 1)
    env[ia : ia + idd] = 1 - (1 - s) * (t[: min(idd, n - ia)] / max(idd, 1))[: len(env[ia : ia + idd])]
    env[ia + idd : ih] = s
    rel = np.arange(min(ir, max(n - ih, 0)))
    env[ih : ih + len(rel)] = s * (1 - rel / max(ir, 1))
    return env


def pad_note(m, dur, seed):
    n = int((dur + 1.6) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.07, 0.0, 0.065):
        f = mf(m) * 2 ** (det / 12)
        ph = rng(seed).uniform(0, 2 * np.pi)
        for k in range(1, 7):
            out += np.sin(2 * np.pi * f * k * t + ph * k) / (k**1.3)
    return out * adsr(n, 0.9, 0.5, 0.8, 1.6, dur) / 6


def piano(m, vel=1.0, decay=1.6, bright=1.0):
    n = int((decay * 2.2) * SR)
    t = np.arange(n) / SR
    f = mf(m)
    out = np.zeros(n)
    for k in range(1, 8):
        fk = f * k * (1 + 0.0004 * k * k)
        out += np.sin(2 * np.pi * fk * t) * (bright / k**1.6) * np.exp(-t * (1 / decay) * (1 + 0.45 * k))
    atk = np.minimum(1, t / 0.004)
    return out * atk * vel * 0.5


def pluck(m, vel=1.0):
    return piano(m, vel, decay=0.22, bright=1.4)


def bass(m, dur, vel=1.0):
    n = int((dur + 0.15) * SR)
    t = np.arange(n) / SR
    f = mf(m)
    sig = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    sig = np.tanh(1.4 * sig)
    return sig * adsr(n, 0.01, 0.12, 0.75, 0.12, dur) * vel * 0.55


def kick(vel=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 85 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 7) * vel


def hat(vel=1.0, seed=0, length=0.05):
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = filt(rng(seed).uniform(-1, 1, n), "highpass", 7000)
    return x * np.exp(-t / length) * vel * 0.35


def clap(vel=1.0, seed=0):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    x = filt(rng(seed).uniform(-1, 1, n), "bandpass", [900, 3200])
    env = np.exp(-t / 0.09) + 0.6 * np.exp(-np.maximum(t - 0.012, 0) / 0.01) * (t > 0.012)
    return x * env * vel * 0.35


def swell(dur, seed, lo=400, hi=6000):
    """ruido filtrado que crece (subida de tensión)"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng(seed).uniform(-1, 1, n)
    x = filt(x, "bandpass", [lo, hi])
    return x * (t / dur) ** 2.2 * 0.22


# ── armonía ──────────────────────────────────────────────────────────────
CH = {
    "D": [50, 57, 62, 66, 69],
    "Dadd9": [50, 57, 62, 64, 66],
    "Bm": [47, 54, 59, 62, 66],
    "G": [43, 55, 59, 62, 67],
    "Gmaj7": [43, 55, 59, 62, 66],
    "A": [45, 57, 61, 64, 69],
    "Asus4": [45, 57, 62, 64, 69],
    "Em7": [40, 55, 59, 62, 66],
    "F#m": [42, 54, 57, 61, 66],
}
# un acorde por compás (30 compases = 60 s)
PROG = (
    ["Dadd9", "Gmaj7", "Asus4"]  # S1
    + ["Bm", "G", "Em7", "F#m", "F#m"]  # S2 caos
    + ["Gmaj7", "Em7", "Asus4"]  # S3 pausa
    + ["D", "Bm", "G", "A", "D", "A"]  # S4
    + ["D", "A", "Bm", "G", "D", "A"]  # S5
    + ["G", "A", "Bm", "A"]  # S6
    + ["D", "D", "D"]  # S7
)
assert len(PROG) == 30

pad, keys, low, drums, fx = Bus(), Bus(), Bus(), Bus(), Bus()

# pad: todo el tema salvo el corte seco de la congelación
for b, name in enumerate(PROG):
    if b in (27, 28, 29):
        continue
    dur = BAR - (0.25 if b == 7 else 0)  # el compás 7 se corta en 16 s
    for j, m in enumerate(CH[name][1:]):
        pad.add(pad_note(m, dur, b * 10 + j), t_of(b), 0.16, pan=(-0.5 + j * 0.33))
# acorde final largo (54 s) que se apaga solo
for j, m in enumerate([50, 57, 62, 66, 69, 74]):
    pad.add(pad_note(m, 3.4, 900 + j), t_of(27), 0.17, pan=(-0.6 + j * 0.24))

# S1: piano suelto
for t, m in [(0.6, 74), (1.6, 69), (2.4, 76), (4.0, 73), (4.8, 71), (5.4, 69)]:
    keys.add(piano(m, 0.55, 1.8), t, pan=0.15)

# S2: pulso nervioso en semicorcheas, bajo en corcheas, hats, bombo
for b in range(3, 8):
    chord = CH[PROG[b]]
    pattern = [chord[2], chord[3], chord[4], chord[3]]
    for s in range(16):
        t = t_of(b, s * 0.25)
        if t >= 15.98:
            break
        vel = 0.35 + 0.25 * ((b - 3) / 4) + (0.15 if s % 4 == 0 else 0)
        keys.add(pluck(pattern[s % 4] + 12, vel), t, pan=(-0.35 if s % 2 else 0.35))
    for e in range(8):
        t = t_of(b, e * 0.5)
        if t < 15.9:
            low.add(bass(chord[0], 0.22, 0.8), t)
    for e in range(8 if b < 5 else 16):
        step = 0.5 if b < 5 else 0.25
        t = t_of(b, e * step)
        if t < 15.95:
            drums.add(hat(0.6 if e % 2 else 0.9, seed=b * 50 + e), t, pan=0.3)
    for q in (0, 2):
        drums.add(kick(0.55), t_of(b, q))
# temblor 15–15.8: redoble de toms bajos
for k in range(8):
    drums.add(kick(0.25 + 0.06 * k), 15.0 + k * 0.1)
fx.add(swell(3.8, 7), 12.2, 0.9)

# S3: campana en la pregunta y en "un solo lugar"
for t, m in [(16.4, 81), (17.5, 78), (18.6, 76), (20.4, 74)]:
    keys.add(piano(m, 0.38, 2.6, bright=0.6), t, pan=-0.1)
fx.add(swell(2.0, 11, 300, 3000), 20.0, 0.6)

# S4–S6: arpegio en corcheas
def arp(b0, b1, octave=0, vel=0.32):
    for b in range(b0, b1):
        c = CH[PROG[b]]
        seq = [c[1], c[2], c[3], c[4], c[3], c[2], c[3], c[4]]
        for e in range(8):
            keys.add(piano(seq[e] + 12 + octave, vel * (1.1 if e == 0 else 1), 0.7), t_of(b, e * 0.5), pan=(-0.25 + 0.07 * e))


arp(11, 17, 0, 0.26)
arp(17, 23, 0, 0.32)
arp(23, 27, 12, 0.24)
arp(23, 27, 0, 0.22)

# notas en cada widget que aterriza (23.8 / 25.2 / 26.6 / 28.0)
for t, m in [(23.8, 78), (25.2, 81), (26.6, 83), (28.0, 86)]:
    keys.add(piano(m, 0.4, 1.4, bright=0.8), t, pan=0.2)
# notas con cada tarjeta de beneficios (46.3 + 0.12 k)
for k, m in enumerate([74, 78, 81, 86]):
    keys.add(piano(m, 0.38, 1.2), 46.3 + 0.12 * k, pan=-0.3 + 0.2 * k)

# bajo y batería suaves
for b in range(11, 27):
    c = CH[PROG[b]]
    for q in range(4):
        if b >= 13 or q == 0:
            low.add(bass(c[0], BEAT * 0.9, 0.75 if b < 17 else 0.85), t_of(b, q))
    if b >= 13:
        for q in range(4):
            drums.add(kick(0.5 if b < 17 else 0.6), t_of(b, q))
        for e in range(8):
            drums.add(hat(0.45 if e % 2 else 0.25, seed=b * 70 + e, length=0.035), t_of(b, e * 0.5 + 0.0), pan=0.25)
    if b >= 17:
        for q in (1, 3):
            drums.add(clap(0.55 if b < 23 else 0.7, seed=b * 9 + q), t_of(b, q), pan=-0.1)
fx.add(swell(2.0, 23, 500, 7000), 52.0, 0.7)

# S7: cierre — bajo y piano finales
low.add(bass(38, 3.0, 0.8), t_of(27))
for t, m in [(54.0, 74), (54.3, 78), (54.6, 81), (55.6, 86), (56.2, 81)]:
    keys.add(piano(m, 0.42, 2.2), t, pan=0.1)
drums.add(kick(0.6), t_of(27))

# ── mezcla ───────────────────────────────────────────────────────────────
def stereo(bus):
    return np.stack([bus.l, bus.r])


pad_s = stereo(pad)
pad_s = np.stack([filt(ch, "lowpass", 2600) for ch in pad_s])
# en la pausa (16–22) el pad se oscurece
pause = np.stack([filt(ch, "lowpass", 700) for ch in pad_s])
w = np.zeros(N)
i0, i1 = int(16.0 * SR), int(22.0 * SR)
w[i0:i1] = 1
w = np.convolve(w, np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same")
pad_s = pad_s * (1 - w) + pause * w

keys_s = stereo(keys)
low_s = np.stack([filt(ch, "lowpass", 900) for ch in stereo(low)])
drums_s = stereo(drums)
fx_s = stereo(fx)

# reverb: respuesta impulsiva de ruido con caída exponencial
ir_len = int(2.6 * SR)
tir = np.arange(ir_len) / SR
irs = [filt(rng(s).standard_normal(ir_len), "lowpass", 5000) * np.exp(-tir / 0.75) for s in (101, 202)]
irs = [ir / np.sqrt(np.sum(ir**2)) for ir in irs]
send = 0.55 * pad_s + 0.7 * keys_s + 0.15 * drums_s + 0.4 * fx_s
rev = np.stack([fftconvolve(send[c], irs[c])[:N] for c in range(2)]) * 0.35

mix = 0.9 * pad_s + 0.9 * keys_s + 0.65 * low_s + 0.5 * drums_s + 0.6 * fx_s + rev
mix = np.stack([filt(ch, "highpass", 38) for ch in mix])  # sin sub-graves que ensucien parlantes chicos

# volumen por escena: el caos apenas más fuerte, la pausa más baja, cola final
g = np.ones(N)
tt = np.arange(N) / SR
g *= np.where((tt >= 16) & (tt < 22), 0.8, 1.0)
g *= np.clip((tt - 0.0) / 1.2, 0, 1)  # entrada
g *= np.where(tt > 57.0, np.clip((60.0 - tt) / 3.0, 0, 1) ** 1.5, 1.0)  # se apaga al final
g = np.convolve(g, np.ones(2400) / 2400, mode="same")
mix *= g

mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= 10 ** (-5.0 / 20) / np.max(np.abs(mix))  # pico -5 dBFS: música de fondo, 4 dB más baja que la v1
mix[:, -int(0.05 * SR) :] *= np.linspace(1, 0, int(0.05 * SR))

OUT.parent.mkdir(parents=True, exist_ok=True)
pcm = (mix.T * 32767).astype("<i2")
with wave.open(str(OUT), "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())
rms = 20 * np.log10(np.sqrt(np.mean(mix**2)))
print(f"{OUT} {N / SR:.2f}s  pico -5.0 dBFS  RMS {rms:.1f} dBFS")

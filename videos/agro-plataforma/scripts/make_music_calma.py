"""Música tranquila para el video agro (versión "calma", 60 s, instrumental).

Pensada para acompañar sin cansar: sin batería, piano suave tipo "felt", colchón cálido,
transiciones lentas y volumen parejo (nivelador lento + techo de agudos).
Misma grilla que el video: Re mayor, 120 BPM → 1 compás = 2 s, cada escena empieza en compás.
  S1 0–6    pad + notas sueltas
  S2 6–16   arpegio en corcheas, apenas más movimiento (no más volumen)
  S3 16–22  el piano se retira, queda el colchón y tres notas
  S4 22–34  arpegio en negras, bajo largo, una nota por widget
  S5 34–46  igual con una segunda voz
  S6 46–54  una nota aguda por tarjeta
  S7 54–60  acorde final que se apaga

Uso: python3 scripts/make_music_calma.py   (numpy + scipy)
Salida: assets/audio/agro-musica-calma.wav (48 kHz, 16 bit, estéreo, 60,0 s)
"""

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/audio/agro-musica-calma.wav"
SR = 48000
BEAT = 0.5
BAR = 2.0
N = int(SR * 60.0)
TARGET_LUFS_APPROX = -24.7  # calibrado: da ≈ -20 LUFS integrados (medido con ffmpeg ebur128)


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tb(bar, beat=0.0):
    return bar * BAR + beat * BEAT


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x)


class Bus:
    def __init__(self):
        self.l = np.zeros(N)
        self.r = np.zeros(N)

    def add(self, sig, t, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= N:
            return
        sig = sig[: N - i] * gain
        self.l[i : i + len(sig)] += sig * np.cos((pan + 1) * np.pi / 4) * 1.414
        self.r[i : i + len(sig)] += sig * np.sin((pan + 1) * np.pi / 4) * 1.414

    def st(self):
        return np.stack([self.l, self.r])


def env(n, a, hold, r):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a)
    rel = np.clip(1 - (t - hold) / r, 0, 1)
    return e * np.where(t > hold, rel, 1) ** 2


def pad_note(m, dur, seed):
    """colchón cálido: senos levemente desafinados, pocos armónicos, ataque y caída lentos"""
    n = int((dur + 2.5) * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    ph = np.random.default_rng(seed).uniform(0, 2 * np.pi, 8)
    for j, det in enumerate((-0.05, 0.0, 0.05)):
        f = mf(m) * 2 ** (det / 12)
        for k in (1, 2, 3):
            out += np.sin(2 * np.pi * f * k * t + ph[j + k]) / k**2.2
    # vibrato de amplitud muy lento para que respire
    out *= 1 + 0.06 * np.sin(2 * np.pi * 0.23 * t + ph[0])
    return out * env(n, 1.6, dur, 2.4) / 4.5


def felt(m, vel=1.0, decay=2.4):
    """piano suave: pocos armónicos, ataque redondeado, sin brillo metálico"""
    n = int(decay * 2.6 * SR)
    t = np.arange(n) / SR
    f = mf(m)
    out = np.zeros(n)
    for k in range(1, 6):
        out += np.sin(2 * np.pi * f * k * (1 + 0.0003 * k * k) * t) / k**2.3 * np.exp(-t * (1 + 0.6 * k) / decay)
    return out * np.minimum(1, t / 0.014) * vel * 0.45


def bass(m, dur, vel=1.0):
    n = int((dur + 1.0) * SR)
    t = np.arange(n) / SR
    f = mf(m)
    sig = np.sin(2 * np.pi * f * t) + 0.12 * np.sin(4 * np.pi * f * t)
    return sig * env(n, 0.25, dur, 0.9) * vel * 0.32


CH = {
    "Dadd9": [50, 57, 62, 64, 66],
    "D": [50, 57, 62, 66, 69],
    "Bm": [47, 54, 59, 62, 66],
    "G": [43, 55, 59, 62, 67],
    "Gmaj7": [43, 55, 59, 62, 66],
    "A": [45, 57, 61, 64, 69],
    "Asus4": [45, 57, 62, 64, 69],
    "Em7": [40, 55, 59, 62, 66],
}
PROG = (
    ["Dadd9", "Gmaj7", "Asus4"]
    + ["Bm", "Gmaj7", "Em7", "Asus4", "Asus4"]
    + ["Gmaj7", "Em7", "Asus4"]
    + ["D", "Bm", "G", "A", "D", "A"]
    + ["D", "A", "Bm", "G", "D", "A"]
    + ["G", "A", "Bm", "A"]
    + ["Dadd9", "Dadd9", "Dadd9"]
)
assert len(PROG) == 30

pad, keys, low = Bus(), Bus(), Bus()

# colchón continuo (los acordes se encadenan, nunca hay cortes)
for b, name in enumerate(PROG[:27]):
    for j, m in enumerate(CH[name][1:]):
        pad.add(pad_note(m, BAR + 0.4, b * 7 + j), tb(b), 0.15, pan=-0.45 + j * 0.3)
for j, m in enumerate([50, 57, 62, 64, 66, 69]):
    pad.add(pad_note(m, 3.2, 500 + j), tb(27), 0.15, pan=-0.5 + j * 0.2)

# bajo: una nota larga por compás (en la pausa también, más suave)
for b, name in enumerate(PROG[:27]):
    low.add(bass(CH[name][0], BAR - 0.1, 0.55 if 8 <= b <= 10 else 0.8), tb(b))
low.add(bass(38, 3.0, 0.75), tb(27))

# S1: notas sueltas
for t, m in [(0.8, 74), (2.0, 69), (3.2, 76), (4.4, 73), (5.4, 71)]:
    keys.add(felt(m, 0.5, 2.8), t, pan=0.15)

# S2: arpegio en corcheas, suave y parejo (más movimiento, no más fuerte)
for b in range(3, 8):
    c = CH[PROG[b]]
    seq = [c[1], c[2], c[3], c[4], c[3], c[2], c[3], c[4]]
    for e in range(8):
        t = tb(b, e * 0.5)
        if t > 15.6:
            break
        keys.add(felt(seq[e] + 12, 0.24 + (0.05 if e == 0 else 0), 1.2), t, pan=-0.3 + 0.08 * e)

# S3: tres notas
for t, m in [(16.6, 78), (18.2, 76), (20.0, 74)]:
    keys.add(felt(m, 0.4, 3.2), t, pan=-0.1)

# S4–S6: arpegio en negras
for b in range(11, 27):
    c = CH[PROG[b]]
    seq = [c[1], c[2], c[3], c[2]]
    for q in range(4):
        keys.add(felt(seq[q] + 12, 0.26 if q == 0 else 0.21, 1.8), tb(b, q), pan=-0.2 + 0.13 * q)
    if 17 <= b < 27:  # S5–S6: segunda voz, una nota larga por compás
        keys.add(felt(c[4] + 12, 0.18, 3.0), tb(b, 0.5), pan=0.35)

# una nota por widget y por tarjeta, muy suaves
for t, m in [(23.8, 78), (25.2, 81), (26.6, 83), (28.0, 86)]:
    keys.add(felt(m, 0.22, 2.0), t, pan=0.25)
for k, m in enumerate([74, 78, 81, 86]):
    keys.add(felt(m, 0.2, 2.0), 46.3 + 0.12 * k, pan=-0.3 + 0.2 * k)

# S7: cierre
for t, m in [(54.0, 74), (54.5, 78), (55.0, 81), (56.0, 86)]:
    keys.add(felt(m, 0.32, 3.2), t, pan=0.1)

# ── mezcla ───────────────────────────────────────────────────────────────
pad_s = np.stack([filt(ch, "lowpass", 2200) for ch in pad.st()])
keys_s = np.stack([filt(ch, "lowpass", 3800) for ch in keys.st()])
low_s = np.stack([filt(ch, "lowpass", 400) for ch in low.st()])

ir_len = int(3.2 * SR)
tir = np.arange(ir_len) / SR
irs = []
for s in (11, 22):
    ir = filt(np.random.default_rng(s).standard_normal(ir_len), "lowpass", 4000) * np.exp(-tir / 1.0)
    irs.append(ir / np.sqrt(np.sum(ir**2)))
send = 0.6 * pad_s + 0.9 * keys_s
rev = np.stack([fftconvolve(send[c], irs[c])[:N] for c in range(2)]) * 0.45

mix = 0.85 * pad_s + 0.8 * keys_s + 0.7 * low_s + rev
mix = np.stack([filt(ch, "highpass", 45) for ch in mix])
mix = np.stack([filt(ch, "lowpass", 6000) for ch in mix])  # techo de agudos: nada filoso

# nivelador lento: lleva el volumen a un nivel parejo, con cambios de ganancia suaves (≈2 s)
mono = np.mean(mix, axis=0)
win = int(1.5 * SR)
rms = np.sqrt(np.convolve(mono**2, np.ones(win) / win, mode="same") + 1e-9)
target = np.median(rms[int(2 * SR) : int(56 * SR)])
gain = np.clip(target / rms, 0.6, 1.6)
k = int(2.0 * SR)
gain = np.convolve(gain, np.ones(k) / k, mode="same")
tt = np.arange(N) / SR
fade = np.clip(tt / 2.0, 0, 1) * np.where(tt > 56.5, np.clip((60 - tt) / 3.5, 0, 1) ** 1.6, 1)
# en la entrada y en la cola manda el fundido, no el nivelador
gain = np.where((tt < 2.0) | (tt > 56.0), np.minimum(gain, 1.0), gain)
mix = mix * gain * fade

# nivel final: integrado ≈ -21 LUFS (aprox. por RMS), pico ≤ -6 dBFS
rms_all = np.sqrt(np.mean(mix[:, int(2 * SR) : int(56 * SR)] ** 2))
mix *= 10 ** ((TARGET_LUFS_APPROX + 3.0) / 20) / rms_all
peak = np.max(np.abs(mix))
if peak > 10 ** (-6 / 20):
    mix *= 10 ** (-6 / 20) / peak
mix[:, -int(0.05 * SR) :] *= np.linspace(1, 0, int(0.05 * SR))

OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes((mix.T * 32767).astype("<i2").tobytes())
print(f"{OUT} 60.00s  pico {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS")

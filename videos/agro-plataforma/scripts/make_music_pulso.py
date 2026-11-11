"""Música "pulso" para el video agro (60 s, instrumental): punto medio entre la primera
(movida, cansaba) y las tranquilas (se dormían).

Tiene pulso y sensación de avance, pero sin lo que irritaba:
  - sin platillos/hi-hats ni ruido agudo; el ritmo lo lleva un ostinato tipo marimba en corcheas
  - bombo blando (sin click) y una palma suave y oscura sólo en la parte más alta
  - el volumen sigue un arco por escena (sube de a poco), con cambios lentos, sin saltos
Sol mayor, 120 BPM (1 compás = 2 s; cada escena empieza en compás, igual que el video).

  S1 0–6    piano + colchón oscuro, se presenta un fragmento de la melodía
  S2 6–16   entra el ostinato y el bombo a medio tiempo: se nota el movimiento del caos
  S3 16–22  se vacía: colchón + piano (baja ≈3 dB, no se corta)
  S4 22–34  vuelve el pulso, entra el bajo en corcheas, el colchón se abre
  S5 34–46  bombo en negras, palma suave, melodía completa
  S6 46–54  la melodía sube una octava: punto más alto
  S7 54–60  acorde final en Sol que se apaga

Uso: python3 scripts/make_music_pulso.py   (numpy + scipy)
Salida: assets/audio/agro-musica-pulso.wav (48 kHz, 16 bit, estéreo, 60,0 s)
"""

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/audio/agro-musica-pulso.wav"
SR = 48000
BEAT = 0.5
BAR = 2.0
N = int(SR * 60.0)
LEVEL = -22.7  # calibrado para ≈ -21 LUFS integrados (se mide con ffmpeg ebur128)


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tb(bar, beat=0.0):
    return bar * BAR + beat * BEAT


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, btype=kind, fs=SR, output="sos"), x)


def rng(s):
    return np.random.default_rng(s)


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
    return e * np.where(t > hold, np.clip(1 - (t - hold) / r, 0, 1), 1) ** 2


# ── instrumentos ─────────────────────────────────────────────────────────
def piano(m, vel=1.0, decay=2.0):
    n = int(decay * 2.5 * SR)
    t = np.arange(n) / SR
    f = mf(m)
    out = np.zeros(n)
    for k in range(1, 7):
        out += np.sin(2 * np.pi * f * k * (1 + 0.0003 * k * k) * t) / k**1.9 * np.exp(-t * (1 + 0.5 * k) / decay)
    return out * np.minimum(1, t / 0.006) * vel * 0.45


def marimba(m, vel=1.0):
    """ostinato: madera suave (fundamental + parcial 4x que se apaga enseguida)"""
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = mf(m)
    out = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.22) + 0.25 * np.sin(2 * np.pi * 3.99 * f * t) * np.exp(-t / 0.035)
    return out * np.minimum(1, t / 0.003) * vel * 0.4


def pad_note(m, dur, seed):
    n = int((dur + 2.2) * SR)
    t = np.arange(n) / SR
    ph = rng(seed).uniform(0, 2 * np.pi, 8)
    out = np.zeros(n)
    for j, det in enumerate((-0.07, 0.0, 0.07)):
        f = mf(m) * 2 ** (det / 12)
        for k in (1, 2, 3, 4):
            out += np.sin(2 * np.pi * f * k * t + ph[j + k]) / k**1.6
    return out * env(n, 1.0, dur, 2.0) / 5.0


def bass(m, dur, vel=1.0):
    n = int((dur + 0.2) * SR)
    t = np.arange(n) / SR
    f = mf(m)
    sig = np.tanh(1.2 * (np.sin(2 * np.pi * f * t) + 0.2 * np.sin(4 * np.pi * f * t)))
    return sig * env(n, 0.012, dur, 0.15) * vel * 0.42


def kick(vel=1.0):
    """bombo blando: barrido 95→48 Hz sin click de ataque"""
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    f = 48 + 47 * np.exp(-t * 25)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * np.minimum(1, t / 0.003)
    return filt(s, "lowpass", 180) * vel


def clap(vel=1.0, seed=0):
    """palma suave y oscura (sin agudos)"""
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    x = filt(rng(seed).uniform(-1, 1, n), "bandpass", [700, 2200])
    return x * np.exp(-t / 0.07) * vel * 0.3


# ── armonía y melodía ────────────────────────────────────────────────────
CH = {
    "G": (43, [55, 59, 62, 67]),
    "Em": (40, [55, 59, 64, 67]),
    "Cmaj7": (48, [55, 59, 60, 64]),
    "C": (48, [55, 60, 64, 67]),
    "D": (50, [54, 57, 62, 66]),
    "Dsus": (50, [55, 57, 62, 67]),
    "Am7": (45, [55, 60, 64, 67]),
}
PROG = (
    ["G", "Em", "Cmaj7"]  # S1
    + ["Em", "C", "G", "D", "Dsus"]  # S2
    + ["Cmaj7", "Am7", "Dsus"]  # S3
    + ["G", "D", "Em", "C", "G", "Dsus"]  # S4
    + ["G", "D", "Em", "C", "G", "D"]  # S5
    + ["C", "D", "Em", "Dsus"]  # S6
    + ["G", "G", "G"]  # S7
)
assert len(PROG) == 30

# motivo de 4 compases sobre G–D–Em–C: (compás relativo, tiempo, nota)
MOTIF = [
    (0, 1.0, 71), (0, 1.5, 74), (0, 2.0, 76), (0, 3.0, 74),
    (1, 1.0, 74), (1, 1.5, 76), (1, 2.0, 78), (1, 3.0, 76),
    (2, 1.0, 79), (2, 2.0, 78), (2, 3.0, 76),
    (3, 1.0, 74), (3, 2.0, 72), (3, 3.0, 71),
]

pad, keys, osti, low, drums = Bus(), Bus(), Bus(), Bus(), Bus()

# colchón continuo
for b, name in enumerate(PROG[:27]):
    for j, m in enumerate(CH[name][1]):
        pad.add(pad_note(m, BAR + 0.3, b * 9 + j), tb(b), 0.13, pan=-0.45 + j * 0.3)
for j, m in enumerate([55, 59, 62, 67, 71]):
    pad.add(pad_note(m, 3.4, 700 + j), tb(27), 0.13, pan=-0.45 + j * 0.22)

# ostinato en corcheas (S2, S4–S6)
ACC = [1.0, 0.55, 0.8, 0.55, 0.9, 0.55, 0.8, 0.6]
for b in list(range(3, 8)) + list(range(11, 27)):
    v = CH[PROG[b]][1]
    pat = [v[0], v[2], v[3], v[2], v[1], v[2], v[3], v[2]]
    base = 0.2 if b < 8 else (0.22 if b < 17 else 0.26)
    for e in range(8):
        t = tb(b, e * 0.5)
        if 15.75 < t < 22.0:
            continue
        osti.add(marimba(pat[e] + 12, base * ACC[e]), t, pan=(-0.35 if e % 2 else 0.35))

# bajo: notas largas en S1–S3, corcheas desde S4 (compás 13)
for b, name in enumerate(PROG[:27]):
    bs = CH[name][0]
    if b >= 13:
        for e in range(8):
            low.add(bass(bs, 0.2, 0.75 if e % 2 else 0.9), tb(b, e * 0.5))
    else:
        low.add(bass(bs, BAR - 0.15, 0.6), tb(b))
low.add(bass(43, 3.0, 0.7), tb(27))

# bombo: medio tiempo en S2 y S4, negras en S5–S6; palma suave en 2 y 4 sólo en S5–S6
for b in list(range(4, 8)) + list(range(11, 27)):
    four = 17 <= b < 27
    for q in range(4) if four else (0, 2):
        t = tb(b, q)
        if 15.75 < t < 22.0:
            continue
        drums.add(kick(0.55 if not four else 0.5), t)
    if four:
        for q in (1, 3):
            drums.add(clap(0.5 if b < 23 else 0.6, seed=b * 4 + q), tb(b, q), pan=-0.1)
drums.add(kick(0.45), tb(27))

# piano: fragmento en S1, notas en S3, motivo completo en S5 y una octava arriba en S6
for b, q, m in MOTIF[:7]:
    keys.add(piano(m - 12, 0.32, 2.2), tb(b, q), pan=0.1)
for t, m in [(16.4, 74), (17.6, 71), (19.0, 72), (20.6, 74)]:
    keys.add(piano(m, 0.3, 2.8), t, pan=0.0)
for start, shift, vel in [(13, -12, 0.26), (17, 0, 0.34), (21, 0, 0.32), (23, 12, 0.3)]:
    for b, q, m in MOTIF:
        if start + b > 26:
            continue
        keys.add(piano(m + shift, vel, 1.8), tb(start + b, q), pan=0.12)
# una nota por widget y por tarjeta
for t, m in [(23.8, 79), (25.2, 81), (26.6, 83), (28.0, 86)]:
    keys.add(piano(m, 0.16, 1.4), t, pan=0.3)
# cierre
for t, m in [(54.0, 67), (54.0, 71), (54.0, 74), (54.6, 79), (55.4, 83)]:
    keys.add(piano(m, 0.3, 3.2), t, pan=0.05)

# ── mezcla ───────────────────────────────────────────────────────────────
tt = np.arange(N) / SR


def curve(points):
    xs, ys = zip(*points)
    return np.interp(tt, xs, ys)


# el colchón se abre de a poco (oscuro al inicio y en la pausa, abierto en S5–S6)
bright = curve([(0, 0), (6, 0.2), (15, 0.6), (16.5, 0.1), (21, 0.3), (34, 0.8), (46, 1.0), (54, 1.0), (60, 0.6)])
pad_raw = pad.st()
pad_dark = np.stack([filt(ch, "lowpass", 900) for ch in pad_raw])
pad_open = np.stack([filt(ch, "lowpass", 3200) for ch in pad_raw])
pad_s = pad_dark * (1 - bright) + pad_open * bright
# "bombeo" leve del colchón con el pulso (sensación de avance) donde hay bombo en negras
pump = np.ones(N)
for b in range(17, 27):
    for q in range(4):
        i = int(tb(b, q) * SR)
        L = int(0.4 * SR)
        pump[i : i + L] = np.minimum(pump[i : i + L], 1 - 0.25 * np.exp(-np.arange(L) / SR / 0.12))
pad_s = pad_s * pump

keys_s = np.stack([filt(ch, "lowpass", 5000) for ch in keys.st()])
osti_s = np.stack([filt(ch, "lowpass", 4000) for ch in osti.st()])
low_s = np.stack([filt(ch, "lowpass", 500) for ch in low.st()])
drums_s = drums.st()

ir_len = int(2.6 * SR)
tir = np.arange(ir_len) / SR
irs = []
for s in (51, 62):
    ir = filt(rng(s).standard_normal(ir_len), "lowpass", 4500) * np.exp(-tir / 0.8)
    irs.append(ir / np.sqrt(np.sum(ir**2)))
send = 0.5 * pad_s + 0.7 * keys_s + 0.35 * osti_s + 0.1 * drums_s
rev = np.stack([fftconvolve(send[c], irs[c])[:N] for c in range(2)]) * 0.35

mix = 0.8 * pad_s + 0.9 * keys_s + 0.75 * osti_s + 0.75 * low_s + 0.7 * drums_s + rev
mix = np.stack([filt(filt(ch, "highpass", 40), "lowpass", 9000) for ch in mix])

# arco de volumen por escena (dB) + nivelador lento que lo sigue sin saltos
arc_db = curve([(0, -3.5), (6, -2.0), (15.5, -1.0), (17, -4.0), (21.5, -3.5), (24, -1.8), (34, -0.8), (46, 0.0), (54, 0.2), (56, -0.8), (60, -0.8)])
mono = np.mean(mix, axis=0)
win = int(1.5 * SR)
rms = np.sqrt(np.convolve(mono**2, np.ones(win) / win, mode="same") + 1e-9)
ref = np.median(rms[int(34 * SR) : int(54 * SR)])
gain = np.clip(ref * 10 ** (arc_db / 20) / rms, 0.5, 1.8)
k = int(2.5 * SR)
gain = np.convolve(gain, np.ones(k) / k, mode="same")
gain = np.where((tt < 2.0) | (tt > 56.0), np.minimum(gain, gain[int(56 * SR)]), gain)
fade = np.clip(tt / 1.5, 0, 1) * np.where(tt > 56.5, np.clip((60 - tt) / 3.5, 0, 1) ** 1.6, 1)
mix = mix * gain * fade

rms_all = np.sqrt(np.mean(mix[:, int(2 * SR) : int(56 * SR)] ** 2))
mix *= 10 ** (LEVEL / 20) / rms_all
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

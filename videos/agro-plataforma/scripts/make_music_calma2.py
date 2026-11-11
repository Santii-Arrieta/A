"""Música tranquila v2 para el video agro (60 s, instrumental): otra melodía, más baja.

Fa mayor, 120 BPM (1 compás = 2 s; cada escena empieza en compás, igual que el video).
Piano eléctrico suave (tipo Rhodes) + una melodía en un timbre de flauta suave + colchón y bajo.
Sin batería, sin agudos filosos, volumen parejo (nivelador lento). Nivel ≈ -23 LUFS.

  S1 0–6    se presenta el motivo de la melodía
  S2 6–16   el piano eléctrico se mueve en corcheas; la melodía responde corta
  S3 16–22  sólo colchón y una nota larga
  S4 22–34  vuelve el motivo completo
  S5 34–46  variación del motivo, más aguda y abierta
  S6 46–54  frase que sube
  S7 54–60  resuelve en Fa y se apaga

Uso: python3 scripts/make_music_calma2.py   (numpy + scipy)
Salida: assets/audio/agro-musica-calma2.wav (48 kHz, 16 bit, estéreo, 60,0 s)
"""

import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets/audio/agro-musica-calma2.wav"
SR = 48000
BEAT = 0.5
BAR = 2.0
N = int(SR * 60.0)
LEVEL = -25.1  # calibrado para ≈ -23 LUFS integrados (se mide con ffmpeg ebur128)


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
    return e * np.where(t > hold, np.clip(1 - (t - hold) / r, 0, 1), 1) ** 2


def epiano(m, vel=1.0, decay=2.0):
    """piano eléctrico suave: fundamental + armónicos que se apagan rápido + trémolo lento"""
    n = int(decay * 2.4 * SR)
    t = np.arange(n) / SR
    f = mf(m)
    out = np.sin(2 * np.pi * f * t) * np.exp(-t / decay)
    out += 0.28 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / (decay * 0.35))
    out += 0.06 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t / (decay * 0.15))
    out *= 1 + 0.08 * np.sin(2 * np.pi * 4.2 * t)
    return out * np.minimum(1, t / 0.008) * vel * 0.5


def flute(m, dur, vel=1.0):
    """melodía: timbre de flauta suave (senos + un soplo filtrado mínimo), vibrato que entra tarde"""
    n = int((dur + 0.6) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.25) / 0.4, 0, 1)
    ph = 2 * np.pi * np.cumsum(mf(m) * vib) / SR
    out = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    breath = filt(np.random.default_rng(m).standard_normal(n), "bandpass", [mf(m) * 0.9, mf(m) * 2.2]) * 0.03
    return (out + breath) * env(n, 0.09, dur, 0.5) * vel * 0.35


def pad_note(m, dur, seed):
    n = int((dur + 2.5) * SR)
    t = np.arange(n) / SR
    ph = np.random.default_rng(seed).uniform(0, 2 * np.pi, 6)
    out = np.zeros(n)
    for j, det in enumerate((-0.06, 0.06)):
        f = mf(m) * 2 ** (det / 12)
        out += np.sin(2 * np.pi * f * t + ph[j]) + 0.2 * np.sin(4 * np.pi * f * t + ph[j + 2])
    return out * env(n, 1.8, dur, 2.4) / 3.5


def bass(m, dur, vel=1.0):
    n = int((dur + 1.0) * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * mf(m) * t) + 0.1 * np.sin(4 * np.pi * mf(m) * t)
    return sig * env(n, 0.2, dur, 0.9) * vel * 0.3


# (bajo, voces)
CH = {
    "Fmaj9": (41, [57, 60, 64, 67]),
    "F": (41, [53, 57, 60, 65]),
    "Dm9": (38, [53, 57, 60, 64]),
    "Bbmaj7": (46, [50, 53, 57, 62]),
    "Gm9": (43, [53, 57, 58, 62]),
    "Csus": (48, [53, 55, 60, 65]),
    "C": (48, [52, 55, 60, 64]),
    "Am7": (45, [52, 55, 57, 60]),
}
PROG = (
    ["Fmaj9", "Dm9", "Bbmaj7"]  # S1
    + ["Gm9", "Csus", "Am7", "Dm9", "Bbmaj7"]  # S2
    + ["Bbmaj7", "Gm9", "Csus"]  # S3
    + ["F", "Am7", "Dm9", "Bbmaj7", "Gm9", "Csus"]  # S4
    + ["F", "Am7", "Dm9", "Bbmaj7", "F", "Csus"]  # S5
    + ["Bbmaj7", "C", "Dm9", "Csus"]  # S6
    + ["Fmaj9", "Fmaj9", "Fmaj9"]  # S7
)
assert len(PROG) == 30

# melodía: (compás, tiempo, nota MIDI, duración en s)
MOTIF = [(0, 1.0, 72, 0.9), (0, 2.0, 74, 0.45), (0, 2.5, 72, 1.4), (1, 1.0, 69, 0.9), (1, 2.0, 67, 1.8), (2, 1.0, 65, 0.9), (2, 2.0, 69, 1.9)]
MEL = []
MEL += MOTIF  # S1: se presenta
MEL += [(4, 1.0, 72, 0.9), (4, 2.0, 70, 1.6), (6, 1.0, 69, 0.9), (6, 2.0, 67, 1.6)]  # S2: respuestas cortas
MEL += [(9, 0.0, 69, 3.6)]  # S3: una nota larga
MEL += [(b + 11, q, m, d) for (b, q, m, d) in MOTIF]  # S4: vuelve el motivo
MEL += [(14, 1.0, 74, 0.9), (14, 2.0, 72, 0.9), (15, 0.0, 70, 1.4), (15, 2.0, 67, 1.8)]
MEL += [(17, 1.0, 77, 0.9), (17, 2.0, 79, 0.45), (17, 2.5, 77, 1.4), (18, 1.0, 76, 0.9), (18, 2.0, 72, 1.8),
        (19, 1.0, 74, 0.9), (19, 2.0, 77, 1.9), (21, 1.0, 76, 0.9), (21, 2.0, 74, 0.9), (22, 0.0, 72, 1.8)]  # S5: variación
MEL += [(23, 1.0, 74, 0.9), (23, 2.0, 77, 0.9), (24, 0.0, 79, 1.4), (24, 2.0, 76, 0.9),
        (25, 0.0, 77, 1.4), (25, 2.0, 81, 1.8), (26, 1.0, 79, 1.6)]  # S6: sube
MEL += [(27, 0.0, 77, 3.0), (28, 1.0, 72, 2.4)]  # S7: resuelve en Fa

pad, keys, lead, low = Bus(), Bus(), Bus(), Bus()

for b, name in enumerate(PROG[:27]):
    bs, voices = CH[name]
    for j, m in enumerate(voices):
        pad.add(pad_note(m, BAR + 0.4, b * 5 + j), tb(b), 0.11, pan=-0.4 + j * 0.27)
    low.add(bass(bs, BAR - 0.1, 0.55 if 8 <= b <= 10 else 0.8), tb(b))
    # piano eléctrico: S2 en corcheas (movimiento), resto en blancas (calma), S3 sin piano
    if 3 <= b <= 7:
        seq = [voices[0], voices[2], voices[1], voices[3], voices[2], voices[1], voices[3], voices[2]]
        for e in range(8):
            if tb(b, e * 0.5) <= 15.6:
                keys.add(epiano(seq[e] + 12, 0.2 + (0.04 if e == 0 else 0), 1.0), tb(b, e * 0.5), pan=-0.3 + 0.08 * e)
    elif not 8 <= b <= 10:
        for q in (0, 2):
            for j, m in enumerate(voices):
                keys.add(epiano(m + 12, 0.11, 2.4), tb(b, q) + j * 0.012, pan=-0.25 + j * 0.17)
bs, voices = CH["Fmaj9"]
for j, m in enumerate(voices + [72]):
    pad.add(pad_note(m, 3.2, 300 + j), tb(27), 0.11, pan=-0.4 + j * 0.2)
    keys.add(epiano(m + 12, 0.13, 3.0), tb(27) + j * 0.05, pan=-0.3 + j * 0.15)
low.add(bass(41, 3.0, 0.75), tb(27))

for b, q, m, d in MEL:
    lead.add(flute(m, d, 0.9), tb(b, q), pan=0.08)

# ── mezcla ───────────────────────────────────────────────────────────────
pad_s = np.stack([filt(ch, "lowpass", 2000) for ch in pad.st()])
keys_s = np.stack([filt(ch, "lowpass", 3200) for ch in keys.st()])
lead_s = np.stack([filt(ch, "lowpass", 4500) for ch in lead.st()])
low_s = np.stack([filt(ch, "lowpass", 380) for ch in low.st()])

ir_len = int(3.0 * SR)
tir = np.arange(ir_len) / SR
irs = []
for s in (31, 42):
    ir = filt(np.random.default_rng(s).standard_normal(ir_len), "lowpass", 3800) * np.exp(-tir / 0.95)
    irs.append(ir / np.sqrt(np.sum(ir**2)))
send = 0.6 * pad_s + 0.8 * keys_s + 0.7 * lead_s
rev = np.stack([fftconvolve(send[c], irs[c])[:N] for c in range(2)]) * 0.42

mix = 0.85 * pad_s + 0.85 * keys_s + 0.75 * lead_s + 0.7 * low_s + rev
mix = np.stack([filt(filt(ch, "highpass", 45), "lowpass", 6000) for ch in mix])

# nivelador lento (cambios de ganancia de ≈2 s) para que no haya saltos de volumen
mono = np.mean(mix, axis=0)
win = int(1.5 * SR)
rms = np.sqrt(np.convolve(mono**2, np.ones(win) / win, mode="same") + 1e-9)
target = np.median(rms[int(2 * SR) : int(56 * SR)])
gain = np.convolve(np.clip(target / rms, 0.6, 1.6), np.ones(int(2.0 * SR)) / int(2.0 * SR), mode="same")
tt = np.arange(N) / SR
gain = np.where((tt < 2.0) | (tt > 56.0), np.minimum(gain, 1.0), gain)
fade = np.clip(tt / 2.0, 0, 1) * np.where(tt > 56.5, np.clip((60 - tt) / 3.5, 0, 1) ** 1.6, 1)
mix = mix * gain * fade

rms_all = np.sqrt(np.mean(mix[:, int(2 * SR) : int(56 * SR)] ** 2))
mix *= 10 ** (LEVEL / 20) / rms_all
peak = np.max(np.abs(mix))
if peak > 10 ** (-9 / 20):
    mix *= 10 ** (-9 / 20) / peak
mix[:, -int(0.05 * SR) :] *= np.linspace(1, 0, int(0.05 * SR))

OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes((mix.T * 32767).astype("<i2").tobytes())
print(f"{OUT} 60.00s  pico {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS")

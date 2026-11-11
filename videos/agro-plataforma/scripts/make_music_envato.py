"""Edita "Presentación" de AudioPizza (Envato Elements, licenciada) a 60 s para el video agro.

El archivo fuente NO está en el repositorio (licencia por proyecto). Para regenerar:
  1. Descargá el tema desde Envato y dejá el WAV en assets/audio/envato/audiopizza_presentation_main.wav
  2. python3 scripts/make_music_envato.py   (numpy + scipy)
Salida: assets/audio/agro-musica-envato.wav (48 kHz, 16 bit, estéreo, 60,0 s)

Grilla medida del tema: 115 BPM, compás = 2,08696 s, frases de 8 compases que empiezan en
1,051 · 17,747 · 34,443 · 51,139 · 67,835 · 84,530 · 101,226 · 117,922 · 134,618 (golpe final).

Edición (un solo corte, en tiempo fuerte y con la armonía en la misma posición):
  video  0,000 → 30,556  =  tema  3,887 → 34,443   intro y subida, entra con fundido
  video 30,556 → 47,252  =  tema 34,443 → 51,139   gran entrada con "Toda la información del campo
                                                   en una plataforma" ya en pantalla
  video 47,252 → 60,000  =  tema 126,270 → 139,02  últimos 4 compases + golpe final en 55,6
                                                   (con el cierre armado) y cola que se apaga
                                                   junto con los 2 s de imagen quieta
Niveles por escena (dB relativos) y nivel final ≈ -22 LUFS integrados.
"""

import wave
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets/audio/envato/audiopizza_presentation_main.wav"
OUT = ROOT / "assets/audio/agro-musica-envato.wav"
GAIN_DB = -12.4  # calibrado para ≈ -22 LUFS integrados (se mide con ffmpeg ebur128)

BAR = 4 * 60 / 115
DROP1 = 34.443  # gran entrada del tema
HIT = 134.618  # golpe final del tema
V_HIT = 55.6  # golpe final: el tema suena ≈2 s después del golpe, así se apaga con la imagen quieta
V_DROP = V_HIT - 12 * BAR  # 30.556
V_CUT = V_DROP + 8 * BAR  # 47.252
SEGMENTS = [  # (inicio en el tema, inicio en el video, fin en el video)
    (DROP1 - V_DROP, 0.0, V_DROP),
    (DROP1, V_DROP, V_CUT),
    (HIT - 4 * BAR, V_CUT, 60.0),
]
# automatización de nivel en dB: (segundo del video, dB)
LEVELS = [
    (0.0, -2.0), (5.8, -2.0), (6.4, 0.0),  # apertura un poco más baja, el caos completo
    (15.4, 0.0), (16.4, -5.0), (21.4, -5.0),  # pausa: baja ~5 dB, sin corte
    (22.4, -3.0), (30.2, -2.0), (30.6, 0.0),  # convergencia: sube hacia la entrada
    (47.2, 0.0), (47.8, 1.0), (55.4, 1.0), (55.6, 1.5), (58.0, 0.5), (60.0, 0.5),
]
XF = 0.025  # crossfade en los cortes (s)

w = wave.open(str(SRC))
sr = w.getframerate()
src = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2).astype(np.float64) / 32768
N = int(60.0 * sr)
out = np.zeros((N, 2))
xf = int(XF * sr)
for k, (s0, v0, v1) in enumerate(SEGMENTS):
    # cada tramo arranca un poco antes del corte para cruzarse con el anterior
    pre = xf if k > 0 else 0
    i_src = int(round(s0 * sr)) - pre - int(0.010 * sr) * (k > 0)
    i_v = int(round(v0 * sr)) - pre - int(0.010 * sr) * (k > 0)
    length = int(round(v1 * sr)) - i_v + (xf if k < len(SEGMENTS) - 1 else 0)
    length = min(length, N - i_v, len(src) - i_src)
    seg = src[i_src : i_src + length].copy()
    ramp = np.sin(np.linspace(0, np.pi / 2, xf)) ** 2
    if k > 0:
        seg[:xf] *= ramp[:, None]
    if k < len(SEGMENTS) - 1:
        seg[-xf:] *= ramp[::-1, None]
    out[i_v : i_v + length] += seg

t = np.arange(N) / sr
xs, ys = zip(*LEVELS)
gain_db = np.interp(t, xs, ys) + GAIN_DB
gain = 10 ** (gain_db / 20)
gain *= np.clip(t / 1.5, 0, 1) ** 1.5  # entrada con fundido (arranca a mitad de la intro)
gain *= np.where(t > 58.0, np.clip((60.0 - t) / 2.0, 0, 1) ** 1.6, 1)  # cola que se apaga
out *= gain[:, None]

out48 = resample_poly(out, 160, 147, axis=0)[: int(60.0 * 48000)]
peak = np.max(np.abs(out48))
assert peak < 0.98, f"pico {peak}"
OUT.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(OUT), "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(48000)
    wf.writeframes((out48 * 32767).astype("<i2").tobytes())
print(f"{OUT} {len(out48) / 48000:.2f}s  pico {20 * np.log10(peak):.1f} dBFS")
print("cortes en el video:", [round(v0, 3) for _, v0, _ in SEGMENTS[1:]], f" golpe final en {V_HIT:.3f}")

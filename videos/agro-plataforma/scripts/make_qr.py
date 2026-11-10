"""QR de la encuesta → assets/qr-encuesta.svg (módulos oscuros sobre crema, zona de silencio de 4).

Para cambiar el destino, editá URL y corré: python3 scripts/make_qr.py
"""
from pathlib import Path

import qrcode

URL = "https://encuestas.webexperiencepro.com/asesores"
OUT = Path(__file__).resolve().parent.parent / "assets/qr-encuesta.svg"

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
qr.add_data(URL)
qr.make(fit=True)
m = qr.get_matrix()  # incluye el borde
n = len(m)
d = "".join(f"M{x} {y}h1v1h-1z" for y, row in enumerate(m) for x, v in enumerate(row) if v)
OUT.write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
    f'<rect width="{n}" height="{n}" fill="#f4f1e8"/><path d="{d}" fill="#0b0b0b"/></svg>\n'
)
print(f"{OUT} versión {qr.version}, {n}×{n} módulos → {URL}")

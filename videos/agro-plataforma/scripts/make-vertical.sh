#!/usr/bin/env bash
# Genera la versión 9:16 en vertical/ (1080×1920) desde index.html (1920×1080).
# Editá textos en index.html y volvé a correr: bash scripts/make-vertical.sh
# vertical/ es un proyecto autónomo (copia assets/ y vendor/) porque HyperFrames
# admite una sola composición raíz por carpeta.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf vertical && mkdir -p vertical
cp -r assets vendor vertical/
sed -e 's/1920/__W__/g; s/1080/1920/g; s/__W__/1080/g' \
    -e 's/class="land"/class="port"/' \
    -e 's/Agro plataforma · 16:9/Agro plataforma · 9:16/' \
    index.html > vertical/index.html
echo "vertical/index.html generado"

---
workflow: general-video
flow: automation
storyboard: no
message: "The Peugeot bottle carries the brand's own line: Drive your future."
destination: shorts
aspect: 1080x1920
language: en
length: 15s
angle: product-promo
---

## Intent

"Create a full dynamic promotion video for this bottle. Using Motion effects and must be a
profesional video, not more than 15 seg." Vertical (9:16) confirmed by the user.

## Assets

- assets/img/hero.jpg — the user's product photo (1536×1024), used for macro camera moves and the zoom-out reveal
- assets/img/bottle.png — bottle cut out of the photo (hyperframes remove-background), 2× Lanczos upscale
- assets/img/plate-shield.jpg — left part of the photo (shield wall) used as the hero backdrop

## Notes

- Copy uses only text visible on the product ("PEUGEOT", "DRIVE YOUR FUTURE") and visible
  details (cap & loop, lion emblem, tricolour). No performance claims were invented.
- Soundtrack is synthesized + bundled SFX (scripts/make_audio.py); no external music.

---
workflow: general-video
flow: automation
storyboard: no
message: "Every frame of motion is a deliberate design decision — and I can make all of them."
aspect: 1920x1080
language: en
length: 15s
angle: showreel
---

## Intent

"Make a dynamic 15-second motion graphics video that shows what an incredible
motion designer you are, like it's your showreel for a résumé. go all out."

A résumé showreel for Claude as a motion designer: six numbered skill scenes cut
on a fast pulse, framed by persistent reel chrome (timecode, scene index,
progress rail), ending on a signature lockup.

## Notes

- Inferred (not confirmed by the user): 16:9 1920x1080, English copy, dark warm
  palette with one signal-orange accent, no audio.
- No audio: local music generation is blocked (huggingface.co denied by the
  environment network policy); the piece is designed to read silent.
- cdn.jsdelivr.net is blocked: GSAP is vendored at `vendor/gsap.min.js` from npm.
- All on-screen numbers are true of this video (450 frames = 15 s × 30 fps;
  shot lengths match the real scene timings).

# Changelog

## 1.1.0 — 2026-07-19

- Replace the single-pass redraw workflow with four independently enhanced overlapping tiles.
- Use the built-in `image_gen` editor only; no API key or local upscaler model is required.
- Add exact-aspect 4K tile preparation with configurable 8%–18% overlap.
- Add full-frame reference guidance for geometry, color, lighting, logos, and edge continuity.
- Add low-frequency color matching and complementary cosine-feathered seamless stitching.
- Reject tile aspect-ratio drift above 2% and report exact 4K, blend-weight, and seam metrics.
- Validate the workflow on a 1920×1080 automotive image and produce a 3840×2160 PNG without cropping, padding, or canvas extension.

## 1.0.0 — 2026-07-12

- First public release.
- Add true-4K long-edge normalization and JSON verification.
- Add structure-locking and material-redraw workflow.
- Add Chinese installation and usage documentation.

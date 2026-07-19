# Changelog

## 1.2.0 — 2026-07-20

- Mark `v1.1.0` as defective because whole-tile feathering softened detail and unregistered tiles could create blur, ghosting, or incorrect joins.
- Add one globally consistent whole-image `image_gen` restoration at the highest native output size before tiling.
- Remove fixed-2K master normalization; split the actual native master directly into four overlapping tiles.
- Add category-aware structural parsing and physical material regeneration guidance for the whole-image master.
- Add ECC affine registration followed by displacement-limited dense optical flow for every generated tile.
- Preserve the whole-image master as the only low-frequency geometry, color, and lighting source.
- Replace whole-tile feathering with evidence-gated high-frequency residual fusion; complementary cosine weights now blend residuals only.
- Reject or down-weight misregistered generated detail and provide a safe native-master tile fallback after one failed retry.
- Report native-master dimensions, registration improvement, accepted-detail coverage, residual seam metrics, and exact-aspect 4K validation.
- Validate the complete five-generation workflow on a 326×264 automotive image and produce a 3840×3110 PNG without cropping, padding, or canvas extension.

## 1.1.0 — 2026-07-19

**Defective — do not use. Upgrade to 1.2.0.** Whole-tile feathering can soften detail, and the absence of geometry registration can cause blur, ghosting, or incorrect joins.

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

#!/usr/bin/env python3
"""Color-match and seamlessly stitch four overlapping restored tiles."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageFilter
except ImportError as exc:
    raise SystemExit("Pillow and NumPy are required. Install them from requirements.txt") from exc


NAMES = ("tl", "tr", "bl", "br")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seamlessly stitch four enhanced 4K tiles")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--tl", type=Path, required=True)
    parser.add_argument("--tr", type=Path, required=True)
    parser.add_argument("--bl", type=Path, required=True)
    parser.add_argument("--br", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--color-strength", type=float, default=0.82)
    parser.add_argument("--color-blur-radius", type=float, default=32.0)
    parser.add_argument("--max-color-shift", type=float, default=28.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def open_rgb(path: Path) -> Image.Image:
    if not path.is_file():
        raise SystemExit(f"Image not found: {path}")
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        image.load()
    return image


def cosine_left_weight(xs: np.ndarray, start: int, end: int) -> np.ndarray:
    weight = np.ones_like(xs, dtype=np.float32)
    weight[xs >= end] = 0.0
    zone = (xs > start) & (xs < end)
    phase = (xs[zone] - start) / max(1, end - start)
    weight[zone] = 0.5 * (1.0 + np.cos(math.pi * phase))
    return weight


def cosine_top_weight(ys: np.ndarray, start: int, end: int) -> np.ndarray:
    return cosine_left_weight(ys, start, end)


def low_frequency_match(
    tile: Image.Image,
    reference: Image.Image,
    strength: float,
    blur_radius: float,
    max_shift: float,
) -> Image.Image:
    tile_arr = np.asarray(tile, dtype=np.float32)
    tile_low = np.asarray(tile.filter(ImageFilter.GaussianBlur(blur_radius)), dtype=np.float32)
    ref_low = np.asarray(reference.filter(ImageFilter.GaussianBlur(blur_radius)), dtype=np.float32)
    correction = np.clip(ref_low - tile_low, -max_shift, max_shift) * strength
    corrected = np.clip(tile_arr + correction, 0, 255).astype(np.uint8)
    return Image.fromarray(corrected)


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not manifest_path.is_file():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"Output exists; choose another path or use --overwrite: {output_path}")
    if not 0.0 <= args.color_strength <= 1.0:
        raise SystemExit("--color-strength must be between 0 and 1")
    if args.color_blur_radius <= 0 or args.max_color_shift < 0:
        raise SystemExit("Color matching parameters must be positive")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("tile_count") != 4:
        raise SystemExit("Manifest must describe exactly four tiles")
    width, height = manifest["canvas_size"]
    if max(width, height) != 3840:
        raise SystemExit("Manifest canvas is not true 4K")
    base_path = Path(manifest["base_4k"])
    base = open_rgb(base_path)
    if base.size != (width, height):
        raise SystemExit("Base image size does not match manifest")

    provided = {
        "tl": args.tl.expanduser().resolve(),
        "tr": args.tr.expanduser().resolve(),
        "bl": args.bl.expanduser().resolve(),
        "br": args.br.expanduser().resolve(),
    }
    corrected: dict[str, np.ndarray] = {}
    tile_reports: dict[str, dict] = {}
    for name in NAMES:
        box = manifest["tiles"][name]["box"]
        x0, y0, x1, y1 = box
        expected_size = (x1 - x0, y1 - y0)
        image = open_rgb(provided[name])
        source_size = image.size
        source_ratio = source_size[0] / source_size[1]
        expected_ratio = expected_size[0] / expected_size[1]
        ratio_error = abs(source_ratio / expected_ratio - 1) * 100
        if ratio_error > 2.0:
            raise SystemExit(
                f"Tile {name} aspect ratio differs by {ratio_error:.3f}%; regenerate it without reframing"
            )
        if image.size != expected_size:
            image = image.resize(expected_size, Image.Resampling.LANCZOS)
        reference = base.crop(tuple(box))
        image = low_frequency_match(
            image,
            reference,
            args.color_strength,
            args.color_blur_radius,
            args.max_color_shift,
        )
        corrected[name] = np.asarray(image, dtype=np.float32)
        tile_reports[name] = {
            "input": str(provided[name]),
            "source_size": list(source_size),
            "target_size": list(expected_size),
            "source_aspect_ratio_error_percent": ratio_error,
            "box": box,
        }

    split = manifest["split"]
    rs, le = split["right_start"], split["left_end"]
    bs, te = split["bottom_start"], split["top_end"]
    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    left = cosine_left_weight(xs, rs, le)
    right = 1.0 - left
    top = cosine_top_weight(ys, bs, te)
    bottom = 1.0 - top
    global_weights = {
        "tl": top[:, None] * left[None, :],
        "tr": top[:, None] * right[None, :],
        "bl": bottom[:, None] * left[None, :],
        "br": bottom[:, None] * right[None, :],
    }

    accumulator = np.zeros((height, width, 3), dtype=np.float32)
    weight_sum = np.zeros((height, width), dtype=np.float32)
    for name in NAMES:
        x0, y0, x1, y1 = manifest["tiles"][name]["box"]
        weight = global_weights[name][y0:y1, x0:x1]
        accumulator[y0:y1, x0:x1] += corrected[name] * weight[:, :, None]
        weight_sum[y0:y1, x0:x1] += weight
    if float(weight_sum.min()) < 0.999 or float(weight_sum.max()) > 1.001:
        raise SystemExit("Blend weights do not sum to one across the canvas")
    composite = np.clip(accumulator / weight_sum[:, :, None], 0, 255).astype(np.uint8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = Image.fromarray(composite)
    save_kwargs: dict = {"compress_level": 6}
    with Image.open(base_path) as base_opened:
        if base_opened.info.get("icc_profile"):
            save_kwargs["icc_profile"] = base_opened.info["icc_profile"]
        if base_opened.info.get("dpi"):
            save_kwargs["dpi"] = base_opened.info["dpi"]
    output.save(output_path, format="PNG", **save_kwargs)

    vertical_delta = float(
        np.mean(np.abs(composite[:, split["mid_x"]].astype(np.float32) - composite[:, split["mid_x"] - 1].astype(np.float32)))
    )
    horizontal_delta = float(
        np.mean(np.abs(composite[split["mid_y"]].astype(np.float32) - composite[split["mid_y"] - 1].astype(np.float32)))
    )
    result = {
        "manifest": str(manifest_path),
        "output": str(output_path),
        "output_size": [width, height],
        "output_long_edge": max(width, height),
        "tile_count": 4,
        "overlap_x": manifest["overlap_x"],
        "overlap_y": manifest["overlap_y"],
        "color_matched": True,
        "color_strength": args.color_strength,
        "color_blur_radius": args.color_blur_radius,
        "blend_mode": "complementary-cosine",
        "weight_sum_min": float(weight_sum.min()),
        "weight_sum_max": float(weight_sum.max()),
        "vertical_center_delta": vertical_delta,
        "horizontal_center_delta": horizontal_delta,
        "tiles": tile_reports,
        "cropped": False,
        "padded": False,
        "canvas_extended": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

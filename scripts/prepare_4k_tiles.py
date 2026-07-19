#!/usr/bin/env python3
"""Create an exact-aspect 4K base and four overlapping 2x2 tiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError as exc:
    raise SystemExit("Pillow is required. Install it with: python3 -m pip install Pillow") from exc


SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
TILE_NAMES = ("tl", "tr", "bl", "br")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare four overlapping tiles on a 4K canvas")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--long-edge", type=int, default=3840)
    parser.add_argument("--overlap-percent", type=float, default=12.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def target_size(width: int, height: int, long_edge: int) -> tuple[int, int]:
    if width >= height:
        return long_edge, max(1, round(height * long_edge / width))
    return max(1, round(width * long_edge / height)), long_edge


def save_png(image: Image.Image, path: Path, info: dict) -> None:
    kwargs: dict = {"compress_level": 6}
    if info.get("icc_profile"):
        kwargs["icc_profile"] = info["icc_profile"]
    if info.get("dpi"):
        kwargs["dpi"] = info["dpi"]
    image.save(path, format="PNG", **kwargs)


def has_real_transparency(image: Image.Image, info: dict) -> bool:
    if "A" in image.getbands():
        return image.getchannel("A").getextrema()[0] < 255
    if info.get("transparency") is not None:
        return image.convert("RGBA").getchannel("A").getextrema()[0] < 255
    return False


def even_overlap(length: int, percent: float) -> int:
    minimum = max(2, min(64, length // 8))
    maximum = max(2, length // 3)
    overlap = min(max(minimum, round(length * percent / 100)), maximum)
    if overlap % 2:
        overlap = overlap + 1 if overlap + 1 <= maximum else overlap - 1
    return max(2, overlap)


def main() -> int:
    args = parse_args()
    source = args.input.expanduser().resolve()
    out_dir = args.output_dir.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Input file not found: {source}")
    if source.suffix.lower() not in SUPPORTED:
        raise SystemExit(f"Unsupported input format: {source.suffix}")
    if args.long_edge != 3840:
        raise SystemExit("This skill defines true 4K as a 3840 px long edge")
    if not 8.0 <= args.overlap_percent <= 18.0:
        raise SystemExit("--overlap-percent must be between 8 and 18")

    outputs = [out_dir / "base_4k.png", out_dir / "manifest.json"]
    outputs.extend(out_dir / f"tile_{name}.png" for name in TILE_NAMES)
    existing = [path for path in outputs if path.exists()]
    if existing and not args.overwrite:
        raise SystemExit("Output files already exist; choose another directory or use --overwrite")
    out_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as opened:
        if getattr(opened, "is_animated", False):
            raise SystemExit("Animated images are not supported")
        info = dict(opened.info)
        image = ImageOps.exif_transpose(opened)
        image.load()
    if has_real_transparency(image, info):
        raise SystemExit("Input contains real transparent pixels; choose an opaque background first")
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")

    original_size = image.size
    canvas_size = target_size(*original_size, args.long_edge)
    base = image.resize(canvas_size, Image.Resampling.LANCZOS)
    base_path = out_dir / "base_4k.png"
    save_png(base, base_path, info)

    width, height = canvas_size
    overlap_x = even_overlap(width, args.overlap_percent)
    overlap_y = even_overlap(height, args.overlap_percent)
    mid_x, mid_y = width // 2, height // 2
    right_start = mid_x - overlap_x // 2
    left_end = mid_x + overlap_x // 2
    bottom_start = mid_y - overlap_y // 2
    top_end = mid_y + overlap_y // 2
    boxes = {
        "tl": [0, 0, left_end, top_end],
        "tr": [right_start, 0, width, top_end],
        "bl": [0, bottom_start, left_end, height],
        "br": [right_start, bottom_start, width, height],
    }

    tiles: dict[str, dict] = {}
    for name, box in boxes.items():
        tile_path = out_dir / f"tile_{name}.png"
        tile = base.crop(tuple(box))
        save_png(tile, tile_path, info)
        tiles[name] = {
            "path": str(tile_path),
            "box": box,
            "size": list(tile.size),
            "aspect_ratio": tile.width / tile.height,
        }

    manifest = {
        "source": str(source),
        "original_size": list(original_size),
        "canvas_size": list(canvas_size),
        "output_long_edge": max(canvas_size),
        "base_4k": str(base_path),
        "tile_count": 4,
        "overlap_percent": args.overlap_percent,
        "overlap_x": left_end - right_start,
        "overlap_y": top_end - bottom_start,
        "split": {
            "mid_x": mid_x,
            "mid_y": mid_y,
            "right_start": right_start,
            "left_end": left_end,
            "bottom_start": bottom_start,
            "top_end": top_end,
        },
        "tiles": tiles,
        "cropped": False,
        "padded": False,
        "canvas_extended": False,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**manifest, "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Aspect-ratio-preserving 4K raster upscaler with machine-readable verification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError as exc:
    raise SystemExit("Pillow is required. Install it with: python3 -m pip install Pillow") from exc


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upscale a raster image to a 3840 px long edge without cropping or padding."
    )
    parser.add_argument("input", type=Path, help="Input raster image")
    parser.add_argument("--output", type=Path, help="Output path; defaults to <stem>_4k<suffix>")
    parser.add_argument(
        "--aspect-reference",
        type=Path,
        help="Use another image's dimensions as the required output aspect ratio",
    )
    parser.add_argument("--long-edge", type=int, default=3840, help="Target long edge (default: 3840)")
    parser.add_argument(
        "--force-exact",
        action="store_true",
        help="Downscale images already larger than the target so the long edge is exact",
    )
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing output")
    parser.add_argument(
        "--no-sharpen", action="store_true", help="Disable the mild post-resize unsharp mask"
    )
    return parser.parse_args()


def default_output(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_4k{input_path.suffix}")


def target_size(width: int, height: int, long_edge: int) -> tuple[int, int]:
    if width >= height:
        return long_edge, max(1, round(height * long_edge / width))
    return max(1, round(width * long_edge / height)), long_edge


def save_image(image: Image.Image, output: Path, source_info: dict) -> None:
    suffix = output.suffix.lower()
    kwargs: dict = {}
    if source_info.get("icc_profile"):
        kwargs["icc_profile"] = source_info["icc_profile"]
    if source_info.get("dpi"):
        kwargs["dpi"] = source_info["dpi"]

    if suffix in {".jpg", ".jpeg"}:
        if image.mode not in {"RGB", "L"}:
            background = Image.new("RGB", image.size, "white")
            if "A" in image.getbands():
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image.convert("RGB"))
            image = background
        kwargs.update(quality=95, subsampling=0, optimize=True)
    elif suffix == ".png":
        kwargs.update(compress_level=6)
    elif suffix == ".webp":
        kwargs.update(quality=95, method=6)
    elif suffix in {".tif", ".tiff"}:
        kwargs.update(compression="tiff_lzw")

    image.save(output, **kwargs)


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_path = (args.output or default_output(input_path)).expanduser().resolve()
    aspect_reference = args.aspect_reference.expanduser().resolve() if args.aspect_reference else None

    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise SystemExit(f"Unsupported input format: {input_path.suffix}")
    if aspect_reference and not aspect_reference.is_file():
        raise SystemExit(f"Aspect-reference file not found: {aspect_reference}")
    if output_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise SystemExit(f"Unsupported output format: {output_path.suffix}")
    if args.long_edge < 1:
        raise SystemExit("--long-edge must be a positive integer")
    if output_path == input_path and not args.overwrite:
        raise SystemExit("Refusing to overwrite the input without --overwrite")
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"Output already exists; choose another path or pass --overwrite: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as opened:
        if getattr(opened, "is_animated", False):
            raise SystemExit("Animated images are not supported; provide a single still frame")
        source_info = dict(opened.info)
        image = ImageOps.exif_transpose(opened)
        image.load()

    original_size = image.size
    original_long_edge = max(original_size)
    if aspect_reference:
        with Image.open(aspect_reference) as reference_opened:
            reference = ImageOps.exif_transpose(reference_opened)
            reference_size = reference.size
    else:
        reference_size = original_size

    source_ratio = original_size[0] / original_size[1]
    reference_ratio = reference_size[0] / reference_size[1]
    source_to_reference_ratio_difference = abs(source_ratio / reference_ratio - 1) * 100
    if aspect_reference and source_to_reference_ratio_difference > 2.0:
        raise SystemExit(
            "Redrawn image aspect ratio differs from the original by more than 2%; "
            "retry the redraw instead of forcing a large distortion"
        )

    if original_long_edge >= args.long_edge and not args.force_exact and not aspect_reference:
        resized = image.copy()
        operation = "preserved-existing-resolution"
    else:
        size = target_size(*reference_size, args.long_edge)
        resized = image.resize(size, Image.Resampling.LANCZOS)
        if not args.no_sharpen:
            resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=3))
        if aspect_reference:
            operation = "normalized-to-reference-aspect"
        else:
            operation = "upscaled" if original_long_edge < args.long_edge else "downscaled-to-exact"

    save_image(resized, output_path, source_info)

    with Image.open(output_path) as verified:
        output_size = verified.size

    output_ratio = output_size[0] / output_size[1]
    ratio_error = abs(output_ratio / reference_ratio - 1) * 100
    result = {
        "input": str(input_path),
        "output": str(output_path),
        "aspect_reference": str(aspect_reference) if aspect_reference else None,
        "operation": operation,
        "input_size": list(original_size),
        "reference_size": list(reference_size),
        "output_size": list(output_size),
        "output_long_edge": max(output_size),
        "target_long_edge": args.long_edge,
        "input_aspect_ratio": source_ratio,
        "reference_aspect_ratio": reference_ratio,
        "output_aspect_ratio": output_ratio,
        "aspect_ratio_error_percent": ratio_error,
        "source_to_reference_ratio_difference_percent": source_to_reference_ratio_difference,
        "cropped": False,
        "padded": False,
        "canvas_extended": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if ratio_error > 0.05:
        print("Aspect-ratio verification failed", file=sys.stderr)
        return 2
    if operation in {"upscaled", "downscaled-to-exact", "normalized-to-reference-aspect"} and max(output_size) != args.long_edge:
        print("Long-edge verification failed", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

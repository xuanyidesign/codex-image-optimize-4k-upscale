#!/usr/bin/env python3
"""Register four restored tiles and fuse only their trusted high-frequency residuals."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageFilter
except ImportError as exc:
    raise SystemExit(
        "Pillow, NumPy and OpenCV are required. Install them from requirements.txt"
    ) from exc


NAMES = ("tl", "tr", "bl", "br")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Geometrically register four tiles and fuse only high-frequency residuals"
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--tl", type=Path, required=True)
    parser.add_argument("--tr", type=Path, required=True)
    parser.add_argument("--bl", type=Path, required=True)
    parser.add_argument("--br", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--detail-strength", type=float, default=1.32)
    parser.add_argument("--base-sharpen", type=float, default=0.62)
    parser.add_argument("--registration-edge", type=int, default=900)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def open_rgb(path: Path) -> Image.Image:
    if not path.is_file():
        raise SystemExit(f"Image not found: {path}")
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        image.load()
    return image


def gaussian(array: np.ndarray, radius: float) -> np.ndarray:
    image = Image.fromarray(np.clip(array * 255.0, 0, 255).astype(np.uint8))
    return np.asarray(image.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def gradients(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3) / 8.0
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3) / 8.0
    return gx, gy, np.sqrt(gx * gx + gy * gy)


def edge_image(rgb: np.ndarray) -> np.ndarray:
    _, _, magnitude = gradients(cv2.GaussianBlur(luminance(rgb), (0, 0), 0.8))
    scale = float(np.percentile(magnitude, 97)) + 1e-6
    return np.clip(magnitude / scale, 0, 1).astype(np.float32)


def resize_array(array: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return cv2.resize(array, size, interpolation=cv2.INTER_AREA)


def normalized_edge_error(reference: np.ndarray, moving: np.ndarray) -> float:
    ref = edge_image(reference)
    mov = edge_image(moving)
    return float(np.mean(np.abs(ref - mov)))


def validate_affine(matrix: np.ndarray, width: int, height: int) -> tuple[bool, str]:
    linear = matrix[:, :2]
    singular = np.linalg.svd(linear, compute_uv=False)
    if singular.min() < 0.94 or singular.max() > 1.06:
        return False, "affine-scale-out-of-range"
    if abs(float(matrix[0, 1])) > 0.055 or abs(float(matrix[1, 0])) > 0.055:
        return False, "affine-shear-out-of-range"
    if abs(float(matrix[0, 2])) > width * 0.05 or abs(float(matrix[1, 2])) > height * 0.05:
        return False, "affine-translation-out-of-range"
    return True, "accepted"


def register_candidate(
    reference: np.ndarray, moving: np.ndarray, registration_edge: int
) -> tuple[np.ndarray, dict]:
    """ECC affine registration followed by bounded dense optical flow."""
    height, width = reference.shape[:2]
    scale = min(1.0, registration_edge / max(width, height))
    small_size = (max(96, round(width * scale)), max(96, round(height * scale)))
    ref_small = resize_array(reference, small_size)
    mov_small = resize_array(moving, small_size)
    ref_edge = edge_image(ref_small)
    mov_edge = edge_image(mov_small)
    before = float(np.mean(np.abs(ref_edge - mov_edge)))

    affine = np.eye(2, 3, dtype=np.float32)
    affine_reason = "accepted"
    ecc = None
    try:
        criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5)
        ecc, candidate_affine = cv2.findTransformECC(
            ref_edge,
            mov_edge,
            affine,
            cv2.MOTION_AFFINE,
            criteria,
            None,
            3,
        )
        valid, affine_reason = validate_affine(candidate_affine, *small_size)
        if valid:
            affine = candidate_affine
        else:
            affine = np.eye(2, 3, dtype=np.float32)
    except cv2.error:
        affine_reason = "ecc-failed"

    affine_small = cv2.warpAffine(
        mov_small,
        affine,
        small_size,
        flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE,
    )
    affine_edge = edge_image(affine_small)

    flow = cv2.calcOpticalFlowFarneback(
        (ref_edge * 255).astype(np.uint8),
        (affine_edge * 255).astype(np.uint8),
        None,
        pyr_scale=0.5,
        levels=5,
        winsize=31,
        iterations=5,
        poly_n=7,
        poly_sigma=1.5,
        flags=cv2.OPTFLOW_FARNEBACK_GAUSSIAN,
    )
    flow = cv2.GaussianBlur(flow, (0, 0), 2.0)
    displacement = np.sqrt(np.sum(np.square(flow), axis=2))
    flow_p95 = float(np.percentile(displacement, 95))
    max_flow = max(3.0, min(small_size) * 0.045)
    dense_used = flow_p95 <= max_flow
    if not dense_used:
        flow.fill(0)

    grid_x, grid_y = np.meshgrid(
        np.arange(small_size[0], dtype=np.float32),
        np.arange(small_size[1], dtype=np.float32),
    )
    registered_small = cv2.remap(
        affine_small,
        grid_x + flow[..., 0],
        grid_y + flow[..., 1],
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REPLICATE,
    )
    after = normalized_edge_error(ref_small, registered_small)
    if after >= before * 0.985:
        affine = np.eye(2, 3, dtype=np.float32)
        affine_small = mov_small
        flow.fill(0)
        dense_used = False
        registered_small = mov_small
        after = before
        affine_reason = "registration-rejected-no-improvement"

    sx = width / small_size[0]
    sy = height / small_size[1]
    full_affine = affine.copy()
    full_affine[0, 2] *= sx
    full_affine[1, 2] *= sy
    affine_full = cv2.warpAffine(
        moving,
        full_affine,
        (width, height),
        flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE,
    )
    full_flow = cv2.resize(flow, (width, height), interpolation=cv2.INTER_LINEAR)
    full_flow[..., 0] *= sx
    full_flow[..., 1] *= sy
    full_x, full_y = np.meshgrid(
        np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32)
    )
    registered = cv2.remap(
        affine_full,
        full_x + full_flow[..., 0],
        full_y + full_flow[..., 1],
        interpolation=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return np.clip(registered, 0, 1).astype(np.float32), {
        "registration_mode": "ecc-affine+dense-optical-flow",
        "ecc_correlation": None if ecc is None else float(ecc),
        "affine_status": affine_reason,
        "affine_matrix_small": affine.tolist(),
        "dense_flow_used": dense_used,
        "dense_flow_displacement_p95_small_px": flow_p95,
        "edge_error_before": before,
        "edge_error_after": after,
        "edge_error_reduction_percent": 0.0 if before == 0 else (1 - after / before) * 100,
    }


def low_frequency_match(moving: np.ndarray, reference: np.ndarray) -> np.ndarray:
    difference = gaussian(reference, 24.0) - gaussian(moving, 24.0)
    return np.clip(moving + np.clip(difference, -0.11, 0.11) * 0.82, 0, 1)


def border_taper(height: int, width: int) -> np.ndarray:
    distance_x = np.minimum(np.arange(width), np.arange(width)[::-1]).astype(np.float32)
    distance_y = np.minimum(np.arange(height), np.arange(height)[::-1]).astype(np.float32)
    distance = np.minimum(distance_y[:, None], distance_x[None, :])
    feather = max(16, min(96, round(min(width, height) * 0.045)))
    phase = np.clip(distance / feather, 0, 1)
    return 0.5 - 0.5 * np.cos(np.pi * phase)


def detail_residual(
    reference: np.ndarray, registered: np.ndarray, strength: float
) -> tuple[np.ndarray, np.ndarray, dict]:
    registered = low_frequency_match(registered, reference)
    ref_gray = cv2.GaussianBlur(luminance(reference), (0, 0), 0.7)
    mov_gray = cv2.GaussianBlur(luminance(registered), (0, 0), 0.7)
    ref_gx, ref_gy, ref_mag = gradients(ref_gray)
    mov_gx, mov_gy, mov_mag = gradients(mov_gray)
    dot = ref_gx * mov_gx + ref_gy * mov_gy
    orientation = np.clip(dot / (ref_mag * mov_mag + 1e-6), 0, 1)

    ref_scale = float(np.percentile(ref_mag, 96)) + 1e-6
    mov_scale = float(np.percentile(mov_mag, 96)) + 1e-6
    ref_edge = np.clip(ref_mag / (ref_scale * 0.72) - 0.10, 0, 1)
    mov_edge = np.clip(mov_mag / (mov_scale * 0.72) - 0.10, 0, 1)
    magnitude_match = np.sqrt(np.minimum(ref_mag / ref_scale, mov_mag / mov_scale) /
                              (np.maximum(ref_mag / ref_scale, mov_mag / mov_scale) + 1e-6))
    low_delta = np.mean(np.abs(gaussian(reference, 5.0) - gaussian(registered, 5.0)), axis=2)
    tone_match = np.exp(-np.square(low_delta / 0.075))
    confidence = ref_edge * mov_edge * np.square(orientation) * magnitude_match * tone_match
    confidence = cv2.GaussianBlur(confidence.astype(np.float32), (0, 0), 0.65)
    confidence = np.power(np.clip(confidence, 0, 1), 0.70)
    confidence *= border_taper(*confidence.shape)

    fine = np.clip(registered - gaussian(registered, 1.0), -0.050, 0.050)
    middle = np.clip(gaussian(registered, 0.8) - gaussian(registered, 2.8), -0.075, 0.075)
    band = np.clip(fine * 0.58 + middle * 0.76, -0.072, 0.072)
    residual = band * confidence[..., None] * strength
    return residual.astype(np.float32), confidence.astype(np.float32), {
        "accepted_detail_coverage_percent": float(np.mean(confidence > 0.08) * 100),
        "accepted_detail_weight_mean": float(np.mean(confidence)),
        "residual_p99_levels": float(np.percentile(np.abs(residual), 99) * 255),
        "flat_region_residual_mean_levels": float(
            np.mean(np.abs(residual[ref_edge < 0.08])) * 255 if np.any(ref_edge < 0.08) else 0
        ),
    }


def base_edge_delta(base: np.ndarray, strength: float) -> np.ndarray:
    gray = cv2.GaussianBlur(luminance(base), (0, 0), 0.65)
    _, _, magnitude = gradients(gray)
    scale = float(np.percentile(magnitude, 96)) + 1e-6
    edge = np.clip(magnitude / (scale * 0.70) - 0.08, 0, 1)
    fine = np.clip(base - gaussian(base, 0.9), -0.024, 0.024)
    middle = np.clip(gaussian(base, 0.75) - gaussian(base, 2.0), -0.040, 0.040)
    return (fine * 0.45 + middle * 0.65) * edge[..., None] * strength


def cosine_left_weight(xs: np.ndarray, start: int, end: int) -> np.ndarray:
    weight = np.ones_like(xs, dtype=np.float32)
    weight[xs >= end] = 0.0
    zone = (xs > start) & (xs < end)
    phase = (xs[zone] - start) / max(1, end - start)
    weight[zone] = 0.5 * (1.0 + np.cos(math.pi * phase))
    return weight


def seam_stats(delta: np.ndarray, split: dict) -> dict:
    mid_x, mid_y = split["mid_x"], split["mid_y"]
    vertical = np.mean(np.abs(delta[:, mid_x] - delta[:, mid_x - 1]), axis=1) * 255
    horizontal = np.mean(np.abs(delta[mid_y] - delta[mid_y - 1]), axis=1) * 255
    return {
        "vertical_residual_seam_mean_levels": float(np.mean(vertical)),
        "vertical_residual_seam_p95_levels": float(np.percentile(vertical, 95)),
        "horizontal_residual_seam_mean_levels": float(np.mean(horizontal)),
        "horizontal_residual_seam_p95_levels": float(np.percentile(horizontal, 95)),
    }


def main() -> int:
    args = parse_args()
    if not 0 <= args.detail_strength <= 1.5 or not 0 <= args.base_sharpen <= 1.0:
        raise SystemExit("Invalid detail strength or base sharpen value")
    manifest_path = args.manifest.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    if not manifest_path.is_file():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"Output exists; choose another path or use --overwrite: {output_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("tile_count") != 4:
        raise SystemExit("Manifest must describe exactly four tiles")
    width, height = manifest["canvas_size"]
    if max(width, height) != 3840:
        raise SystemExit("Manifest canvas is not true 4K")
    base_path = Path(manifest["base_4k"])
    base_image = open_rgb(base_path)
    if base_image.size != (width, height):
        raise SystemExit("Base image size does not match manifest")
    base = np.asarray(base_image, dtype=np.float32) / 255.0

    provided = {name: getattr(args, name).expanduser().resolve() for name in NAMES}
    split = manifest["split"]
    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    left = cosine_left_weight(xs, split["right_start"], split["left_end"])
    right = 1.0 - left
    top = cosine_left_weight(ys, split["bottom_start"], split["top_end"])
    bottom = 1.0 - top
    global_weights = {
        "tl": top[:, None] * left[None, :],
        "tr": top[:, None] * right[None, :],
        "bl": bottom[:, None] * left[None, :],
        "br": bottom[:, None] * right[None, :],
    }

    residual_sum = np.zeros_like(base)
    weight_sum = np.zeros((height, width), dtype=np.float32)
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
                f"Tile {name} aspect ratio differs by {ratio_error:.3f}%; regenerate without reframing"
            )
        if image.size != expected_size:
            image = image.resize(expected_size, Image.Resampling.LANCZOS)
        moving = np.asarray(image, dtype=np.float32) / 255.0
        reference = base[y0:y1, x0:x1]
        fallback = float(np.max(np.abs(moving - reference))) <= (1.0 / 255.0 + 1e-7)
        if fallback:
            registered = reference.copy()
            registration = {
                "registration_mode": "base-tile-fallback",
                "ecc_correlation": 1.0,
                "affine_status": "not-needed-identical-base-tile",
                "affine_matrix_small": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                "dense_flow_used": False,
                "dense_flow_displacement_p95_small_px": 0.0,
                "edge_error_before": 0.0,
                "edge_error_after": 0.0,
                "edge_error_reduction_percent": 0.0,
            }
        else:
            registered, registration = register_candidate(reference, moving, args.registration_edge)
        residual, confidence, detail = detail_residual(reference, registered, args.detail_strength)
        weight = global_weights[name][y0:y1, x0:x1]
        residual_sum[y0:y1, x0:x1] += residual * weight[..., None]
        weight_sum[y0:y1, x0:x1] += weight
        tile_reports[name] = {
            "input": str(provided[name]),
            "source_size": list(source_size),
            "target_size": list(expected_size),
            "source_aspect_ratio_error_percent": ratio_error,
            "candidate_mode": "base-tile-fallback" if fallback else "image-gen-enhanced",
            "box": box,
            **registration,
            **detail,
        }

    if float(weight_sum.min()) < 0.999 or float(weight_sum.max()) > 1.001:
        raise SystemExit("Residual blend weights do not sum to one across the canvas")
    base_delta = base_edge_delta(base, args.base_sharpen)
    total_delta = base_delta + residual_sum
    composite = np.clip(base + total_delta, 0, 1)
    output_u8 = np.round(composite * 255).astype(np.uint8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = Image.fromarray(output_u8)
    save_kwargs: dict = {"compress_level": 6}
    with Image.open(base_path) as opened:
        if opened.info.get("icc_profile"):
            save_kwargs["icc_profile"] = opened.info["icc_profile"]
        if opened.info.get("dpi"):
            save_kwargs["dpi"] = opened.info["dpi"]
    output.save(output_path, format="PNG", **save_kwargs)

    result = {
        "manifest": str(manifest_path),
        "output": str(output_path),
        "output_size": [width, height],
        "output_long_edge": max(width, height),
        "tile_count": 4,
        "registration_mode": "ecc-affine+dense-optical-flow",
        "fusion_mode": "registered-high-frequency-residual",
        "whole_tile_blended": False,
        "base_low_frequency_preserved": True,
        "residual_blend_mode": "complementary-cosine",
        "residual_weight_sum_min": float(weight_sum.min()),
        "residual_weight_sum_max": float(weight_sum.max()),
        "detail_strength": args.detail_strength,
        "base_sharpen": args.base_sharpen,
        **seam_stats(total_delta, split),
        "tiles": tile_reports,
        "cropped": False,
        "padded": False,
        "canvas_extended": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

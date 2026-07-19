# 内置 image_gen 分块高清修复提示模板

每个切片单独调用一次内置 `image_gen`。根据 manifest 填充方括号；四次提示除切片名称、坐标和局部内容外保持一致。

```text
Use case: precise-object-edit
Asset type: one tile of a seamless true-4K restoration
Input images: Image 1 is the only edit target, the [TL/TR/BL/BR] overlapping tile cropped directly from the highest-native-resolution whole-image master. Image 2 is that complete unscaled native master; use it only to preserve global composition, geometry, colors, lighting and continuity. Return only the enhanced version of Image 1.

Tile coordinates: Image 1 corresponds exactly to native master coordinates [native_x0, native_y0, native_x1, native_y1] and maps to final 4K coordinates [x0, y0, x1, y1]. Its native shared overlap edges are [right/left/top/bottom descriptions]. Preserve every boundary feature so it continues naturally into adjacent tiles.

Primary request: Improve only the technical image quality of Image 1 at the highest native resolution available from the built-in image editor. Remove visible noise, dirt, compression blocks, jagged edges, smearing, banding and low-resolution surface artifacts. Restore conservative, physically plausible fine detail without redesigning or reinterpreting anything.

Local subject and materials: [描述当前切片中的主体部件、轮廓、文字/徽标以及真实材质]

Invariants: Keep exactly the same crop, aspect ratio, pixel-space framing, object identity, object count, silhouette, geometry, proportions, design, panel lines, lights, wheels, facial features, text, logos, camera viewpoint, lens perspective, spatial relationships, colors, lighting direction, reflections and shadows. Match Image 2's global color temperature, exposure, contrast and material response. Change only degraded texture and image-quality artifacts.

Overlap continuity: In every shared overlap edge, preserve the exact positions and trajectories of lines, contours, reflections, gradients, shadows and textures. Do not simplify, move, duplicate or terminate a feature near an edge.

Avoid: no redesign, no altered proportions, no changed logo or text, no extra or missing objects, no duplicated parts, no reframing, no cropping, no padding, no canvas extension, no borders, no invented structure, no color cast, no exposure change, no plastic look, no oversmoothing, no oversharpening, no halos, no painterly effect, no watermark.
```

若某块第一次生成发生漂移，第二次仍使用原始切片作为 Image 1，只加强发生漂移的单一约束，不增加新场景描述。第二次仍不合格时，使用母版原切片作为该块的安全回退；禁止强行裁切、拉伸或第三次生成。

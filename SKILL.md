---
name: tool-image-optimize-4k-upscale
description: Upscale and restore opaque still raster images to a clean true-4K PNG by dividing an exact-aspect 4K working image into four overlapping tiles, enhancing each tile independently with the built-in image_gen editor at its highest available native resolution, then applying reference-guided color matching and cosine-feathered seamless stitching. Use for 四块重叠高清放大、分块AI修复、无缝拼接4K、原比例4K输出、去噪去脏污 and high-detail restoration when cropping, padding, canvas extension, API keys, local upscaler models, visible seams, color shifts, structural redesign, and invented objects are forbidden.
---

# 工具_图像优化_4k高清放大

执行“原图取证 → 原比例4K坐标基底 → 2×2重叠切片 → 四次内置 image_gen 修复 → 低频色彩回校 → 余弦羽化拼合 → 4K验证”。使用 ChatGPT/Codex 内置图像能力，不要求 `OPENAI_API_KEY`。

## 强制约束

- 只使用内置 `image_gen` 编辑四个切片；禁止使用 SeedVR2、其他本地超分模型或需要 API Key 的 imagegen CLI。
- 最终 PNG 长边必须恰好为 3840 像素，短边按原图真实宽高比取最近整数。
- 不裁切原始构图、不补边、不扩图、不固定为 16:9。
- 四个切片必须带横向与纵向重叠；默认总重叠宽度为对应整图尺寸的 12%。
- 锁定主体身份、数量、轮廓、比例、设计、文字/徽标、视角、透视、颜色、光影和坐标边界。
- 每个切片只修复低清纹理、噪点、脏污、压缩块、锯齿与涂抹感；不得重新构图或新增内容。
- 拼接必须经过参考色彩回校和互补余弦羽化，禁止硬切、简单覆盖或仅靠肉眼摆放。

## 工作流

1. 完整读取系统 `imagegen` skill。使用其默认内置工具模式；不要切换 CLI，也不要索取 API Key。
2. 查看原图并读取真实宽高、EXIF 方向和透明度。若图像存在真实透明像素，先请用户决定不透明背景；不要自行丢弃透明度。
3. 创建任务目录并生成原比例 4K 基底、四个重叠切片和 manifest：

```bash
python3 scripts/prepare_4k_tiles.py "/absolute/path/input.png" \
  --output-dir "/absolute/path/output/imagegen/job-name"
```

4. 读取脚本 JSON，必须满足：
   - `output_long_edge == 3840`；
   - `tile_count == 4`；
   - `cropped == false`、`padded == false`、`canvas_extended == false`；
   - `overlap_x > 0`、`overlap_y > 0`。
5. 完整读取 [references/tile_prompt.md](references/tile_prompt.md)。依次处理 `tl`、`tr`、`bl`、`br` 四块；每块都执行独立的内置 `image_gen` 调用：
   - Image 1：当前切片，唯一 edit target；
   - Image 2：完整 4K 基底，只作为全局构图、颜色和光影参考；
   - 提示中写明切片名称、manifest 中的坐标和与相邻块共享的重叠边；
   - 要求以当前内置工具可提供的最高原生分辨率返回；不要声称可以传入不存在的尺寸参数。
6. 本地切片使用 `view_image` 查看后再交给内置图像编辑工具。四次生成的最终结果复制到任务目录，稳定命名为：
   - `enhanced_tl.png`
   - `enhanced_tr.png`
   - `enhanced_bl.png`
   - `enhanced_br.png`
7. 每次生成后单独核对：边界内容、主体结构、文字/徽标、颜色、光向和切片比例必须与对应输入一致。某块漂移时，只允许从该块的原始切片重新编辑一次；不要基于漂移结果继续生成。
8. 拼合四块：

```bash
python3 scripts/stitch_4k_tiles.py \
  "/absolute/path/output/imagegen/job-name/manifest.json" \
  --tl "/absolute/path/output/imagegen/job-name/enhanced_tl.png" \
  --tr "/absolute/path/output/imagegen/job-name/enhanced_tr.png" \
  --bl "/absolute/path/output/imagegen/job-name/enhanced_bl.png" \
  --br "/absolute/path/output/imagegen/job-name/enhanced_br.png" \
  --output "/absolute/path/output/imagegen/final-4k.png"
```

9. 拼合脚本必须按以下顺序处理：
   - 将每块无裁切地缩放回 manifest 中的精确坐标尺寸；原始比例误差超过 2% 时拒绝拼接并重做该块；
   - 以对应 4K 基底区域做低频 RGB 色彩/亮度回校，只校准大尺度色调，不抹除新恢复的高频细节；
   - 在横纵重叠区使用成对互补的余弦权重；四块权重和必须为 1；
   - 输出精确原图比例 4K PNG，不再锐化。
10. 读取最终 JSON，必须满足：
    - `output_long_edge == 3840`；
    - `output_size` 等于 manifest 的 `canvas_size`；
    - `tile_count == 4`、`color_matched == true`、`blend_mode == "complementary-cosine"`；
    - `cropped == false`、`padded == false`、`canvas_extended == false`；
    - 每块 `source_aspect_ratio_error_percent <= 2.0`。
11. 以 100% 比例查看最终图，重点检查中央十字交汇区及两条完整接缝。必须没有亮度跳变、色偏、双影、重复纹理、断裂边缘或羽化模糊带。若有问题，先重做引发差异的单块，再拼合；不要模糊整张图掩盖接缝。
12. 报告最终真实像素尺寸、绝对路径、四块均由内置 `image_gen` 单独处理，以及是否重试过切片。

## 切片与拼接原则

- 在最终 4K 坐标系中切片，确保所有块拥有确定的目标尺寸和位置。
- 让重叠区包含足够的共同结构；默认 12%，可在 8%–18% 之间调整。结构复杂或渐变背景使用 14%–18%。
- 始终把完整基底作为每块的全局参考，避免四次编辑产生不同色温、光向或设计解释。
- 不让关键文字、徽标、脸部中心或高对比细边恰好位于中央接缝；若不可避免，增大重叠，不移动原始切割中心。
- 独立生成无法绝对保证语义一致；重叠、全局参考、色彩回校、余弦融合和最终人工核验缺一不可。

## 输出规则

- 最终结果保存为 PNG，默认放入工作区 `output/imagegen/`。
- 不覆盖原图或现有结果；重试使用版本化文件名。
- 中间基底、切片和生成块保留到最终检查完成，之后可由用户决定是否删除。

## 依赖

- AI 修复：内置 `image_gen` 工具，不需要 `OPENAI_API_KEY`。
- 4K基底、切片、色彩回校、余弦拼合和验证：Pillow、NumPy。

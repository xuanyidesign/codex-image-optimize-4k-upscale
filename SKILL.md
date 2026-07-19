---
name: tool-image-optimize-4k-upscale
description: Upscale and restore opaque still raster images to a clean true-4K PNG by first creating one globally consistent highest-native-resolution whole-image master with the built-in image_gen editor using structural parsing and category-specific physical material regeneration, then splitting that native master directly into four overlapping tiles, enhancing each tile independently, geometrically registering every result, and fusing only evidence-gated high-frequency residuals. Use for 最高原生整图重绘、四块重叠高清放大、分块AI修复、几何配准、高频残差融合、无缝4K、原比例4K输出、去噪去脏污 and high-detail restoration when fixed-2K normalization, cropping, padding, canvas extension, API keys, local upscaler models, whole-tile feathering, visible seams, color shifts, structural redesign, and invented objects are forbidden.
---

# 工具_图像优化_4k高清放大

执行“原图取证 → 结构解析与分区物理材质策略 → 一次整图 image_gen 生成最高原生母版 → 直接在原生母版坐标中切2×2重叠块 → 四次内置 image_gen 修复 → 映射到原比例4K坐标 → 仿射与稠密光流配准 → 可信高频残差融合 → 4K验证”。不生成固定2048母版，不要求 `OPENAI_API_KEY`。

## 强制约束

- 只使用内置 `image_gen` 完成一次最高原生整图母版和四个切片增强，共五次编辑；禁止使用 SeedVR2、其他本地超分模型或需要 API Key 的 imagegen CLI。
- 禁止把整图原生输出归一化为固定2048或其他“2K母版”；四个切片必须直接从工具原生返回文件裁出。
- 最终 PNG 长边必须恰好为 3840 像素，短边按原图真实宽高比取最近整数。
- 不裁切原始构图、不补边、不扩图、不固定为 16:9。
- 四个切片必须带横向与纵向重叠；默认总重叠宽度为对应整图尺寸的 12%。
- 锁定主体身份、数量、轮廓、比例、设计、文字/徽标、视角、透视、颜色、光影和坐标边界。
- 每个切片只修复低清纹理、噪点、脏污、压缩块、锯齿与涂抹感；不得重新构图或新增内容。
- 每个生成块必须先与对应原始4K基底区域做几何配准；全局仿射后再做有位移上限的稠密光流对齐。
- 低频构图、轮廓、颜色和光影由最高原生整图母版直接建立的4K配准基底提供；禁止把四个生成块的整块像素直接羽化、覆盖或平均。
- 只允许注入与基底边缘方向、位置和低频明暗一致的高频残差；对不准的结构必须降权或拒绝。
- 互补余弦权重只能用于四块“已配准高频残差”的重叠融合，不能用于整块图像内容。

## 工作流

1. 完整读取系统 `imagegen` skill。使用其默认内置工具模式；不要切换 CLI，也不要索取 API Key。
2. 查看原图并读取真实宽高、EXIF 方向和透明度。若图像存在真实透明像素，先请用户决定不透明背景；不要自行丢弃透明度。
3. 完整读取 [references/master_prompt.md](references/master_prompt.md)。先完成图像类别、主体结构、空间关系、分区真实材质、光影和摄影调性的分析，再把原始完整图作为唯一 edit target 调用一次内置 `image_gen`。保存工具返回的原始文件为 `master_native.png`，不得改成固定2K。先检查：
   - 画面完整、没有裁切、扩图或补边；
   - 主体、徽标、文字、灯组、脸部等关键结构没有漂移；
   - 记录内置工具真实返回尺寸，不虚报或承诺固定分辨率；
   - 与原图宽高比误差不超过 2%。
4. 使用原图提供最终真实比例；脚本直接从 `master_native.png` 的原生像素坐标裁出四个重叠切片，同时建立原比例4K配准基底和坐标映射：

```bash
python3 scripts/prepare_4k_tiles.py "/absolute/path/input.png" \
  --master "/absolute/path/output/imagegen/job-name/master_native.png" \
  --output-dir "/absolute/path/output/imagegen/job-name"
```

5. 读取脚本 JSON，必须满足：
   - `output_long_edge == 3840`；
   - `base_source == "whole-image-image-gen-native-master"`；
   - `fixed_2k_normalization == false`；
   - `master_native_size` 等于工具真实原生输出尺寸；
   - `master_aspect_ratio_error_percent <= 2.0`；
   - `tile_count == 4`；
   - `cropped == false`、`padded == false`、`canvas_extended == false`；
   - `overlap_x > 0`、`overlap_y > 0`。
6. 完整读取 [references/tile_prompt.md](references/tile_prompt.md)。依次处理 `tl`、`tr`、`bl`、`br` 四块；每块都执行独立的内置 `image_gen` 调用：
   - Image 1：当前切片，唯一 edit target；
   - Image 2：完整最高原生母版，只作为全局构图、颜色和光影参考；
   - 提示中写明切片名称、manifest 中的 `native_box`、对应最终 `box` 和与相邻块共享的原生重叠边；
   - 要求以当前内置工具可提供的最高原生分辨率返回；不要声称可以传入不存在的尺寸参数。
7. 本地切片使用 `view_image` 查看后再交给内置图像编辑工具。四次生成的最终结果复制到任务目录，稳定命名为：
   - `enhanced_tl.png`
   - `enhanced_tr.png`
   - `enhanced_bl.png`
   - `enhanced_br.png`
8. 每次生成后单独核对：边界内容、主体结构、文字/徽标、颜色、光向和切片比例必须与对应输入一致。某块漂移时，只允许从该块的原始切片重新编辑一次；不要基于漂移结果继续生成。重试仍不合格时，把该块的母版原切片复制为对应 `enhanced_*.png` 安全回退，禁止裁切、拉伸或继续消耗生成次数。
9. 配准并融合四块：

```bash
python3 scripts/stitch_4k_tiles.py \
  "/absolute/path/output/imagegen/job-name/manifest.json" \
  --tl "/absolute/path/output/imagegen/job-name/enhanced_tl.png" \
  --tr "/absolute/path/output/imagegen/job-name/enhanced_tr.png" \
  --bl "/absolute/path/output/imagegen/job-name/enhanced_bl.png" \
  --br "/absolute/path/output/imagegen/job-name/enhanced_br.png" \
  --output "/absolute/path/output/imagegen/final-4k.png"
```

10. 融合脚本必须按以下顺序处理：
   - 将每块无裁切地缩放回 manifest 中的精确坐标尺寸；原始比例误差超过 2% 时拒绝拼接并重做该块；
   - 以对应基底区域的边缘图执行 ECC 仿射配准，再执行有最大位移约束的稠密光流配准；只有边缘误差确实下降时才接受变换；
   - 以基底做低频 RGB 色彩/亮度回校，但最终绝不输出生成块的低频像素；
   - 从配准块提取细节频带，以基底边缘位置、梯度方向、边缘强度、低频明暗一致性生成置信度，只保留有原图证据的高频残差；
   - 把四块残差按成对互补余弦权重融合后加回唯一的4K基底；四块残差权重和必须为 1，整块图像不得参与羽化；
   - 对基底只做受边缘约束的轻微锐化，输出精确原图比例 4K PNG。
11. 读取最终 JSON，必须满足：
    - `output_long_edge == 3840`；
    - `output_size` 等于 manifest 的 `canvas_size`；
    - `tile_count == 4`、`registration_mode == "ecc-affine+dense-optical-flow"`；
    - `fusion_mode == "registered-high-frequency-residual"`、`residual_blend_mode == "complementary-cosine"`；
    - `whole_tile_blended == false`、`base_low_frequency_preserved == true`；
    - `cropped == false`、`padded == false`、`canvas_extended == false`；
    - 每块 `source_aspect_ratio_error_percent <= 2.0`。
12. 以 100% 比例查看最终图，重点检查中央十字交汇区及两条完整接缝。必须没有亮度跳变、色偏、双影、重复纹理、断裂边缘或羽化模糊带。检查每块 `edge_error_after <= edge_error_before`，并查看残差接缝的 mean/p95 指标。若某块配准失败或细节覆盖率异常，先重做该块；不要模糊整张图掩盖接缝。
13. 报告最终真实像素尺寸、绝对路径、整图母版的真实原生尺寸、`fixed_2k_normalization == false`、四块均由内置 `image_gen` 处理，以及是否重试过母版或切片。

## 切片与拼接原则

- 直接在最高原生母版像素坐标中切片，并在 manifest 中保存 `native_box`；同时保存它对应的最终4K `box`，用于确定目标尺寸和位置。
- 让重叠区包含足够的共同结构；默认 12%，可在 8%–18% 之间调整。结构复杂或渐变背景使用 14%–18%。
- 始终把完整基底作为每块的全局参考，避免四次编辑产生不同色温、光向或设计解释。
- 最高原生整图母版直接建立的4K基底是四块阶段唯一的低频与几何真值；四个生成块只是候选细节源。几何配准和置信度门控不能被“看起来大致对齐”替代。
- 不让关键文字、徽标、脸部中心或高对比细边恰好位于中央接缝；若不可避免，增大重叠，不移动原始切割中心。
- 独立生成无法绝对保证语义一致；重叠、全局参考、几何配准、可信高频残差、残差余弦融合和最终人工核验缺一不可。

## 输出规则

- 最终结果保存为 PNG，默认放入工作区 `output/imagegen/`。
- 不覆盖原图或现有结果；重试使用版本化文件名。
- 中间基底、切片和生成块保留到最终检查完成，之后可由用户决定是否删除。

## 依赖

- AI 修复：内置 `image_gen` 工具，不需要 `OPENAI_API_KEY`。
- 4K基底、切片、几何配准、高频残差融合和验证：Pillow、NumPy、OpenCV。

# Codex Image Optimize — True 4K Upscale

一个面向 Codex 的图像优化 Skill。它将原图映射到保持原始长宽比的 4K 坐标系，切成四块带重叠区域的图像，分别调用内置 `image_gen` 高清修复，再通过参考色彩回校和余弦羽化拼合为无明显接缝的 PNG。

当前版本：`1.1.0`

## 核心能力

- 最终长边精确为 3840 像素，短边按原图比例计算
- 不裁切、不补边、不扩展画布，不强制转换成 16:9
- 默认切分为 2×2 四块，横纵重叠区域为整图对应尺寸的 12%
- 四块分别调用 Codex 内置 `image_gen`，无需 `OPENAI_API_KEY`
- 清理噪点、脏污、压缩块、锯齿、涂抹感与条带
- 锁定主体、构图、轮廓、比例、徽标、文字、颜色、光影和透视
- 以完整 4K 基底校正各块低频色彩和亮度
- 使用互补余弦权重融合重叠区域，并输出机器可读的验证结果

## 工作原理

```text
读取原图真实尺寸
  → 创建原比例 4K 坐标基底
  → 切分四个重叠图块
  → 四次内置 image_gen 独立修复
  → 对齐基底色彩与亮度
  → 互补余弦羽化拼合
  → 尺寸、比例和接缝验证
```

## 安装

让 Codex 安装：

```text
请安装这个 Skill：
https://github.com/xuanyidesign/codex-image-optimize-4k-upscale
```

手动安装：

```bash
git clone https://github.com/xuanyidesign/codex-image-optimize-4k-upscale.git \
  "$HOME/.codex/skills/tool-image-optimize-4k-upscale"

python3 -m pip install -r \
  "$HOME/.codex/skills/tool-image-optimize-4k-upscale/requirements.txt"
```

如果 Codex 没有立即发现 Skill，请重新启动 Codex。

## 使用

上传一张不透明的静态图片，然后告诉 Codex：

```text
使用 $tool-image-optimize-4k-upscale 优化这张图片。
保持原始长宽比例与完整构图，分成四块调用内置 image_gen 高清修复，
去除噪点和脏污并无缝拼合为 4K PNG。
```

准备 4K 基底和四个重叠切片：

```bash
python3 scripts/prepare_4k_tiles.py "/absolute/path/input.png" \
  --output-dir "/absolute/path/output/imagegen/job-name"
```

四个切片经内置 `image_gen` 编辑并分别保存为 `enhanced_tl.png`、`enhanced_tr.png`、`enhanced_bl.png`、`enhanced_br.png` 后，执行：

```bash
python3 scripts/stitch_4k_tiles.py \
  "/absolute/path/output/imagegen/job-name/manifest.json" \
  --tl "/absolute/path/output/imagegen/job-name/enhanced_tl.png" \
  --tr "/absolute/path/output/imagegen/job-name/enhanced_tr.png" \
  --bl "/absolute/path/output/imagegen/job-name/enhanced_bl.png" \
  --br "/absolute/path/output/imagegen/job-name/enhanced_br.png" \
  --output "/absolute/path/output/imagegen/final-4k.png"
```

## “真实 4K”的定义

本 Skill 将 4K 定义为输出图像长边精确为 `3840` 像素。竖图、方图和非 16:9 横图均保持原始比例。

拼合脚本会验证：

- `output_long_edge == 3840`
- `tile_count == 4`
- `color_matched == true`
- `blend_mode == "complementary-cosine"`
- `cropped == false`
- `padded == false`
- `canvas_extended == false`
- 每个生成切片的比例误差不超过 2%

## 注意事项

- 内置图像生成属于受约束的细节重建，不等同于真实光学原生 4K。
- 复杂文字、徽标、人物身份和高对比细边仍需最终人工复核。
- 输入包含真实透明像素时，Skill 会要求先确定不透明背景。
- 默认不会覆盖原图或现有结果。

## 目录结构

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/tile_prompt.md
├── scripts/prepare_4k_tiles.py
├── scripts/stitch_4k_tiles.py
├── requirements.txt
└── README.md
```

## License

[MIT](LICENSE)

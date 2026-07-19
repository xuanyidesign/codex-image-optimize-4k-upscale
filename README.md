# Codex Image Optimize — True 4K Upscale

一个面向 Codex 的图像优化 Skill。它先用内置 `image_gen` 生成全局一致的最高原生分辨率整图母版，再直接从母版切出四块重叠图像分别增强，最后通过几何配准与可信高频残差融合生成无明显接缝的原比例 4K PNG。

当前版本：`1.2.0`

> [!WARNING]
> `v1.1.0` 存在已知缺陷：整块余弦羽化会造成细节变软，且缺少几何配准，可能产生模糊、重影或错误拼合。请停止使用并升级到 `v1.2.0`。

## 核心能力

- 最终长边精确为 3840 像素，短边按原图比例计算
- 不裁切、不补边、不扩展画布，不强制转换成 16:9
- 先按结构解析与分区真实材质策略生成最高原生整图母版，不归一化为固定 2K
- 默认切分为 2×2 四块，横纵重叠区域为整图对应尺寸的 12%
- 四块分别调用 Codex 内置 `image_gen`，无需 `OPENAI_API_KEY`
- 清理噪点、脏污、压缩块、锯齿、涂抹感与条带
- 锁定主体、构图、轮廓、比例、徽标、文字、颜色、光影和透视
- 使用 ECC 仿射配准与受限稠密光流对齐各块
- 保留整图母版的低频几何、颜色与光影，只注入有原图证据的高频残差
- 互补余弦权重仅融合已配准的高频残差，不直接羽化整块图像
- 输出机器可读的配准、融合、接缝与尺寸验证结果

## 工作原理

```text
读取原图真实尺寸
  → 结构解析与分区真实材质策略
  → 一次 image_gen 生成最高原生整图母版
  → 直接从原生母版切分四个重叠图块
  → 四次内置 image_gen 独立修复
  → 映射到原比例 4K 坐标
  → ECC 仿射与稠密光流几何配准
  → 可信高频残差融合
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
保持原始长宽比例与完整构图，先生成最高原生整图母版，再分成四块调用
内置 image_gen 高清修复，经几何配准与高频残差融合输出 4K PNG。
```

先把内置 `image_gen` 返回的最高原生整图母版保存为 `master_native.png`，再准备 4K 配准基底和四个重叠切片：

```bash
python3 scripts/prepare_4k_tiles.py "/absolute/path/input.png" \
  --master "/absolute/path/output/imagegen/job-name/master_native.png" \
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
- `fixed_2k_normalization == false`
- `registration_mode == "ecc-affine+dense-optical-flow"`
- `fusion_mode == "registered-high-frequency-residual"`
- `whole_tile_blended == false`
- `base_low_frequency_preserved == true`
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
├── references/master_prompt.md
├── references/tile_prompt.md
├── scripts/prepare_4k_tiles.py
├── scripts/stitch_4k_tiles.py
├── requirements.txt
└── README.md
```

## License

[MIT](LICENSE)

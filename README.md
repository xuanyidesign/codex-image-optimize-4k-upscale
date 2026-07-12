# Codex Image Optimize — True 4K Upscale

一个面向 Codex 的图像优化 Skill：在保持原始长宽比、完整构图、主体身份、几何、透视、颜色与光影的前提下，完成去噪、材质重绘，并把最终图像确定性归一化为长边 3840 像素。

## 核心能力

- 原始像素尺寸取证，不依赖预览图估算
- 按真实原始比例生成 4K 工作图
- AI 去除噪点、灰尘、脏污、划痕、压缩痕迹和塑料感
- 锁定主体身份、数量、轮廓、视角、透视、构图、颜色与光影
- 不裁切、不补边、不扩图，不创建无关的 16:9 画布
- 最终长边精确为 3840px，并输出机器可读的 JSON 验证结果
- 支持 PNG、JPEG、WebP、BMP 和 TIFF

## 工作原理

```text
原图尺寸取证
  → 初步 4K 等比放大
  → 结构与材质解析
  → AI 去噪和材质再生
  → 原比例 4K 归一化
  → 元数据与视觉双重验证
```

其中，尺寸归一化由确定性 Python 脚本完成；高保真重绘由 Codex 的内置图像编辑能力完成。

## 安装

### 方法一：让 Codex 安装

把本仓库地址交给 Codex，并发送：

```text
请安装这个 Skill，并检查 Pillow 依赖：
https://github.com/xuanyidesign/codex-image-optimize-4k-upscale
```

### 方法二：手动安装

```bash
git clone https://github.com/xuanyidesign/codex-image-optimize-4k-upscale.git \
  "$HOME/.agents/skills/tool-image-optimize-4k-upscale"

python3 -m pip install -r \
  "$HOME/.agents/skills/tool-image-optimize-4k-upscale/requirements.txt"
```

如果 Codex 没有立即发现新 Skill，请重新启动 Codex。

## 使用

上传一张图片，然后告诉 Codex：

```text
使用 $tool-image-optimize-4k-upscale 优化这张图片。
保持主体、构图、视角、颜色和光影不变，去除噪点、脏污与压缩痕迹，
重绘真实材质，并按原始长宽比例输出真实 4K 图片。
```

也可以直接运行确定性尺寸脚本：

```bash
python3 scripts/upscale_4k.py "/absolute/path/input.png"
```

最终重绘图归一化：

```bash
python3 scripts/upscale_4k.py "/path/redrawn.png" \
  --aspect-reference "/path/original.png" \
  --force-exact \
  --output "/path/final_4k.png"
```

## “真实 4K”的定义

本 Skill 将 4K 定义为输出图像长边精确为 `3840` 像素。竖图、方图和非 16:9 横图均保持原始比例，不会被强行塞进 `3840×2160` 画布。

脚本会验证：

- `output_long_edge == 3840`
- `cropped == false`
- `padded == false`
- `canvas_extended == false`
- `aspect_ratio_error_percent <= 0.05`

## 注意事项

- AI 重绘可能受模型能力和原图质量影响，复杂文字、五官和重复结构需要人工复核。
- 默认不会覆盖原文件。
- 输入长边已经超过 3840px 时，初步处理默认保留原分辨率；最终归一化阶段使用 `--force-exact`。
- 本项目不会上传你的图片；图片处理发生在你使用的 Codex 环境和相应图像工具中。

## 目录结构

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/redraw_prompt.md
├── scripts/upscale_4k.py
├── requirements.txt
└── README.md
```

## License

[MIT](LICENSE)

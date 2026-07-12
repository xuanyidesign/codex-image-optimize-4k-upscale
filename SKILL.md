---
name: tool-image-optimize-4k-upscale
description: Upscale and AI-redraw a raster image into a clean true-4K result while preserving the original aspect ratio, complete composition, subject identity, geometry, perspective, colors, and lighting. Use when the user asks for 4K高清放大、图像优化至4K、原比例4K输出、去噪重绘、清除脏污划痕、修复涂抹感或塑料感, especially when cropping, padding, canvas extension, and generative reframing are forbidden. Supports PNG, JPEG, WebP, BMP, and TIFF images.
---

# 工具_图像优化_4k高清放大

执行“原图尺寸取证 → 初步4K等比放大 → 结构与材质解析 → AI去噪重绘 → 原比例4K归一化 → 双重验证”。清除噪点、灰尘、脏污、划痕、压缩痕迹和涂抹/塑料感，同时锁定主体、构图、视角、透视、颜色与光影。

## 工作流

1. 读取输入文件的真实像素宽高并记录为比例基准。不要从预览图估计。
2. 运行 `scripts/upscale_4k.py` 生成初步4K工作图；长边设为 3840，短边按真实原始比例四舍五入。
3. 查看初步4K工作图，解析图像类别、主体骨架/轮廓/姿态/特殊结构、前后景透视关系、环境和光影。忽略现有低质量纹理，不把噪点和污渍当作设计细节。
4. 完整读取 [references/redraw_prompt.md](references/redraw_prompt.md)，按模板生成中文重绘提示词。调用内置图像编辑工具前，完整读取系统 `imagegen` skill 并遵循其编辑、输入角色和非破坏性保存规则。
5. 将初步4K工作图标为唯一“编辑目标”；将用户提供的文字截图仅标为“指令参考”，不得把截图内容合成到结果中。执行一次高保真去噪和材质再生重绘。
6. 检查重绘结果：主体结构、数量、身份、轮廓、视角、透视、裁切边界、颜色和光影必须与输入一致；背景必须 clean、pure smooth、completely noise-free。若出现结构漂移，仅针对漂移项重试一次。
7. 无需向用户发送中间说明，立即将重绘结果归一化为原始比例4K：

```bash
python3 scripts/upscale_4k.py "/path/redrawn.png" \
  --aspect-reference "/path/original.png" \
  --force-exact \
  --output "/path/final_4k.png"
```

8. 读取脚本 JSON 并核对：
   - `output_long_edge` 为 `3840`；
   - `cropped`、`padded`、`canvas_extended` 均为 `false`；
   - `aspect_ratio_error_percent` 不超过 `0.05`；
   - `source_to_reference_ratio_difference_percent` 不超过 `2.0`。超过时禁止强行拉伸，重新生成更匹配原比例的重绘图。
9. 查看最终文件，确认主体完整、无新噪点/脏污、没有过度磨皮、过度锐化、光晕、重复结构或AI伪影。
10. 报告真实输出像素和绝对路径；不要用“4K级”代替真实4K。

## 初步放大命令

```bash
python3 scripts/upscale_4k.py "/absolute/path/input.png"
```

只有用户明确要求替换现有文件时才使用 `--overwrite`。输入长边已超过 3840 时默认保留，不主动降采样；最终归一化阶段使用 `--force-exact`。

## 强制约束

- 将“4K”定义为长边 3840 像素，适用于横图、竖图和方图。
- 不创建 3840×2160 画布，除非原图本身就是 16:9。
- 不裁切、不补边、不扩图、不加模糊边栏、不增减对象、不改变构图。
- 重绘只替换劣质表面纹理和伪影；锁定真实结构、边缘、姿态、光影与透视。
- 背景必须平滑、干净、彻底无噪点；主体材质必须符合图像类别和物理肌理。
- 不覆盖原文件，除非用户明确授权。
- 最终输出必须再次经过确定性尺寸归一化与元数据验证。

## 依赖

确定性脚本需要 Pillow；AI重绘使用内置图像编辑工具。

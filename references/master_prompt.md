# 最高原生整图重绘提示模板

在拆分四块之前，以完整原图为唯一 edit target 调用一次内置 `image_gen`。不得指定或承诺固定2048尺寸；要求工具返回当前可用的最高原生分辨率。

## 生成提示前的强制分析

彻底忽略输入图中的低清、噪点、脏污、涂抹感、塑料感和压缩损伤，只解析画面本应具有的完整物理状态：

1. 识别图像类别：人物肖像、产品静物、自然风景或建筑/室内空间。
2. 提取主体骨架、姿态、形状、轮廓、比例、特殊结构和关键标识。
3. 提取背景元素、前后景透视、环境和空间关系。
4. 为不同区域分配真实物理材质：
   - 背景/环境：必须干净、平滑、纯净、彻底无噪点，不继承原图脏污。
   - 人物：自然弹性皮肤、细微毛孔、真实毛发纹理。
   - 产品：无瑕疵金属拉丝或阳极氧化、细腻哑光塑料、高光泽透明玻璃等匹配材质。
   - 场景：清晰叶片脉络、粗糙真实混凝土或其他符合对象的材质。
5. 明确光影、氛围、相机视角和摄影调性；不得因修复而改变这些关系。

## 整图 image_gen 提示模板

按以下模块填充后合并为一次完整编辑提示，不得遗漏：

```text
Use case: precise-object-edit
Asset type: highest-native-resolution whole-image restoration master for later four-tile 4K enhancement
Input images: Image 1 is the only edit target and the complete source image. Return only its restored full-frame version at the highest native resolution currently available.

Image category: [人物肖像 / 产品静物 / 自然风景 / 建筑或室内空间]
Core subject: [完整描述主体、骨架/形状、姿态、轮廓、比例、特殊结构、文字、徽标和关键标识]
Extreme physical texture: [按区域描述真实材料机理；彻底移除原图低清涂抹、噪点、脏污和塑料感]
Environment and background: [背景元素、前后景、透视和环境关系]；background must be clean, pure, smooth and completely noise-free, with no inherited dirt or blotches.
Lighting and atmosphere: [原图光向、明暗对比、边缘过渡、反射和氛围]
Camera and tonality: [原图视角、镜头感、景别、景深、写实或电影级调性]

Primary request: Reconstruct the exact same full image as a clean, high-fidelity global image-to-image master. Remove noise, dirt, fingerprints, scratches, compression blocks, jagged edges, banding, smearing and damaged synthetic texture. Restore conservative, physically plausible fine detail without adding or removing content.

Local regeneration rule for people: Ignore the poor painted texture of skin and hair in the reference. Regenerate clean, realistic physical microstructure while keeping identity, facial geometry, expression, pose, lighting and perspective seamlessly identical.

Product refinement rule: Precisely restore the authentic product colors and material response. Remove fingerprints, dust, scratches, dirt and defects. Keep surfaces new and clean, illumination even and soft, highlights naturally transparent, shadows orderly and three-dimensional. Do not change product design.

Invariants: Preserve exactly the original full-frame composition, aspect ratio, object identity and count, silhouette, geometry, proportions, design, text, logos, viewpoint, lens perspective, spatial relationships, colors, lighting direction, reflections, shadows and normalized coordinates. Change only technical image quality and damaged material texture.

Avoid: no redesign, no altered geometry, no reframing, no crop, no padding, no canvas extension, no extra or missing content, no changed text or logo, no invented structure, no color cast, no dirty regenerated background, no plastic look, no painterly effect, no oversmoothing, no oversharpening, no halos, no watermark.
```

删除与图像类别无关的规则：有人物才保留人物局部重生段，产品作为主体时必须保留产品精修段。生成后校验完整画面、主体结构、文字/徽标、颜色、光影和宽高比；误差超过2%或关键结构漂移时，只能从原始完整图重试一次。

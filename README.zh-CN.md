# GothicNameplate3D

[English](README.md) | **简体中文**

给定两行文字，生成字母从底座沿圆弧升起的立体名牌。左侧为文字，右侧为圆形展示台；展示台与名牌处于相同的前后区域。默认总长 **150 mm**，文字末端平面与水平底座夹角 **70°**。

![Bandosa 字体的 PUT YOUR / NAME HERE 名牌](docs/images/preview.png)

导出经过检查的 STL、可编辑 Blender 场景、GLB 和预览图。示例使用 **Bandosa Regular**；首次提供具有适用授权的字体文件后，即可重复使用本地字形缓存。

## 快速开始

需要 **Python 3.10+** 和 **Blender**。建模及导出已在 macOS、Blender **5.2.1** 验证；其他 Blender 版本和操作系统尚未完成完整建模验证。运行生成器无需安装 pip 包，Blender 自带所需的 NumPy。

```bash
git clone git@github.com:CyclopsRay/GothicNameplate3D.git
cd GothicNameplate3D

# 首次配置字体；已有相同版本的缓存时会直接复用
python3 generate.py setup-font /path/to/bandosa.regular.ttf

# 之后只需要两行文字
python3 generate.py "PUT YOUR" "NAME HERE"
```

`setup-font` 将字体复制到本地 `assets/fonts/`，预处理该字体支持的可打印字形，并保存默认选择。Bandosa 的参考版本包含 90 个可打印字符。字体、字形缓存和本机配置均被 Git 忽略；换名字不会重复转换已经缓存的字形。

**字体需自行提供。** Bandosa 发布页标注个人使用；开源代码的 GPL-3.0 许可不包含字体授权。本仓库不分发 TTF/OTF 或派生的整套字形缓存。请从 [字体发布页](https://www.1001fonts.com/bandosa-font.html) 或 [Blankids Studio](https://blankidsfonts.com/product/bandosa-a-handmade-blackletter-font/) 获取适用授权的文件。也支持其他独立 TTF/OTF。详见 [字体说明](assets/fonts/README.md)。

Blender 按 `--blender`、`BLENDER_BIN`、系统 PATH、macOS 标准安装路径的顺序查找。不能自动找到时，在配置和生成命令上添加 `--blender /path/to/blender`。Windows 可使用 `python` 代替 `python3`。

## 调整模型

```bash
python3 generate.py "MEI'S" "GARDEN" --length 180 --angle 65 --output outputs/mei-garden
python3 generate.py "ALICE" "WONDERLAND" --fit preserve --views beauty,front,side,top
python3 generate.py "YOUR" "NAME" --font /path/to/custom.ttf --no-render
```

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| 两个位置参数 | 必填 | 上排文字、下排文字；保留大小写 |
| `--length` | `150` | 总长度，单位 mm；其他尺寸同比例缩放 |
| `--angle` | `70` | 末端文字平面相对底座的角度，范围 45–85° |
| `--fit` | `stretch` | 按模板铺满；`preserve` 保留字体比例 |
| `--font` | 本机默认字体 | 本次使用的 TTF/OTF，不更改默认字体 |
| `--output` | `outputs/<timestamp>` | 新建或空目录；拒绝覆盖已有结果 |
| `--views` | `beauty,side,top` | 可另选 `front`、`back` |
| `--no-render` | 关闭 | 只生成和检查模型，跳过预览渲染 |

150 mm 模型占地约 150 × 65 mm，展示台内部直径 52 mm，两行 70° 模型约高 56 mm。每个字母以及标点的实心部分都有独立圆弧延伸至底座，然后合并为一个实体。长度改变时，展示台、边缘和文字一并缩放。

Bandosa 不含中文、重音字母或 emoji。缺失字符会明确报错；缺失的弯引号可以转换为字体已有的直引号，并记录在报告中。当前排字不支持复杂文字塑形、连字或双向文本。参数、单行模式及 JSON 输入见 [docs/parameters.md](docs/parameters.md)。

对于应用集成，直接用 `subprocess.run([sys.executable, "generate.py", top, bottom], check=True)` 传入参数列表。文字含命令行选项前缀时，在两个位置参数前加 `--`；需要任意文字数据时也可使用 [JSON 示例](examples/job.json)。不要将未经转义的文字拼进 shell 命令。

## 输出与检查

每次成功生成会输出：

- `nameplate.stl`：以毫米为单位的打印网格。
- `nameplate.blend`：可编辑构造、文字源和摄影场景，包含使用的字体。
- `nameplate.glb`：以米为单位的浏览器/3D 查看器模型。
- `renders/*.png`：选择的预览视角。
- `report.json`、`stl_check.json`：尺寸、角度、缓存命中及网格检查。
- `request.json`、`build.log`：本次参数和运行日志。

成功以 `report.json` 和 `stl_check.json` 的 **`PASS`** 为准。STL 导出后会重新读取，检查单一连通实体、闭合边、非退化三角形、正体积、底部 Z=0、请求长度及末端文字角度。GLB 另检查毫米到米的缩放。切片与实物打印尚未验证。

## 字体缓存与开发

缓存按字体 SHA-256、Blender 主次版本、清理流程版本和曲线分辨率区分。相同条件下已缓存字形应显示 `converted_glyphs: 0`。生成仍需进行圆弧建模、布尔合并、网格验证和可选渲染；缓存只省去重复的字体转换和清理。

大型字体可以只预处理需要的字符：

```bash
python3 generate.py setup-font /path/to/custom.ttf --chars "ALICEBOB0123456789"
```

后续生成会增量加入缺失字形。维护文档记录了本次遇到的具体问题和修复：

- [字体预处理](docs/font-preprocessing.md)：Blender 字距校准、无面顶点、点接触轮廓。
- [故障与修复](docs/troubleshooting.md)：布尔失败、重复反向三角形、缩放精度、导出单位。
- [验证记录与测试](docs/validation.md)：测试边界、运行方法，以及正面、侧面和俯视预览图。

轻量测试在 CI 上运行；完整 Blender 验证需要本机字体：

```bash
python3 -m pip install numpy  # 仅独立网格检查测试需要；生成器无需此安装
python3 -m unittest discover -s tests -v
python3 generate.py "PUT YOUR" "NAME HERE" --no-render
```

代码采用 [GNU GPL v3](LICENSE)。第三方字体及其派生资产遵循各自许可，见 [THIRD_PARTY.md](THIRD_PARTY.md)。

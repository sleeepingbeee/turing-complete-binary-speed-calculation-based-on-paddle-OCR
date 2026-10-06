# OCR 自动答题脚本（十进制 → 二进制）

自动完成"二进制转换"类小游戏：截取游戏画面 → OCR 识别题目「二进制下，N 如何表示？」→
把 N 换算成 8 位二进制 → 按位点击对应的 8 个答案位置 → 点击过关。

全程在内存中完成，不需要保存截图文件。

---

## 目录结构

| 文件 | 职责 |
| --- | --- |
| `main.py` | 主流程：屏幕捕获、开始检测、逐轮答题与点击 |
| `OCR.py` | 全部 OCR 相关内容：引擎构建、图像预处理、识别封装 |
| `utils.py` | 纯工具函数：进制转换、题目数字解析 |
| `config.py` | 配置：推理设备、轮数、截图区域、点击坐标 |

---

## 环境要求

### 系统与硬件

- Windows（使用了 `mss` 抓屏和 `pyautogui` 模拟点击）
- Python 3.11（实测 3.11.9）
- **NVIDIA 显卡 + CUDA**（本项目当前配置为 GPU 推理；无显卡时可改用 CPU，见下文）
  - 实测显卡：NVIDIA GeForce RTX 5080 Laptop GPU（16 GB），驱动 610.88

### 依赖版本（本项目实测通过的组合）

| 包 | 版本 | 说明 |
| --- | --- | --- |
| `paddlepaddle-gpu` | 3.3.1 | GPU 版。**纯 CPU 环境请改装 `paddlepaddle`** |
| `paddleocr` | 3.7.0 | OCR 主库 |
| `paddlex` | 3.7.2 | paddleocr 的依赖，随其自动安装 |
| `opencv-python` | 5.0.0 | 图像处理 |
| `numpy` | 2.3.5 | 数组运算 |
| `mss` | 10.2.0 | 屏幕捕获 |
| `pyautogui` | 0.9.54 | 模拟鼠标点击 |
| `Pillow` | 12.3.0 | 图像处理 |

> ⚠️ `paddlepaddle` 与 `paddlepaddle-gpu` **不能同时安装**，两者只能留一个。

---

## 安装

```bash
# GPU 环境（当前配置）
pip install paddlepaddle-gpu paddleocr opencv-python numpy mss pyautogui Pillow

# 纯 CPU 环境（同时要把 config.py 里的 DEVICE 改成 "cpu"）
pip install paddlepaddle paddleocr opencv-python numpy mss pyautogui Pillow
```

---

## 运行

```bash
python main.py
```

运行后请**不要移动鼠标或切换窗口**，脚本会自行抓屏并点击。

---

## 配置说明（`config.py`）

| 配置项 | 当前值 | 说明 |
| --- | --- | --- |
| `DEVICE` | `"gpu:0"` | 推理设备。`"gpu:0"` 用第一块显卡，`"cpu"` 用处理器 |
| `ROUNDS` | `63` | 自动进行的轮数 |
| `AREA1` | `top 595, left 615, 55×45` | **开始按钮**所在区域 |
| `AREA2` | `top 600, left 0, 1280×50` | **题目文字**所在横条区域 |
| `POSITIONS` | 8 个坐标 | 8 个答案位置，自左向右依次对应二进制的高位到低位 |
| `IF_TEST` | `True` | 保留字段，当前未被使用 |

坐标基于 **1280 宽的屏幕**标定。换分辨率需要重新测量 `AREA1`、`AREA2`、`POSITIONS`，
以及 `main.py` 中写死的两处点击点 `(640, 620)`（开始键）和 `(640, 1470)`（过关键）。

---

## 工作流程

```
启动
 │
 ├─ build_ocr(DEVICE, False)          加载 PaddleOCR 引擎
 │
 ├─ 【阶段一】循环截取 AREA1
 │     └─ OCR 识别 → 文本含「开始」？
 │           ├─ 是 → 点击 (640,620)，进入阶段二
 │           └─ 否 → 等 1 秒重试
 │
 └─ 【阶段二】循环 ROUNDS 次
       ├─ 截取 AREA2 → OCR 得到题目文本
       ├─ extract_num() 取出十进制数字 N
       │     └─ 解析失败 → 点击 (640,1470) 跳下一轮
       ├─ converter() 把 N 转成 8 位二进制字符串
       ├─ 遍历 8 位，为 "1" 的位置点击 POSITIONS[j]
       └─ 点击 (640,1470) 过关
```

---

## 关键实现细节（踩过的坑）

这一节记录了开发和调试中确认过的真实问题，改动前建议先读一下。

### 1. 识别前必须给图像补白边（`OCR.OCR_MARGIN = 80`）

这是最容易被忽略、但影响最大的一个点。

实测本机 `PP-OCRv6_medium` 模型**在 CPU 和 GPU 上都有同一现象**：
当文字紧贴图像边缘时，识别结果会**稳定丢掉开头 1~4 个字符**。

| 原始文本 | 实际识别结果（不补白） |
| --- | --- |
| `12345` | `2345` |
| `二进制下，5如何表示？` | `表示` |
| `开始` | *（空，什么都没识别到）* |

后果是：开始键永远检测不到（死循环）、题目数字解析失败。

**原因不是模型坏了，也不是分辨率不够**，已逐项排除：

- ❌ 渲染问题 — 导出图片肉眼检查完全清晰，墨迹边界正常
- ❌ 分辨率问题 — 放大 2/3/4 倍无效
- ❌ 方向分类问题 — 关闭 `use_textline_orientation` 无改善
- ✅ **文字贴边问题** — 四周补白后**逐字完全正确**

所以 `ocr_text()` 在识别前会调用 `pad_white()` 补上 `OCR_MARGIN = 80` 像素的纯白边：

| 题目在条内起始 x | 不补白 | 补白 80px |
| --- | --- | --- |
| 0 | `表示` | `二进制下，5如何表示？` ✅ |
| 60 | `前下如回表示？` | `二进制下，5如何表示？` ✅ |
| 200 | `一送制下，5如何表示？` | `二进制下，5如何表示？` ✅ |
| 400 | `一进制下、5郊何表示？` | `二进制下，5如何表示？` ✅ |

> 注意：**换成 GPU 并不会修好这个问题**，GPU 上实测同样丢字。`OCR_MARGIN` 必须保留。

### 2. PaddleOCR 3.x 的返回值必须用字符串键取值

`ocr.predict()` 返回的是 `list[OCRResult]`，而 `OCRResult` 继承自 `dict`
（`paddlex.inference.common.result.BaseResult(dict, ...)`）。

```python
# ❌ 错误：KeyError: 1 / IndexError
text = result[0][1][0]
confidence = result[0][1][1]

# ✅ 正确
res = ocr.predict(frame_bgr)[0]     # 单张图 → 列表只有 1 项
res["rec_texts"]                    # list[str]
res["rec_scores"]                   # list[float]
```

`OCR.ocr_text()` 已经封装好了这一层，并且对空结果做了保护。

### 3. CPU 推理必须关闭 oneDNN（MKLDNN）

`paddlepaddle 3.3.1 + PaddleX` 在 CPU 上默认走 mkldnn 分支，会抛：

```
NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]
```

`OCR.build_ocr()` 里已按设备做了区分——**只在 CPU 下**设置 `enable_mkldnn=False`，GPU 不受影响：

```python
if not device.startswith("gpu"):
    kwargs["enable_mkldnn"] = False
```

### 4. `converter()` 必须输出固定 8 位

点击逻辑是"第 j 位是 1 就点 `POSITIONS[j]`"，所以二进制字符串**必须是 8 位**：

- 位数不足 → `"1"` 与 `POSITIONS` 下标整体错位 → **点错位置**
- 位数超过 8 → `POSITIONS[8]` 越界 → **程序崩溃**

因此用内置格式化即可（`format(5, "08b") == "00000101"`），不要手工算补零个数。

### 5. `extract_num()` 采用三级兜底

OCR 可能把前缀"二进制下，"认错（实测出现过 `制下，`、`刮下，`、`、` 等），
但**数字和"如何表示"都能稳定保留**，所以逐级放宽：

1. `二进制下，N如何表示？`（标准句式）
2. `N如何表示`（前缀被认错时的兜底）
3. 整行只出现一个数字时直接取它

---

## 常见问题

**Q：一直显示"无法识别到开始键"，卡住不动？**

1. 确认 `AREA1` 框住了开始按钮，可以截图核对坐标；
2. 确认 `OCR_MARGIN` 没有被改成 0 —— 贴边丢字会导致按钮文字识别为空；
3. `main.py` 的 `while` 循环**没有超时退出**，识别不到会一直重试，需要手动 `Ctrl+C`。

**Q：点击位置错位 / 点不到答案？**

`POSITIONS` 是按 1280 宽屏幕标定的，换分辨率必须重新测量；同时确认 `(640, 620)`
和 `(640, 1470)` 两处写死的点击点也符合当前分辨率。

**Q：首次运行卡在下载模型？**

本机会把模型缓存到 `C:\Users\<用户名>\.paddlex\official_models`。
本机已缓存 `PP-OCRv6_medium_det` / `PP-OCRv6_medium_rec`，离线可直接使用。
`paddleocr 3.7.0` 的默认中文模型就是这一对，因此 `build_ocr(DEVICE, False)` 无需联网。

**Q：能不能不用显卡？**

可以。把 `config.py` 的 `DEVICE` 改成 `"cpu"`，并改用 `paddlepaddle`（卸载 `paddlepaddle-gpu`）。
CPU 推理会慢一些，但因为是"截一帧识别一次"的节奏，实际影响有限。

**Q：GPU 报 CUDA / cuDNN 相关错误？**

确认装的是 `paddlepaddle-gpu` 而不是 `paddlepaddle`，且显卡驱动版本与 CUDA 版本匹配：

```bash
python -c "import paddle; print(paddle.device.is_compiled_with_cuda(), paddle.device.cuda.device_count())"
```

---

## 许可

仅供学习交流使用。

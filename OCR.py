import cv2   # 仅用于识别前给图像补白边（预处理）


def build_ocr(device, use_cached_models):
    """
    创建 PaddleOCR 识别器对象。

    参数:
        device            : "gpu:0" 或 "cpu"
        use_cached_models : 是否强制使用本机缓存的 PP-OCRv6_medium 模型
                            （本机无外网时用它可避免联网下载模型）

    返回:
        ocr   : PaddleOCR 实例
        info  : 描述信息字符串（版本号 / 使用的模型），仅用于打印
    """
    # 延迟导入：把耗时较长的 paddle 导入放到函数里，方便上层给出更清晰的报错
    try:
        import paddleocr                       # 主库：OCR 全流程（检测 + 方向分类 + 识别）
        from paddleocr import PaddleOCR        # PaddleOCR 类：一站式 OCR 引擎
    except ImportError as exc:                 # 没装依赖时给出人话提示，而不是一堆栈
        print("[错误] 未安装 paddleocr / paddlepaddle，请先执行：")
        print("       pip install paddlepaddle paddleocr")
        raise SystemExit(1) from exc           # 直接退出，退出码 1 表示失败

    ver = getattr(paddleocr, "__version__", "unknown")  # 取版本号，便于说明 API 差异

    # ---------- 组装构造参数 ----------
    kwargs = {
        "device": device,    # 推理设备："gpu:0" 用第一块显卡，"cpu" 用处理器
    }

    # PaddleOCR 3.x 用 use_textline_orientation 控制“文字行方向分类”（判断是否倒转 180°）；
    # PaddleOCR 2.x 用的是 use_angle_cls。这里按版本传入正确的参数名，保证两代都能跑。
    if ver.startswith("2"):
        kwargs["use_angle_cls"] = True       # 2.x：开启角度分类
        kwargs["lang"] = "ch"                # 2.x：语言模型选择放在 lang 上
    else:
        kwargs["use_textline_orientation"] = True  # 3.x：开启文字行方向矫正

    # 3.x 才支持用模型名精确指定“检测/识别”模型；2.x 传了会报错
    if not ver.startswith("2"):
        # 【CPU 上的关键修复】只在 CPU 推理时关闭 oneDNN(MKLDNN)：
        # 原因：paddlepaddle 3.3.1 + PaddleX 在 CPU 上默认走 mkldnn 分支，会抛
        #       NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support
        #       [pir::ArrayAttribute<pir::DoubleAttribute>]；关掉后走普通 paddle 后端即可。
        # GPU 上不存在该问题，也不需要这个开关，所以按设备区分。
        if not device.startswith("gpu"):
            kwargs["enable_mkldnn"] = False

        if use_cached_models:
            # 使用本机 C:\\Users\\<用户>\\.paddlex\\official_models 里已缓存的 v6 中等模型，
            # 这样在离线环境下也不会触发联网下载。
            kwargs["text_detection_model_name"] = "PP-OCRv6_medium_det"      # 文字检测模型
            kwargs["text_recognition_model_name"] = "PP-OCRv6_medium_rec"    # 文字识别模型
        else:
            # 不指定时 PaddleOCR 3.7 默认使用 PP-OCRv5_server 系列（首次运行需联网下载）
            kwargs["lang"] = "ch"            # 用默认模型时，通过 lang 选择中文模型

    # ---------- 真正创建引擎（首次运行会加载模型，耗时数秒） ----------
    ocr = PaddleOCR(**kwargs)
    
    # 生成人类可读的描述信息
    if use_cached_models and not ver.startswith("2"):
        model_desc = "PP-OCRv6_medium (det + rec, 本地缓存)"
    else:
        model_desc = "PaddleOCR 默认模型"
    return ocr, "paddleocr %s / %s" % (ver, model_desc)


# ============================ 以下是识别相关的工具 ============================

# 识别前在图像四周补的纯白留白（单位：像素）。
# 实测 PP-OCRv6_medium 在 CPU 和 GPU 上都有同一现象：文字紧贴图像边缘时会稳定
# 丢掉开头 1~4 个字符（"12345" -> "2345"、"二进制下，5如何表示？" -> "表示"）。
# 四周补上留白后识别即完全正确，80 是在 AREA1/AREA2 两种尺寸下都验证通过的值。
OCR_MARGIN = 80


def pad_white(frame_bgr, margin=OCR_MARGIN):
    """在 BGR 图像四周补纯白边，避免文字贴边导致 OCR 丢字。"""
    if margin <= 0:
        return frame_bgr
    return cv2.copyMakeBorder(frame_bgr, margin, margin, margin, margin,
                              cv2.BORDER_CONSTANT, value=(255, 255, 255))


def ocr_text(ocr, frame_bgr):
    """
    对一帧 BGR 图像做 OCR，返回 (识别文本, 置信度)；没识别到文字时返回 ("", 0.0)。

    【重要】PaddleOCR 3.x 的 predict() 返回的是 list[OCRResult]，
    而 OCRResult 继承自 dict（paddlex.inference.common.result.BaseResult(dict, ...)），
    因此只能用字符串键取值，不能用 result[0][1][0] 之类的下标写法。
    正确取值方式是 res[0]["rec_texts"] / res[0]["rec_scores"]。
    """
    res = ocr.predict(pad_white(frame_bgr))[0]   # 单张图 -> 返回列表只有 1 项
    texts = res["rec_texts"]             # list[str]
    scores = res["rec_scores"]           # list[float]
    if not texts:
        return "", 0.0                   # 无结果时直接返回，避免下标越界
    # 一句话可能被检测成多个文本框，拼接后还原整句，便于正则匹配
    return "".join(texts), float(scores[0])
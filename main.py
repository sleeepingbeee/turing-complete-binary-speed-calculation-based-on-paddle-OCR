import sys               # 用于设置标准输出编码、必要时退出程序
import time              # 用于统计耗时
from OCR import build_ocr, ocr_text
import cv2
import numpy as np
import mss
from config import *
from utils import *
import pyautogui


# Windows 控制台默认可能是 GBK，这里强制成 UTF-8，避免打印中文报编码错误
try:
    sys.stdout.reconfigure(encoding="utf-8")  # Python 3.7+ 支持重新配置输出流编码
    sys.stderr.reconfigure(encoding="utf-8")  # 错误流同样处理
except Exception:
    pass  # 如果解释器不支持就忽略，不影响主流程

import logging                                # 用于调低 paddle 的日志级别，保持输出清爽

# Paddle/PaddleX 默认会打印大量 INFO 日志，这里统一压到 ERROR 级别
logging.getLogger("paddle").setLevel(logging.ERROR)
logging.getLogger("paddlex").setLevel(logging.ERROR)


def main():
    # 初始化OCR 引擎（推理设备由 config.DEVICE 决定，当前为 "gpu:0"）
    print("=" * 72)
    t0 = time.time()                              # 记录开始时间
    ocr, desc = build_ocr(DEVICE, False)
    print("推理设备  : %s" % DEVICE)
    print("引擎      : %s" % desc)
    print("引擎已就绪: %.2f 秒" % (time.time() - t0))
    print("=" * 72)

    # 初始化屏幕捕获工具
    sct = mss.mss()
    print("屏幕捕获已就绪")
    print("=" * 72)

    # 检测启动游戏
    start_game = False
    while not start_game:
        # 1. 捕获屏幕帧，返回 BGRA 格式的 numpy 数组（AREA1 = 开始按钮）
        frame = np.array(sct.grab(AREA1))
        # 2. 转为 BGR 格式（与 PaddleOCR/OpenCV 兼容）
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        # 3. 内存中直接识别，无需保存文件
        text, confidence = ocr_text(ocr, frame_bgr)
        # 4. 打印识别结果
        print(f"识别结果：文本：{text} | 置信度：{confidence:.2f}")
        if "开始" in text:
            start_game = True
            pyautogui.click(640,620)
            print("点击开始键")
        else:
            print("无法识别到开始键")
        print("-" * 40)
        time.sleep(1)

    # 进行游戏
    for i in range(ROUNDS):        
        print("-" * 40)
        print(f"第 {i + 1} 轮开始")
        # 1. 捕获屏幕帧，返回 BGRA 格式的 numpy 数组（题目区用 AREA2 横条）
        frame = np.array(sct.grab(AREA2))
        # 2. 转为 BGR 格式（与 PaddleOCR/OpenCV 兼容）
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        # 3. 内存中直接识别，无需保存文件
        text, confidence = ocr_text(ocr, frame_bgr)
        # 4. 打印识别结果
        print(f"识别结果：文本：{text} | 置信度：{confidence:.2f}")
        num = extract_num(text)
        if num is None:
            pyautogui.click(640,1470)
            print("点击完成,过关完成")
            time.sleep(1)
            continue
        print(f"转换结果：{num},开始计算……")
        ans = converter(num)
        print(f"计算结果：{ans},开始点击……")
        if len(ans) > len(POSITIONS):
            print(f"结果位数 {len(ans)} 超过可选位置数 {len(POSITIONS)}，跳过本轮")
            time.sleep(1)
            continue
        for j, bit in enumerate(ans):
            if bit == "1":
                pyautogui.click(POSITIONS[j][0], POSITIONS[j][1])
        pyautogui.click(640,1470)
        print("点击完成,过关完成")
        time.sleep(1)
    print("-" * 40)
    print(f"运行结束,已通过{ROUNDS}轮游戏")
    cv2.destroyAllWindows()

# 只有“直接运行本文件”时才执行 main()，被 import 时不会自动跑
if __name__ == "__main__":
    main()

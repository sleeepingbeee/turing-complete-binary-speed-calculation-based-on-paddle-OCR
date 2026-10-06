# OCR 推理设备："gpu:0" 表示用第一块显卡，"cpu" 表示用处理器。
# 本机为 RTX 5080 Laptop（paddlepaddle-gpu 3.3.1），实测 GPU 单次推理约 0.04 秒（~25 FPS），
# 明显快于 CPU；若换到没有 NVIDIA 显卡/CUDA 的机器上运行，把这里改回 "cpu" 即可。
DEVICE = "gpu:0"

IF_TEST = True
ROUNDS = 63
AREA1 = {"top": 595, "left": 615, "width": 55, "height": 45}
AREA2 = {"top": 600, "left": 0, "width": 1280, "height": 50}
POSITIONS = ((350,1390),(425,1390),(500,1390),(570,1390),(640,1390),(720,1390),(800,1390),(870,1390))
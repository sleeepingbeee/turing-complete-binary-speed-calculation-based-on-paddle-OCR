def converter(num):
    """
    把十进制数转成 8 位二进制字符串（高位补 0），例如 5 -> "00000101"。

    说明：原实现是 str(0 * (8 - len(new_num_str)))，而 0 * 任意数恒等于 0，
    str(0) 恒为 "0"，所以永远只补一个 0：
      - num < 128 时位数不足，导致 "1" 与 POSITIONS 下标错位 → 点错位置；
      - num >= 128 时输出 9 个字符，j 会取到 8 → POSITIONS[8] 越界崩溃。
    这里直接用内置格式化，语义清晰，也不再需要手工计算 "0b" 前缀的偏移量。
    """
    return format(int(num), "08b")


def extract_num(s):
    """
    从题目文本中取出十进制数字，例如「二进制下，5如何表示？」-> 5。

    识别不到时返回 None（调用方必须判空）。
    """
    import re
    if not s:
        return None

    # 1) 标准句式：二进制下，N如何表示？（放宽标点与空白，OCR 常输出半角逗号/多余空格）
    m = re.search(r"二进制下\s*[，,：:]?\s*(\d+)\s*如何表示", s)
    if m:
        return int(m.group(1))

    # 2) 兜底：OCR 可能把前缀“二进制下，”认错（实测会出成“制下，”“刮下，”“、”等），
    #    但数字和“如何表示”都能稳定保留，所以只按“N如何表示”再匹配一次。
    m = re.search(r"(\d+)\s*如何表示", s)
    if m:
        return int(m.group(1))

    # 3) 再兜底：整行只出现一个数字时直接取它
    nums = re.findall(r"\d+", s)
    if len(nums) == 1:
        return int(nums[0])
    return None

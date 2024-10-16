import random, time
from datetime import datetime

# Function to simulate 50-shicao process and generate 6 lines (hexagram)
def shicao():
    lines = []
    for _ in range(6):
        total_sticks = 49  # 开始有49根蓍草
        # 取出一根不用，象征大衍之数
        total_sticks -= 1

        counts = []  # 存储每次变动的余数之和

        for _ in range(3):
            # 分两堆
            left_pile = random.randint(1, total_sticks - 1)
            right_pile = total_sticks - left_pile

            # 人一之用，从右手取出一根蓍草
            right_pile -= 1

            # 数左手蓍草，按四计算余数
            left_remainder = left_pile % 4 or 4

            # 数右手蓍草，按四计算余数
            right_remainder = right_pile % 4 or 4

            # 本次余数之和，加上人一之用的1根
            total_remainder = left_remainder + right_remainder + 1  # 人一之用

            # 将余数之和的蓍草移除
            total_sticks -= total_remainder

            # 记录本次余数之和
            counts.append(total_remainder)

        # 根据三次余数之和判断爻的性质
        # 第一次余数：5或9，第二次和第三次余数：4或8
        first = counts[0]
        second = counts[1]
        third = counts[2]

        # 判断多（大于等于8）和少（小于等于7）
        first_many = first >= 8
        second_many = second >= 8
        third_many = third >= 8

        many_count = sum([first_many, second_many, third_many])

        if many_count == 3:
            lines.append(6)  # 老阴
        elif many_count == 2:
            lines.append(8)  # 少阴
        elif many_count == 1:
            lines.append(7)  # 少阳
        elif many_count == 0:
            lines.append(9)  # 老阳
        else:
            # 异常情况
            print(f"计算错误，余数之和：{counts}")
            lines.append(0)  # 占位符

    return lines


# 梅花易数法函数
def meihua():
    # 获取当前日期和时间
    print("\n您选择了梅花易数法占卜，将使用当前年月日时。") # 似乎一直都没有变卦
    time.sleep(2.5)
    now = datetime.now()

    # 上卦（外卦）：（月 + 日）模8，0按8计算
    upper = (now.month + now.day) % 8
    upper = 8 if upper == 0 else upper

    # 下卦（内卦）：（时 + 分）模8，0按8计算
    lower = (now.hour + now.minute) % 8
    lower = 8 if lower == 0 else lower

    # 动爻：（年 + 月 + 日 + 时 + 分）模6，0按6计算
    total = now.year + now.month + now.day + now.hour + now.minute
    changing_line = total % 6
    changing_line = 6 if changing_line == 0 else changing_line

    # 数字对应八卦
    trigrams = {
        1: '乾',  # 天
        2: '兑',  # 泽
        3: '离',  # 火
        4: '震',  # 雷
        5: '巽',  # 风
        6: '坎',  # 水
        7: '艮',  # 山
        8: '坤',  # 地
    }

    # 八卦对应二进制代码
    trigram_to_binary = {
        '乾': '111',
        '兑': '011',
        '离': '101',
        '震': '001',
        '巽': '110',
        '坎': '010',
        '艮': '100',
        '坤': '000',
    }

    # 获取上卦和下卦
    upper_trigram = trigrams.get(upper)
    lower_trigram = trigrams.get(lower)

    # 获取二进制表示
    upper_binary = trigram_to_binary.get(upper_trigram)
    lower_binary = trigram_to_binary.get(lower_trigram)

    # 合并形成六爻卦
    hexagram_binary = upper_binary + lower_binary

    # 构建初始卦爻列表
    lines = [int(bit) for bit in hexagram_binary]

    # 确定动爻
    # 梅花易数中通常只有一爻变化，即对应动爻
    # 爻的编号从下往上数，1到6
    changing_line_index = 6 - changing_line  # 转换为索引（0到5）
    moving_line_value = lines[changing_line_index]
    # 翻转动爻
    lines[changing_line_index] = 1 if moving_line_value == 0 else 0

    # 将二进制爻值转换为标准的爻值（6,7,8,9）
    hex_lines = []
    for idx, val in enumerate(hexagram_binary):
        line = 7 if val == '1' else 8  # 阳爻为7，阴爻为8
        if idx == changing_line_index:
            # 这是动爻
            line = 9 if val == '1' else 6  # 老阳为9，老阴为6
        hex_lines.append(line)

    return hex_lines


def coin():
    print("\n您选择了三枚铜钱法占卜。")
    print("系统将为您模拟投掷。")
    time.sleep(1)

    lines = []
    for _ in range(6):
        tosses = []
        for _ in range(3):
            toss = random.choice([2, 3])  # 2代表阴（反面），3代表阳（正面）
            tosses.append(toss)
        line_value = sum(tosses)
        if line_value == 6:
            lines.append(6)  # 老阴
        elif line_value == 7:
            lines.append(7)  # 少阳
        elif line_value == 8:
            lines.append(8)  # 少阴
        elif line_value == 9:
            lines.append(9)  # 老阳
        else:
            print("投掷结果计算错误。")
            lines.append(0)
    return lines


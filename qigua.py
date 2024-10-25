import random, time
from datetime import datetime

class DivinationMethod:
    """Base class for divination methods."""

    def perform_divination(self):
        raise NotImplementedError("Subclasses should implement this method.")

class ShicaoMethod(DivinationMethod):
    """Implements the 50-yarrow stalk divination method."""

    def perform_divination(self):
        print("\n您选择了五十蓍草法占卜。")
        time.sleep(1)
        lines = []
        for _ in range(6):
            line_value = self.calculate_line()
            lines.append(line_value)
        return lines

    @staticmethod
    def calculate_line():
        total_sticks = 49
        total_sticks -= 1  # Remove one stick
        counts = []
        for _ in range(3):
            left = random.randint(1, total_sticks - 1)
            right = total_sticks - left
            right -= 1  # Human use one stick
            left_remain = left % 4 or 4
            right_remain = right % 4 or 4
            total_remainder = left_remain + right_remain + 1
            total_sticks -= total_remainder
            counts.append(total_remainder)
        line_value = ShicaoMethod.determine_line_value(counts)
        return line_value

    @staticmethod
    def determine_line_value(counts):
        many_count = sum(1 for count in counts if count >= 8)
        if many_count == 0:
            return 9  # Old Yang
        elif many_count == 1:
            return 7  # Young Yang
        elif many_count == 2:
            return 8  # Young Yin
        elif many_count == 3:
            return 6  # Old Yin
        else:
            return 0  # Error

class CoinMethod(DivinationMethod):
    """Implements the three-coin divination method."""

    def perform_divination(self):
        print("\n您选择了三枚铜钱法占卜。")
        time.sleep(1)
        lines = []
        for _ in range(6):
            line_value = self.throw_coins()
            lines.append(line_value)
        return lines

    @staticmethod
    def throw_coins():
        tosses = [random.choice([2, 3]) for _ in range(3)]  # 2 for Yin, 3 for Yang
        total = sum(tosses)
        line_map = {6: 6, 7: 7, 8: 8, 9: 9}
        line_value = line_map.get(total, 0)
        if line_value == 0:
            print("投掷结果计算错误。")
        return line_value

import random
import time
from datetime import datetime
from validateTime import get_current_time, get_user_time_input

class MeihuaMethod(DivinationMethod):
    """Implements the Meihua Yishu divination method."""

    def perform_divination(self):
        print("\n您选择了梅花易数法占卜。")
        print("注意：数字卦只可以用较简单的小事，不可以用与人生大事。")

        # Ask if the user wants to use three numbers or the current time
        use_numbers = input("\n是否要使用三个三位数数字？(y/n): ").lower()

        if use_numbers == 'y':
            numbers = self.get_three_numbers()
            lower_gua, upper_gua, changing_line = self.calculate_gua_from_numbers(numbers)

            # Ask for time input (current time or user-provided)
            time_choice = input("\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': ").strip()
            if time_choice == '1':
                current_time = get_current_time()
            elif time_choice == '2':
                current_time = get_user_time_input()
            else:
                print("无效输入，默认使用当前时间。")
                current_time = get_current_time()
        
        else:
            print("将使用当前年月日时分起卦。")
            now = datetime.now()
            lower_gua, upper_gua, changing_line = self.calculate_trigrams(now)

        # Construct hexagram and return the lines
        lines = self.construct_hexagram(upper_gua, lower_gua, changing_line)
        return lines

    def get_three_numbers(self):
        """Prompts the user to input three three-digit numbers between 100 and 999."""
        numbers = []
        for i in range(1, 4):
            while True:
                number = input(f"请输入第 {i} 个三位数数字 (100-999): ").strip()
                if number.isdigit() and 100 <= int(number) <= 999:
                    numbers.append(int(number))
                    break
                else:
                    print("无效输入。请输入一个100到999之间的三位数。")
        return numbers

    @staticmethod
    def calculate_gua_from_numbers(numbers):
        """Calculates the lower gua, upper gua, and changing line from the given numbers."""
        lower_gua = numbers[0] % 8 or 8  # Lower gua, use 8 if remainder is 0
        upper_gua = numbers[1] % 8 or 8  # Upper gua, use 8 if remainder is 0
        changing_line = numbers[2] % 6 or 6  # Changing line, use 6 if remainder is 0
        return lower_gua, upper_gua, changing_line

    @staticmethod
    def calculate_trigrams(now):
        """Calculates the lower and upper gua, and the changing line using the current time."""
        lower_gua = (now.hour + now.minute) % 8 or 8  # Lower gua: (hour + minute) % 8
        upper_gua = (now.month + now.day) % 8 or 8    # Upper gua: (month + day) % 8
        total = now.year + now.month + now.day + now.hour + now.minute
        changing_line = total % 6 or 6  # Changing line
        return lower_gua, upper_gua, changing_line

    @staticmethod
    def construct_hexagram(upper, lower, changing_line):
        """Constructs the hexagram (6 lines) based on upper and lower gua and the changing line."""
        trigrams = {
            1: '111',  # 乾
            2: '011',  # 兑
            3: '101',  # 离
            4: '001',  # 震
            5: '110',  # 巽
            6: '010',  # 坎
            7: '100',  # 艮
            8: '000',  # 坤
        }

        upper_binary = trigrams.get(upper, '000')  # Default to 坤 if not found
        lower_binary = trigrams.get(lower, '000')  # Default to 坤 if not found

        # Combine upper and lower gua into a single binary string (upper comes first)
        hexagram_binary = upper_binary + lower_binary
        lines = [int(bit) for bit in hexagram_binary]

        # Flip the bit for the changing line
        changing_line_index = 6 - changing_line  # Changing line index from bottom (1-based)
        lines[changing_line_index] ^= 1  # Flip the bit at the changing line

        # Convert binary digits to line values (7 for Yang, 8 for Yin, 9 for Old Yang, 6 for Old Yin)
        hex_lines = []
        for idx, val in enumerate(lines):
            line = 7 if val == 1 else 8  # Yang or Yin
            if idx == changing_line_index:
                line = 9 if val == 1 else 6  # Old Yang or Old Yin
            hex_lines.append(line)

        return hex_lines

    
class ManualInputMethod(DivinationMethod):
    """Allows the user to input their own hexagram lines."""

    def perform_divination(self):
        while True:
            gua_input = input("请输入您的卦象 (格式为六个数字，每个数字为6到9，从下到上输入): ").strip()
            if gua_input.isdigit() and len(gua_input) == 6 and all(c in '6789' for c in gua_input):
                lines = [int(c) for c in gua_input]
                return lines
            else:
                print("无效的卦象输入。请使用六位数字（范围为6到9）。")

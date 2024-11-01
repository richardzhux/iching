#!/usr/bin/env python3

import time
from qigua import ShicaoMethod, CoinMethod, MeihuaMethod, ManualInputMethod
from validateTime import get_current_time, get_user_time_input
from bazitime import BaZiCalculator
from bazicalc import Hexagram
def main():
    print("\n欢迎使用理查德猪的易经占卜应用！")

    methods = {
        's': ShicaoMethod,
        'c': CoinMethod,
        'm': MeihuaMethod,
        'x': ManualInputMethod
    }

    while True:
        user_choice = input(
            "\n请选择占卜方法：\n"
            "1. 五十蓍草法占卜 (输入 's')\n"
            "2. 三枚铜钱法占卜 (输入 'c')\n"
            "3. 梅花易数法占卜 (输入 'm')\n"
            "4. 输入您自己的卦 (输入 'x')\n"
            "q. 退出 (输入 'q')\n\n"
            "您的选择: "
        ).lower()

        if user_choice in methods:
            method_class = methods[user_choice]
            method = method_class()
            lines = method.perform_divination()
            if user_choice == 'x':
                # For manual input, ask for time
                time_choice = input("\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': ").strip()
                if time_choice == '1':
                    current_time = get_current_time()
                elif time_choice == '2':
                    current_time = get_user_time_input()
                else:
                    print("无效输入，将默认使用当前时间。")
                    current_time = get_current_time()
            else:
                # For methods 1-3, use current time automatically
                current_time = get_current_time()
        elif user_choice == 'q':
            print("\n感谢您使用易经占卜应用，再见！\n")
            break
        else:
            print("无效输入，请重新选择。")
            continue

        # Calculate BaZi and Five Elements
        bazi_calculator = BaZiCalculator(current_time)
        bazi_output, elements_output = bazi_calculator.calculate_bazi()

        print("\n起卦时间:")
        print(current_time.strftime("%Y.%m.%d %H:%M"))
        print(bazi_output)
        print(elements_output)

        # Load hexagram data
        hexagrams_dict = Hexagram.load_hexagrams('guaxiang.txt')

        # Create the main hexagram
        main_hexagram = Hexagram(lines, hexagrams_dict)
        main_hexagram.display()

        # Ask the user if they want to perform another divination
        again = input("\n是否要再次占卜？(如继续，请输入'y'，任何其他输入为退出): ").lower()
        if again != 'y':
            print("\n感谢您使用易经占卜应用，再见！\n")
            break

if __name__ == "__main__":
    main()

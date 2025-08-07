#!/usr/bin/env python3

import time
from qigua import ShicaoMethod, CoinMethod, MeihuaMethod, ManualInputMethod
from validateTime import get_current_time, get_user_time_input
from sysusage import display_system_usage
from bazitime import BaZiCalculator
from bazicalc import Hexagram
from rateJiXiong import analyze_file as keyword_analyze_file

from closeai import closeai, get_combined_explanation
import os

from najia.najia import Najia

from session_logger import TeeLogger

from dotenv import load_dotenv
load_dotenv()  # loads .env into environment variables

def get_valid_choice(prompt, choices, quit_char="q", err_msg="输入无效，请重新输入。"):
    """Loop until user enters a valid choice from choices or quits."""
    valid_choices = set(c.lower() for c in choices) | {quit_char}
    while True:
        ans = input(prompt).strip().lower()
        if ans == quit_char:
            print("\n感谢您使用易经占卜应用，再见！\n")
            exit(0)
        if ans in valid_choices:
            return ans
        print(err_msg)


def main():
    print("\n欢迎使用理查德猪的易经占卜应用！")

    topic_map = {
        "1": "事业",
        "2": "感情",
        "3": "财运",
        "4": "身体健康",
        "5": "整体运势",
        "6": "其他/跳过",
        "q": "就地退出"
    }

    methods = {
        "s": ShicaoMethod,
        "c": CoinMethod,
        "m": MeihuaMethod,
        "x": ManualInputMethod,
    }

    while True:
        with TeeLogger() as logger:
            try:
                print("\n请选择本次占卜主题：")
                for k, v in topic_map.items():
                    print(f"{k}. {v}")

                topic_choice = get_valid_choice("\n请输入主题编号 (1-6): ", topic_map.keys())
                if topic_choice.lower() == "q":
                    print("\n感谢您使用易经占卜应用，再见！\n")
                    exit(0)
                topic = topic_map[topic_choice]

                specify_q = get_valid_choice("\n是否要输入一个具体问题？(y/n): ", {"y", "n"})
                user_question = None
                if specify_q == "y":
                    user_question = input("\n请输入您的具体问题（按回车结束，或输入 'q' 退出）：").strip()
                    if user_question.lower() == "q":
                        print("\n感谢您使用易经占卜应用，再见！\n")
                        exit(0)
                    if not user_question:
                        user_question = None

                print(
                    "\n请选择占卜方法：\n"
                    "1. 五十蓍草法占卜 (输入 's')\n"
                    "2. 三枚铜钱法占卜 (输入 'c')\n"
                    "3. 梅花易数法占卜 (输入 'm')\n"
                    "4. 输入您自己的卦 (输入 'x')\n"
                    "r. 查看系统资源 (输入 'r')\n"
                    "q. 退出 (输入 'q')"
                )

                user_choice = get_valid_choice("\n您的选择: ", set(methods.keys()) | {"r"})
                if user_choice in methods:
                    method_class = methods[user_choice]
                    method = method_class()
                    lines = method.perform_divination()
                    if user_choice == "x":
                        time_choice = get_valid_choice(
                            "\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': ",
                            {"1", "2"}
                        )
                        if time_choice == "1":
                            current_time = get_current_time()
                        else:
                            current_time = get_user_time_input()
                    else:
                        current_time = get_current_time()
                elif user_choice == "r":
                    display_system_usage()
                    print("\n感谢您使用易经占卜应用，再见！\n")
                    exit(0)

                # Calculate BaZi and Five Elements
                bazi_calculator = BaZiCalculator(current_time)
                bazi_output, elements_output = bazi_calculator.calculate_bazi()

                print("\n起卦时间:")
                print(current_time.strftime("%Y.%m.%d %H:%M"))
                print(bazi_output)
                print(elements_output)

                # Load hexagram data
                hexagrams_dict = Hexagram.load_hexagrams("guaxiang.txt")

                # Create the main hexagram
                main_hexagram = Hexagram(lines, hexagrams_dict)
                main_hexagram.display()

                from najia.najia import Najia
                params = [1 if x in [7,9] else 0 for x in lines]
                date_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
                najia = Najia()
                najia.compile(params=params, date=date_str)

                print("\n【纳甲六亲、六神、动爻等详细信息】")
                for k, v in najia.data.items():
                    print(f"{k}: {v}")


                bengua = main_hexagram.find_explanation_file()
                zhigua = None
                if main_hexagram.changed_hexagram:
                    zhigua = main_hexagram.changed_hexagram.find_explanation_file()

                explanation_text = get_combined_explanation(bengua, zhigua)


                if explanation_text:
                    ai_choice = input("\n是否使用 OpenAI API 分析卦辞？(如分析请输入'y'，其他任意键跳过): ").strip().lower()
                    if ai_choice == "y":
                        api_key = os.environ.get("OPENAI_API_KEY")
                        try:
                            analysis = closeai(
                                explanation_text,
                                api_key=api_key,
                                topic=topic,
                                user_question=user_question
                            )
                            print("\nAI 分析结果:\n" + analysis)
                        except Exception as exc:
                            print(f"AI 分析失败: {exc}")

                again = input("\n请问您是否要再次卜卦？(如继续，请输入'y'，任何其他视为退出): ").strip().lower()
                logger.save()

                if again != "y":
                    print("\n感谢您使用易经占卜应用，再见！\n")
                    break
            except Exception as exc:
                print(f"发生异常: {exc}")
                logger.save()
                break

if __name__ == "__main__":
    main()

# 下一步：纳甲，api level fine tune，context长度，回答风格，连接命主的八字和大运
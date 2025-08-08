# -*- coding: utf-8 -*-
"""
bazicalc.py — one-file interactive console runner.

- Keeps your user prompts and flow inside this file
- Uses TeeLogger for file logging (same behavior as your previous main)
- Integrates: BaZi, Hexagram (with 本卦/变卦/错卦/综卦/互卦 + guaci embedding), Najia, optional AI analysis
- Prints AND logs; also saves a structured result in memory (optional convenience)

How to use from your main.py:
    from bazicalc import run_iching_console
    run_iching_console()
"""

from __future__ import annotations
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv

# ---- External deps you already have in your project ----
from qigua import ShicaoMethod, CoinMethod, MeihuaMethod, ManualInputMethod
from validateTime import get_current_time, get_user_time_input
from sysusage import display_system_usage
from bazitime import BaZiCalculator
from najia.najia import Najia
from session_logger import TeeLogger
from closeai import closeai

load_dotenv()

# ------------------------------
# Configuration
# ------------------------------
COMPLETE_DIR = os.path.expanduser("~/Documents/Hexarchive/guilty")
ACQUITTAL_DIR = os.path.expanduser("~/Documents/Hexarchive/acquittal")
HEX_FILE = "guaxiang.txt"
GUACI_FOLDER = "guaci"

# ------------------------------
# In-memory snapshot (optional)
# ------------------------------
_RESULTS_HISTORY: List[Dict[str, Any]] = []
_LAST_RESULT: Optional[Dict[str, Any]] = None

def get_last_result() -> Optional[Dict[str, Any]]:
    """Optional convenience: last run’s structured data."""
    return _LAST_RESULT

def get_results_history() -> List[Dict[str, Any]]:
    """Optional convenience: all runs since program start."""
    return list(_RESULTS_HISTORY)

def _save_structured_result(result: Dict[str, Any]) -> None:
    global _LAST_RESULT
    _LAST_RESULT = result
    _RESULTS_HISTORY.append(result)

# ------------------------------
# Hexagram model (your logic)
# ------------------------------
class Hexagram:
    """Represents a hexagram and its related calculations."""

    def __init__(self, lines, hexagrams_dict):
        self.lines = lines  # List of 6 integers (6-9)
        self.hexagrams_dict = hexagrams_dict
        self.binary = "".join(["1" if x in [7, 9] else "0" for x in self.lines])
        self.name, self.explanation = hexagrams_dict.get(
            self.binary, ("未知卦", "未找到解释")
        )
        self.changed_hexagram = self.calculate_changed_hexagram()
        self.inverse_hexagram = self.calculate_inverse_hexagram()
        self.reverse_hexagram = self.calculate_reverse_hexagram()
        self.mutual_hexagram = self.calculate_mutual_hexagram()

    @staticmethod
    def load_hexagrams(file_path):
        hexagrams = {}
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines[1:]:
                parts = line.strip().split(", ")
                if len(parts) == 3:
                    gua, binary, jieshi = parts
                    hexagrams[binary] = (gua, jieshi)
        return hexagrams

    def calculate_changed_hexagram(self):
        changed_lines = []
        has_moving_line = False
        for x in self.lines:
            if x == 9:
                changed_lines.append(8)  # Old Yang changes to Yin
                has_moving_line = True
            elif x == 6:
                changed_lines.append(7)  # Old Yin changes to Yang
                has_moving_line = True
            else:
                changed_lines.append(x)
        if has_moving_line:
            return Hexagram(changed_lines, self.hexagrams_dict)
        else:
            return None  # No changing lines

    def calculate_inverse_hexagram(self):
        inverse_binary = "".join(["1" if b == "0" else "0" for b in self.binary])
        name, explanation = self.hexagrams_dict.get(
            inverse_binary, ("未知卦", "未找到解释")
        )
        return name, explanation

    def calculate_reverse_hexagram(self):
        reverse_binary = self.binary[::-1]
        name, explanation = self.hexagrams_dict.get(
            reverse_binary, ("未知卦", "未找到解释")
        )
        return name, explanation

    def calculate_mutual_hexagram(self):
        if len(self.binary) == 6:
            mutual_binary = self.binary[1:4] + self.binary[2:5]
            name, explanation = self.hexagrams_dict.get(
                mutual_binary, ("未知卦", "未找到解释")
            )
            return name, explanation
        else:
            return None, None

    def find_explanation_file(self, folder="guaci"):
        """Find the file corresponding to this hexagram's name in the given folder."""
        if not os.path.isdir(folder):
            return None
        for file_name in os.listdir(folder):
            if self.name in file_name:
                file_path = os.path.join(folder, file_name)
                return file_path
        return None

    def _explanation_file_text(self, file_type="本卦", folder="guaci"):
        file_path = self.find_explanation_file(folder)
        if not file_path:
            return f"未找到 {file_type} 对应的文件: {self.name}\n"
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return f"\n{file_type}: {self.name} 对应的文件: {file_path}\n内容:\n{content}\n"

    def to_text(self, folder="guaci"):
        """Build EXACTLY what display() shows, but as a string (with embedded guaci text)."""
        out = []
        out.append("\n您的卦象:")
        reversed_lines = self.lines[::-1]
        for i, line in enumerate(reversed_lines):
            symbol = "---" if line in [7, 9] else "- -"
            moving = " O" if line == 9 else " X" if line == 6 else ""
            out.append(f"第 {6 - i} 爻: {symbol}{moving}")

        out.append(f"\n本卦: {self.name} - 解释: {self.explanation}")

        if self.changed_hexagram:
            out.append(f"变卦: {self.changed_hexagram.name} - 解释: {self.changed_hexagram.explanation}")
            # embed file contents instead of printing:
            out.append(self._explanation_file_text(file_type="本卦", folder=folder))
            out.append(self.changed_hexagram._explanation_file_text(file_type="变卦", folder=folder))
        else:
            out.append("变卦：没有动爻，故无变卦 - 404 Not Found。")
            out.append(self._explanation_file_text(file_type="本卦", folder=folder))

        inverse_name, inverse_explanation = self.inverse_hexagram
        out.append(f"错卦: {inverse_name} - 解释: {inverse_explanation}")

        reverse_name, reverse_explanation = self.reverse_hexagram
        out.append(f"综卦: {reverse_name} - 解释: {reverse_explanation}")

        mutual_name, mutual_explanation = self.mutual_hexagram
        if mutual_name:
            out.append(f"互卦: {mutual_name} - 解释: {mutual_explanation}")
        else:
            out.append("互卦未找到。")

        return "\n".join(out)

    def display(self, folder="guaci"):
        print(self.to_text(folder=folder))


# ------------------------------
# Structured result holder
# ------------------------------
@dataclass
class SessionResult:
    timestamp: str
    topic: str
    user_question: Optional[str]
    method: str
    lines: List[int]
    current_time_str: str
    bazi_output: str
    elements_output: str
    hex_text: str
    najia_data: Dict[str, Any]
    ai_analysis: Optional[str]


# ------------------------------
# Console helpers
# ------------------------------
def _get_valid_choice(prompt, choices, logger=None, quit_char="q", err_msg="输入无效，请重新输入。"):
    valid_choices = set(c.lower() for c in choices) | {quit_char}
    while True:
        ans = input(prompt).strip().lower()
        if ans == quit_char:
            print("\n感谢您使用易经占卜应用，再见！\n")
            if logger:
                logger.output_dir = ACQUITTAL_DIR
                logger.save()
            raise SystemExit(0)
        if ans in valid_choices:
            return ans
        print(err_msg)

# ------------------------------
# THE one-call interactive app
# ------------------------------

def run_iching_console(
    hex_file: str = HEX_FILE,
    guaci_folder: str = GUACI_FOLDER,
    complete_dir: str = COMPLETE_DIR,
    acquittal_dir: str = ACQUITTAL_DIR,
    enable_ai: bool = True,
) -> None:
    """
    One-line entry point. Handles prompting, divination, BaZi, Hexagram, Najia,
    printing, TeeLogger saving, and AI analysis. Now AI receives the ENTIRE
    structured session dict (topic, question, BaZi, elements, hex_text, Najia, etc.).
    """
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
        "s": ("五十蓍草法", ShicaoMethod),
        "c": ("三枚铜钱法", CoinMethod),
        "m": ("梅花易数法", MeihuaMethod),
        "x": ("手动输入",   ManualInputMethod),
    }

    os.makedirs(complete_dir, exist_ok=True)
    os.makedirs(acquittal_dir, exist_ok=True)

    while True:
        output_dir = complete_dir
        with TeeLogger(output_dir) as logger:
            try:
                print("\n欢迎使用理查德猪的易经占卜应用！")

                # 选择主题
                print("\n请选择本次占卜主题：")
                for k, v in topic_map.items():
                    print(f"{k}. {v}")
                topic_choice = _get_valid_choice("\n请输入主题编号 (1-6): ", topic_map.keys(), logger=logger)
                topic = topic_map[topic_choice]

                # 是否输入具体问题
                specify_q = _get_valid_choice("\n是否要输入一个具体问题？(y/n): ", {"y", "n"}, logger=logger)
                user_question = None
                if specify_q == "y":
                    user_question = input("\n请输入您的具体问题（按回车结束，或输入 'q' 退出）：").strip()
                    if user_question.lower() == "q":
                        print("\n感谢您使用易经占卜应用，再见！\n")
                        logger.output_dir = acquittal_dir
                        logger.save()
                        raise SystemExit(0)
                    if not user_question:
                        user_question = None

                # 选择占卜方法
                print(
                    "\n请选择占卜方法：\n"
                    "1. 五十蓍草法占卜 (输入 's')\n"
                    "2. 三枚铜钱法占卜 (输入 'c')\n"
                    "3. 梅花易数法占卜 (输入 'm')\n"
                    "4. 输入您自己的卦 (输入 'x')\n"
                    "r. 查看系统资源 (输入 'r')\n"
                    "q. 退出 (输入 'q')"
                )
                user_choice = _get_valid_choice("\n您的选择: ", set(methods.keys()) | {"r"}, logger=logger)
                if user_choice == "r":
                    display_system_usage()
                    print("\n感谢您使用易经占卜应用，再见！\n")
                    logger.output_dir = acquittal_dir
                    logger.save()
                    raise SystemExit(0)

                method_name, method_class = methods[user_choice]
                method = method_class()
                lines = method.perform_divination()

                # 时间来源
                if user_choice == "x":
                    time_choice = _get_valid_choice(
                        "\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': ",
                        {"1", "2"},
                        logger=logger
                    )
                    if time_choice == "1":
                        current_time = get_current_time()
                    else:
                        current_time = get_user_time_input()
                else:
                    current_time = get_current_time()

                # BaZi
                bazi_calculator = BaZiCalculator(current_time)
                bazi_output, elements_output = bazi_calculator.calculate_bazi()

                print("\n起卦时间:")
                print(current_time.strftime("%Y.%m.%d %H:%M"))
                print(bazi_output)
                print(elements_output)

                # Hexagrams
                hexagrams_dict = Hexagram.load_hexagrams(hex_file)
                main_hexagram = Hexagram(lines, hexagrams_dict)
                # Print + guaci embed
                main_hexagram.display(folder=guaci_folder)

                # Najia
                params = [1 if x in [7, 9] else 0 for x in lines]
                date_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
                najia = Najia()
                najia.compile(params=params, date=date_str)

                print("\n【纳甲六亲、六神、动爻等详细信息】")
                for k, v in najia.data.items():
                    print(f"{k}: {v}")

                # ---------- Build the FULL session dict BEFORE AI ----------
                session_dict = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "topic": topic,
                    "user_question": user_question,
                    "method": method_name,
                    "lines": lines,
                    "current_time_str": current_time.strftime("%Y.%m.%d %H:%M"),
                    "bazi_output": bazi_output,
                    "elements_output": elements_output,
                    "hex_text": main_hexagram.to_text(folder=guaci_folder),
                    "najia_data": dict(najia.data),
                    "ai_analysis": None,  # will be filled after AI
                }

                # ---------------------- AI section (dict in) ----------------------
                if enable_ai:
                    ai_choice = input("\n是否使用 OpenAI API 分析（将使用完整会话信息）？(y/n): ").strip().lower()
                    if ai_choice == "y":
                        api_key = os.environ.get("OPENAI_API_KEY")
                        try:
                            # 直接把整个 session_dict 传进去；不再传 enforce_json / return_dict
                            ai_text = closeai(session_dict, api_key=api_key)

                            session_dict["ai_analysis"] = ai_text
                            print("\nAI 分析结果:\n" + ai_text)

                        except Exception as exc:
                            print(f"AI 分析失败: {exc}")

                # Save the structured result in-memory (optional convenience)
                _save_structured_result(session_dict)

                # wrap-up and ask to continue
                again = input("\n请问您是否要再次卜卦？(如继续，请输入'y'，任何其他视为退出): ").strip().lower()
                logger.save()  # persist current session log to file
                if again != "y":
                    print("\n感谢您使用易经占卜应用，再见！\n")
                    break

            except SystemExit:
                raise
            except Exception as exc:
                print(f"发生异常: {exc}")
                logger.output_dir = acquittal_dir
                logger.save()
                break

# --- Add this helper to bazicalc.py ---

from typing import Optional, List, Tuple
from datetime import datetime

def compute_session_for_gui(
    *,
    topic: str,
    user_question: Optional[str],
    method_key: str,                      # "s" | "c" | "m" | "x"
    use_current_time: bool = True,
    custom_time: Optional[datetime] = None,
    manual_lines: Optional[List[int]] = None,   # required if method_key == "x"
    hex_file: str = HEX_FILE,
    guaci_folder: str = GUACI_FOLDER,
    enable_ai: bool = False,
    api_key: Optional[str] = None,
) -> Tuple[dict, str]:
    """
    Pure, non-interactive one-shot for GUI: no input(), no prints.
    Returns (session_dict, full_text_to_show).
    """
    # 1) choose method & produce lines
    methods = {
        "s": ("五十蓍草法", ShicaoMethod),
        "c": ("三枚铜钱法", CoinMethod),
        "m": ("梅花易数法", MeihuaMethod),
        "x": ("手动输入",   ManualInputMethod),
    }
    if method_key not in methods:
        raise ValueError("method_key 必须是 's'/'c'/'m'/'x' 之一")
    method_name, method_class = methods[method_key]

    if method_key == "x":
        if not manual_lines or len(manual_lines) != 6 or not all(v in (6,7,8,9) for v in manual_lines):
            raise ValueError("手动输入：必须提供 6 个爻值（每个为 6/7/8/9），例如 [7,7,6,9,8,7]")
        lines = manual_lines
    else:
        method = method_class()
        lines = method.perform_divination()

    # 2) time
    if use_current_time:
        current_time = get_current_time()
    else:
        if custom_time is None:
            raise ValueError("自定义时间模式需要提供 custom_time（datetime）")
        current_time = custom_time

    # 3) BaZi
    bazi_calculator = BaZiCalculator(current_time)
    bazi_output, elements_output = bazi_calculator.calculate_bazi()

    # 4) Hexagrams
    hexagrams_dict = Hexagram.load_hexagrams(hex_file)
    main_hexagram = Hexagram(lines, hexagrams_dict)
    hex_text = main_hexagram.to_text(folder=guaci_folder)

    # 5) Najia
    params = [1 if x in (7,9) else 0 for x in lines]
    date_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    najia = Najia()
    najia.compile(params=params, date=date_str)

    # 6) build session dict
    session_dict = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic,
        "user_question": user_question,
        "method": method_name,
        "lines": lines,
        "current_time_str": current_time.strftime("%Y.%m.%d %H:%M"),
        "bazi_output": bazi_output,
        "elements_output": elements_output,
        "hex_text": hex_text,
        "najia_data": dict(najia.data),
        "ai_analysis": None,
    }

    # 7) optional AI
    if enable_ai:
        ai_text = closeai(session_dict, api_key=api_key)
        session_dict["ai_analysis"] = ai_text

    # 8) compose a full text block (no prints)
    chunks = []
    chunks.append("起卦时间: " + session_dict["current_time_str"])
    chunks.append(str(bazi_output))
    chunks.append(str(elements_output))
    chunks.append(hex_text)
    chunks.append("\n【纳甲六亲、六神、动爻等详细信息】")
    for k, v in session_dict["najia_data"].items():
        chunks.append(f"{k}: {v}")
    if session_dict["ai_analysis"]:
        chunks.append("\n【AI 分析】\n" + session_dict["ai_analysis"])
    full_text = "\n".join(chunks)

    return session_dict, full_text

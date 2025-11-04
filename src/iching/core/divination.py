from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, List, Optional, Protocol


class LineGenerator(Protocol):
    def __call__(self) -> int:
        ...


def _default_sleep(seconds: float) -> None:
    time.sleep(seconds)


def _default_input(prompt: str) -> str:
    return input(prompt)


def _default_now() -> datetime:
    return datetime.now()


class DivinationMethod(Protocol):
    """Contract for divination strategies."""

    key: str
    name: str

    def generate_lines(
        self,
        *,
        interactive: bool = True,
        input_func: Callable[[str], str] = _default_input,
        sleep_func: Callable[[float], None] = _default_sleep,
        now_func: Callable[[], datetime] = _default_now,
        manual_lines: Optional[Iterable[int]] = None,
    ) -> List[int]:
        ...


@dataclass(slots=True)
class ShicaoMethod:
    key: str = "s"
    name: str = "五十蓍草法"

    def generate_lines(
        self,
        *,
        interactive: bool = True,
        input_func: Callable[[str], str] = _default_input,
        sleep_func: Callable[[float], None] = _default_sleep,
        now_func: Callable[[], datetime] = _default_now,
        manual_lines: Optional[Iterable[int]] = None,
    ) -> List[int]:
        if interactive:
            print("\n您选择了五十蓍草法占卜。")
            sleep_func(1)
        return [self._calculate_line() for _ in range(6)]

    @staticmethod
    def _calculate_line(rng: Optional[random.Random] = None) -> int:
        rng = rng or random
        total_sticks = 49 - 1
        counts = []
        for _ in range(3):
            left = rng.randint(1, total_sticks - 1)
            right = total_sticks - left - 1
            left_remain = left % 4 or 4
            right_remain = right % 4 or 4
            total_remainder = left_remain + right_remain + 1
            total_sticks -= total_remainder
            counts.append(total_remainder)
        many_count = sum(1 for count in counts if count >= 8)
        return {0: 9, 1: 7, 2: 8, 3: 6}.get(many_count, 7)


@dataclass(slots=True)
class CoinMethod:
    key: str = "c"
    name: str = "三枚铜钱法"

    def generate_lines(
        self,
        *,
        interactive: bool = True,
        input_func: Callable[[str], str] = _default_input,
        sleep_func: Callable[[float], None] = _default_sleep,
        now_func: Callable[[], datetime] = _default_now,
        manual_lines: Optional[Iterable[int]] = None,
    ) -> List[int]:
        if interactive:
            print("\n您选择了三枚铜钱法占卜。")
            sleep_func(1)
        return [self._throw_coins() for _ in range(6)]

    @staticmethod
    def _throw_coins(rng: Optional[random.Random] = None) -> int:
        rng = rng or random
        tosses = [rng.choice([2, 3]) for _ in range(3)]
        line_value = sum(tosses)
        return {6: 6, 7: 7, 8: 8, 9: 9}.get(line_value, 7)


@dataclass(slots=True)
class MeihuaMethod:
    key: str = "m"
    name: str = "梅花易数法"

    def generate_lines(
        self,
        *,
        interactive: bool = True,
        input_func: Callable[[str], str] = _default_input,
        sleep_func: Callable[[float], None] = _default_sleep,
        now_func: Callable[[], datetime] = _default_now,
        manual_lines: Optional[Iterable[int]] = None,
    ) -> List[int]:
        if interactive:
            print("\n您选择了梅花易数法占卜。")
            print("注意：数字卦只可以用较简单的小事，不可以用与人生大事。")
            use_numbers = input_func("\n是否要使用三个三位数数字？(y/n): ").lower().strip()
            if use_numbers == "y":
                numbers = self._get_three_numbers(input_func)
                lower_gua, upper_gua, changing_line = self._calculate_from_numbers(numbers)
                time_choice = input_func(
                    "\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': "
                ).strip()
                if time_choice == "2":
                    # Re-use manual time entry for CLI, fallback to now on failure
                    from iching.core.time_utils import get_user_time_input

                    current_time = get_user_time_input(input_func=input_func)
                else:
                    current_time = now_func()
            else:
                print("将使用当前年月日时分起卦。")
                current_time = now_func()
                lower_gua, upper_gua, changing_line = self._calculate_trigrams(current_time)
        else:
            current_time = now_func()
            lower_gua, upper_gua, changing_line = self._calculate_trigrams(current_time)
        return self._construct_hexagram(upper_gua, lower_gua, changing_line)

    @staticmethod
    def _get_three_numbers(input_func: Callable[[str], str]) -> List[int]:
        numbers: List[int] = []
        for index in range(1, 4):
            while True:
                raw = input_func(f"请输入第 {index} 个三位数数字 (100-999): ").strip()
                if raw.isdigit() and 100 <= int(raw) <= 999:
                    numbers.append(int(raw))
                    break
                print("无效输入。请输入一个100到999之间的三位数。")
        return numbers

    @staticmethod
    def _calculate_from_numbers(numbers: Iterable[int]) -> tuple[int, int, int]:
        items = list(numbers)
        lower = items[0] % 8 or 8
        upper = items[1] % 8 or 8
        changing_line = items[2] % 6 or 6
        return lower, upper, changing_line

    @staticmethod
    def _calculate_trigrams(dt: datetime) -> tuple[int, int, int]:
        lower = (dt.hour + dt.minute) % 8 or 8
        upper = (dt.month + dt.day) % 8 or 8
        total = dt.year + dt.month + dt.day + dt.hour + dt.minute
        changing_line = total % 6 or 6
        return lower, upper, changing_line

    @staticmethod
    def _construct_hexagram(upper: int, lower: int, changing_line: int) -> List[int]:
        trigrams = {
            1: "111",
            2: "011",
            3: "101",
            4: "001",
            5: "110",
            6: "010",
            7: "100",
            8: "000",
        }
        upper_binary = trigrams.get(upper, "000")
        lower_binary = trigrams.get(lower, "000")
        binary = upper_binary + lower_binary
        digits = [int(bit) for bit in binary]
        index = 6 - changing_line
        digits[index] ^= 1

        lines: List[int] = []
        for idx, digit in enumerate(digits):
            line = 7 if digit == 1 else 8
            if idx == index:
                line = 9 if digit == 1 else 6
            lines.append(line)
        return lines


@dataclass(slots=True)
class ManualInputMethod:
    key: str = "x"
    name: str = "手动输入"

    def generate_lines(
        self,
        *,
        interactive: bool = True,
        input_func: Callable[[str], str] = _default_input,
        sleep_func: Callable[[float], None] = _default_sleep,
        now_func: Callable[[], datetime] = _default_now,
        manual_lines: Optional[Iterable[int]] = None,
    ) -> List[int]:
        if interactive:
            while True:
                raw = input_func(
                    "请输入您的卦象 (格式为六个数字，每个数字为6到9，从下到上输入): "
                ).strip()
                if raw.isdigit() and len(raw) == 6 and all(ch in "6789" for ch in raw):
                    return [int(ch) for ch in raw]
                print("无效的卦象输入。请使用六位数字（范围为6到9）。")
        if manual_lines is None:
            raise ValueError("手动输入模式需要提供 manual_lines")
        values = list(manual_lines)
        if len(values) != 6 or any(v not in (6, 7, 8, 9) for v in values):
            raise ValueError("manual_lines 必须是六个介于 6-9 之间的整数")
        return values


AVAILABLE_METHODS: dict[str, DivinationMethod] = {
    method.key: method
    for method in [
        ShicaoMethod(),
        CoinMethod(),
        MeihuaMethod(),
        ManualInputMethod(),
    ]
}

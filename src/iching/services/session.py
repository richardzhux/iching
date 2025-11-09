from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from iching.config import AppConfig, PATHS, build_app_config
from iching.core.bazi import BaZiCalculator
from iching.core.divination import AVAILABLE_METHODS, DivinationMethod
from iching.core.hexagram import Hexagram, load_hexagram_definitions
from iching.core.time_utils import get_current_time
from iching.integrations.ai import DEFAULT_MODEL, MODEL_CAPABILITIES, analyze_session
from iching.integrations.najia.najia import Najia


def _default_input(prompt: str) -> str:
    return input(prompt)


def _normalize_list(value: Optional[Any], *, length: int = 6) -> List[str]:
    if isinstance(value, list):
        data = value[:]
    elif value is None:
        data = []
    else:
        data = list(value)
    if len(data) < length:
        data.extend([""] * (length - len(data)))
    return [str(item) if item is not None else "" for item in data[:length]]


def _build_najia_table(
    najia_data: Optional[Dict[str, Any]], line_overview: List[Dict[str, object]]
) -> Dict[str, object]:
    if not najia_data:
        return {"meta": {"main": None, "changed": None}, "rows": []}

    main_meta = najia_data.get("main") or {}
    changed_meta = najia_data.get("bian") or {}
    meta = {
        "main": {
            "name": main_meta.get("name") or najia_data.get("name"),
            "gong": main_meta.get("gong") or najia_data.get("gong"),
            "type": main_meta.get("type") or "",
        },
        "changed": None,
    }
    if changed_meta.get("name"):
        meta["changed"] = {
            "name": changed_meta.get("name"),
            "gong": changed_meta.get("gong"),
            "type": changed_meta.get("type") or "",
        }

    god6 = _normalize_list(najia_data.get("god6"))
    hidden = _normalize_list((najia_data.get("hide") or {}).get("qin6"))
    qin6 = _normalize_list(najia_data.get("qin6"))
    qinx = _normalize_list(najia_data.get("qinx"))
    shiy = _normalize_list(najia_data.get("shiy"))
    dyao = _normalize_list(najia_data.get("dyao"))
    main_marks = _normalize_list((najia_data.get("main") or {}).get("mark"))
    changed_qin6 = _normalize_list(changed_meta.get("qin6"))
    changed_marks = _normalize_list(changed_meta.get("mark"))

    overview = list(line_overview or [])
    if len(overview) < 6:
        overview.extend({} for _ in range(6 - len(overview)))

    rows: List[Dict[str, object]] = []
    for idx in range(6):
        source_idx = 5 - idx
        line_info = overview[idx] if idx < len(overview) else {}
        position = line_info.get("position", 6 - idx)
        line_type = line_info.get("line_type", "yang")
        changed_line_type = line_info.get("changed_line_type", line_type)
        is_moving = bool(line_info.get("is_moving"))
        moving_symbol = line_info.get("moving_symbol", "")

        rows.append(
            {
                "position": position,
                "line_type": line_type,
                "changed_line_type": changed_line_type,
                "is_moving": is_moving,
                "moving_symbol": moving_symbol,
                "god": god6[source_idx].strip(),
                "hidden": hidden[source_idx].strip(),
                "main_relation": f"{qin6[source_idx]}{qinx[source_idx]}".strip(),
                "main_mark": main_marks[source_idx],
                "marker": shiy[source_idx].strip(),
                "movement_tag": dyao[source_idx].strip(),
                "changed_relation": changed_qin6[source_idx].strip(),
                "changed_mark": changed_marks[source_idx],
            }
        )

    return {"meta": meta, "rows": rows}


@dataclass(slots=True)
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
    hex_sections: List[Dict[str, object]]
    hex_overview: Dict[str, object]
    najia_text: str
    najia_data: Dict[str, object]
    najia_table: Dict[str, object]
    ai_model: Optional[str]
    ai_reasoning: Optional[str]
    ai_verbosity: Optional[str]
    ai_tone: Optional[str]
    ai_analysis: Optional[str]
    full_text: str = field(repr=False)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload.pop("full_text", None)
        return payload


class SessionService:
    """Central orchestrator for running I Ching sessions."""

    TOPIC_MAP = {
        "1": "事业",
        "2": "感情",
        "3": "财运",
        "4": "身体健康",
        "5": "整体运势",
        "6": "其他/跳过",
        "q": "就地退出",
    }

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self.config = config or build_app_config()
        self.definitions = load_hexagram_definitions(self.config.paths.gua_index_file)
        self._history: List[SessionResult] = []

    @property
    def history(self) -> List[SessionResult]:
        return list(self._history)

    @property
    def methods(self) -> Dict[str, DivinationMethod]:
        return AVAILABLE_METHODS

    def run_console(
        self,
        *,
        input_func: Callable[[str], str] = _default_input,
        print_func: Callable[[str], None] = print,
        enable_ai: Optional[bool] = None,
    ) -> None:
        """Interactive CLI loop used by `iching5.py`."""
        from iching.core.system import display_system_usage
        from iching.services.logging import TeeLogger

        paths = self.config.paths
        enable_ai = self.config.enable_ai if enable_ai is None else enable_ai

        while True:
            output_dir = paths.archive_complete_dir
            with TeeLogger(output_dir) as logger:
                try:
                    print_func("\n欢迎使用理查德猪的易经占卜应用！")
                    print_func("\n请选择本次占卜主题：")
                    for key, label in self.TOPIC_MAP.items():
                        print_func(f"{key}. {label}")
                    topic_choice = self._get_valid_choice(
                        "\n请输入主题编号 (1-6): ",
                        choices=set(self.TOPIC_MAP.keys()),
                        input_func=input_func,
                        logger=logger,
                    )
                    topic = self.TOPIC_MAP[topic_choice]

                    specify_question = self._get_valid_choice(
                        "\n是否要输入一个具体问题？(y/n): ",
                        choices={"y", "n"},
                        input_func=input_func,
                        logger=logger,
                    )
                    user_question = None
                    if specify_question == "y":
                        user_question = input_func(
                            "\n请输入您的具体问题（按回车结束，或输入 'q' 退出）："
                        ).strip()
                        if user_question.lower() == "q":
                            print_func("\n感谢您使用易经占卜应用，再见！\n")
                            logger.output_dir = paths.archive_acquittal_dir
                            logger.save()
                            raise SystemExit(0)
                        if not user_question:
                            user_question = None

                    print_func(
                        "\n请选择占卜方法：\n"
                        "1. 五十蓍草法占卜 (输入 's')\n"
                        "2. 三枚铜钱法占卜 (输入 'c')\n"
                        "3. 梅花易数法占卜 (输入 'm')\n"
                        "4. 输入您自己的卦 (输入 'x')\n"
                        "r. 查看系统资源 (输入 'r')\n"
                        "q. 退出 (输入 'q')"
                    )
                    method_choice = self._get_valid_choice(
                        "\n您的选择: ",
                        choices=set(self.methods.keys()) | {"r"},
                        input_func=input_func,
                        logger=logger,
                    )
                    if method_choice == "r":
                        print_func(display_system_usage())
                        logger.output_dir = paths.archive_acquittal_dir
                        logger.save()
                        print_func("\n感谢您使用易经占卜应用，再见！\n")
                        raise SystemExit(0)

                    method = self.methods[method_choice]
                    manual_lines = None
                    if method.key == "x":
                        manual_lines = method.generate_lines(
                            interactive=True, input_func=input_func
                        )
                    lines = (
                        manual_lines
                        if manual_lines is not None
                        else method.generate_lines(interactive=True, input_func=input_func)
                    )

                    if method.key == "x":
                        time_choice = self._get_valid_choice(
                            "\n使用当前时间进行计算请输入 '1'，输入您自己的时间请输入 '2': ",
                            choices={"1", "2"},
                            input_func=input_func,
                            logger=logger,
                        )
                        if time_choice == "1":
                            current_time = get_current_time()
                        else:
                            from iching.core.time_utils import get_user_time_input

                            current_time = get_user_time_input(input_func=input_func)
                    else:
                        current_time = get_current_time()

                    result = self.create_session(
                        topic=topic,
                        user_question=user_question,
                        method_key=method.key,
                        lines_override=lines,
                        timestamp=current_time,
                        enable_ai=enable_ai,
                        interactive=True,
                        input_func=input_func,
                    )

                    print_func("\n起卦时间:")
                    print_func(result.current_time_str)
                    print_func(result.bazi_output)
                    print_func(result.elements_output)
                    print_func(result.hex_text)
                    print_func("\n【纳甲六亲、六神、动爻等详细信息】")
                    print_func(result.najia_text or "(无数据)")
                    if result.ai_analysis:
                        print_func("\nAI 分析结果:\n" + result.ai_analysis)

                    again = input_func(
                        "\n请问您是否要再次卜卦？(如继续，请输入'y'，任何其他视为退出): "
                    ).strip()
                    logger.save()
                    if again.lower() != "y":
                        print_func("\n感谢您使用易经占卜应用，再见！\n")
                        break
                except SystemExit:
                    raise
                except Exception as exc:
                    print_func(f"发生异常: {exc}")
                    logger.output_dir = paths.archive_acquittal_dir
                    logger.save()
                    break

    def create_session(
        self,
        *,
        topic: str,
        user_question: Optional[str],
        method_key: str,
        use_current_time: bool = True,
        timestamp: Optional[datetime] = None,
        manual_lines: Optional[List[int]] = None,
        lines_override: Optional[List[int]] = None,
        enable_ai: Optional[bool] = None,
        ai_model: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
        ai_verbosity: Optional[str] = None,
        ai_tone: Optional[str] = "normal",
        api_key: Optional[str] = None,
        interactive: bool = False,
        input_func: Callable[[str], str] = _default_input,
    ) -> SessionResult:
        method = self.methods.get(method_key)
        if method is None:
            raise ValueError(f"未知的占卜方法: {method_key}")

        if lines_override is not None:
            lines = lines_override
        else:
            lines = method.generate_lines(
                interactive=interactive,
                input_func=input_func,
                manual_lines=manual_lines,
            )

        if use_current_time or timestamp is None:
            timestamp = get_current_time()
        current_time_str = timestamp.strftime("%Y.%m.%d %H:%M")

        bazi_calculator = BaZiCalculator(timestamp)
        bazi_output, elements_output = bazi_calculator.calculate()

        hexagram = Hexagram(lines, self.definitions)
        hex_text, hex_sections, hex_overview = hexagram.to_text_package(
            guaci_path=self.config.paths.guaci_dir
        )

        params_map = {7: 1, 9: 4, 8: 0, 6: 3}
        params = [params_map.get(value, 0) for value in lines]
        date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        najia = Najia()
        najia.compile(params=params, date=date_str, title=topic or "", guaci=False)
        najia_text = najia.render().strip()

        ai_analysis_text = None
        tone_profile = ai_tone or "normal"
        should_use_ai = self.config.enable_ai if enable_ai is None else enable_ai
        model_hint = ai_model or self.config.preferred_ai_model or DEFAULT_MODEL
        capabilities = MODEL_CAPABILITIES.get(model_hint, MODEL_CAPABILITIES[DEFAULT_MODEL])

        allowed_reasoning = capabilities.get("reasoning", [])
        default_reasoning = capabilities.get("default_reasoning")
        if allowed_reasoning:
            if ai_reasoning in allowed_reasoning:
                reasoning_effort = ai_reasoning
            else:
                reasoning_effort = default_reasoning or allowed_reasoning[0]
        else:
            reasoning_effort = None

        supports_verbosity = bool(capabilities.get("verbosity"))
        if supports_verbosity:
            default_verbosity = capabilities.get("default_verbosity", "medium")
            if ai_verbosity in {"low", "medium", "high"}:
                verbosity_level = ai_verbosity
            else:
                verbosity_level = default_verbosity
        else:
            verbosity_level = None
        najia_table = _build_najia_table(najia.data, hex_overview.get("lines", []))

        if should_use_ai:
            session_payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "topic": topic,
                "user_question": user_question,
                "method": method.name,
                "lines": lines,
                "current_time_str": current_time_str,
                "bazi_output": bazi_output,
                "elements_output": elements_output,
                "hex_text": hex_text,
                "hex_sections": hex_sections,
                "hex_overview": hex_overview,
                "najia_data": dict(najia.data),
                "najia_text": najia_text,
                "najia_table": najia_table,
                "ai_analysis": None,
                "ai_model": model_hint,
                "ai_reasoning": reasoning_effort,
                "ai_verbosity": verbosity_level,
                "ai_tone": tone_profile,
            }
            ai_analysis_text = analyze_session(
                session_payload,
                api_key=api_key,
                model_hint=model_hint,
                interactive=interactive,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity_level,
                tone=tone_profile,
            )
            session_payload["ai_analysis"] = ai_analysis_text
        else:
            session_payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "topic": topic,
                "user_question": user_question,
                "method": method.name,
                "lines": lines,
                "current_time_str": current_time_str,
                "bazi_output": bazi_output,
                "elements_output": elements_output,
                "hex_text": hex_text,
                "hex_sections": hex_sections,
                "hex_overview": hex_overview,
                "najia_data": dict(najia.data),
                "najia_text": najia_text,
                "najia_table": najia_table,
                "ai_analysis": None,
                "ai_model": model_hint,
                "ai_reasoning": reasoning_effort,
                "ai_verbosity": verbosity_level,
                "ai_tone": tone_profile,
            }

        chunks = [
            "起卦时间: " + current_time_str,
            bazi_output,
            elements_output,
            hex_text,
            "\n【纳甲六亲、六神、动爻等详细信息】",
            najia_text or "(无纳甲数据)",
        ]
        if ai_analysis_text:
            chunks.append("\n【AI 分析】\n" + ai_analysis_text)
        full_text = "\n".join(chunks)

        result = SessionResult(
            timestamp=session_payload["timestamp"],
            topic=topic,
            user_question=user_question,
            method=method.name,
            lines=lines,
            current_time_str=current_time_str,
            bazi_output=bazi_output,
            elements_output=elements_output,
            hex_text=hex_text,
            hex_sections=hex_sections,
            hex_overview=hex_overview,
            najia_text=najia_text,
            najia_data=session_payload["najia_data"],
            najia_table=najia_table,
            ai_model=session_payload.get("ai_model"),
            ai_reasoning=session_payload.get("ai_reasoning"),
            ai_verbosity=session_payload.get("ai_verbosity"),
            ai_tone=session_payload.get("ai_tone"),
            ai_analysis=ai_analysis_text,
            full_text=full_text,
        )
        self._history.append(result)
        return result

    def _get_valid_choice(
        self,
        prompt: str,
        *,
        choices: set[str],
        input_func: Callable[[str], str],
        logger=None,
    ) -> str:
        quit_char = "q"
        valid_choices = {choice.lower() for choice in choices} | {quit_char}
        while True:
            answer = input_func(prompt).strip().lower()
            if answer == quit_char:
                print("\n感谢您使用易经占卜应用，再见！\n")
                if logger:
                    from iching.services.logging import TeeLogger

                    if isinstance(logger, TeeLogger):
                        logger.output_dir = self.config.paths.archive_acquittal_dir
                        logger.save()
                raise SystemExit(0)
            if answer in valid_choices:
                return answer
            print("输入无效，请重新输入。")

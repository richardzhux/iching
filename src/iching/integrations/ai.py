from __future__ import annotations

from copy import deepcopy
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, Optional

from iching.core.najia import derive_six_gods, rebase_relation
from iching.integrations.ai_budget import AICallBudget, get_ai_budget
from iching.integrations.reading_format import (
    LANGUAGE_RULE,
    build_system_prompt,
    normalize_locale,
)

from openai import BadRequestError, OpenAI

MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "gpt-5.6-terra": {
        "label": "GPT-5.6 Terra",
        "tier": "standard",
        "description": "默认模型，平衡判断质量、速度与成本。",
        "reasoning": ["none", "low", "medium", "high", "xhigh", "max"],
        "default_reasoning": "medium",
        "verbosity": True,
        "default_verbosity": "medium",
    },
    "gpt-5.6-sol": {
        "label": "GPT-5.6 Sol",
        "tier": "deep",
        "description": "深度占断与复杂连续追问。",
        "reasoning": ["none", "low", "medium", "high", "xhigh", "max"],
        "default_reasoning": "high",
        "verbosity": True,
        "default_verbosity": "medium",
    },
    "gpt-5.5": {
        "label": "GPT-5.5",
        "tier": "more",
        "description": "保留的上一代通用深度模型。",
        "reasoning": ["none", "low", "medium", "high", "xhigh"],
        "default_reasoning": "medium",
        "verbosity": True,
        "default_verbosity": "medium",
    },
    "gpt-5.3-codex": {
        "label": "GPT-5.3 Codex",
        "tier": "expert",
        "description": "结构化、技术性或执行方案追问。",
        "reasoning": ["minimal", "low", "medium", "high"],
        "default_reasoning": "medium",
        "verbosity": True,
        "default_verbosity": "medium",
    },
    "gpt-4.1": {
        "label": "GPT-4.1",
        "tier": "fast",
        "description": "轻量追问与快速验证。",
        "reasoning": [],
        "default_reasoning": None,
        "verbosity": False,
        "default_verbosity": None,
    },
}

MODEL_ALIASES: Dict[str, str] = {
    "gpt-5.1": "gpt-5.5",
    "gpt-5.2": "gpt-5.5",
    "gpt-5-mini": "gpt-5.6-terra",
    "gpt-5.4-mini": "gpt-5.6-terra",
    "gpt-5.5-mini": "gpt-5.6-terra",
    "gpt-5.6": "gpt-5.6-sol",
}

DEFAULT_MODEL = "gpt-5.6-terra"

TONE_PROFILES: Dict[str, str] = {
    "normal": "现代中文，温和且专业，适度引用经典，保持礼貌敬语。",
    "wenyan": "仿庄子等战国文士，遣词古雅但需可读。",
    "modern": "口语直白、短句表达、亲近但不油腻，优先给清晰结论。",
    "academic": "学术期刊口吻，逻辑严密，引用充分。",
}


#: Kept as the Chinese rendering so existing callers and stored prompts
#: keep working; new call sites pass a locale to :func:`build_system_prompt`.
SYSTEM_PROMPT_PRO = build_system_prompt("zh")


def _normalized_najia_for_ai(data: Dict[str, Any]) -> Any:
    najia_table = data.get("najia_table")
    if isinstance(najia_table, dict) and isinstance(najia_table.get("rows"), list):
        return najia_table
    legacy = data.get("najia_data")
    if not isinstance(legacy, dict):
        return None

    sanitized = deepcopy(legacy)
    sanitized.pop("block_text", None)
    gods = derive_six_gods(sanitized.get("day_stem"))
    main = sanitized.get("main")
    changed = sanitized.get("changed")
    main_palace = ""
    if isinstance(main, dict):
        main_palace = str(main.get("palace") or main.get("gong") or "")

    for entry, is_changed in ((main, False), (changed, True)):
        if not isinstance(entry, dict):
            continue
        lines = entry.get("lines")
        if not isinstance(lines, list):
            continue
        for line in lines:
            if not isinstance(line, dict):
                continue
            raw_position = line.get("position", line.get("position_top"))
            try:
                position = int(raw_position)
            except (TypeError, ValueError):
                position = 0
            line["god"] = gods[position - 1] if 1 <= position <= 6 else ""
            if is_changed:
                line["hidden"] = ""
                relation = line.get("relation")
                if main_palace and isinstance(relation, str):
                    try:
                        line["relation"] = rebase_relation(relation, main_palace)
                    except ValueError:
                        pass
    return sanitized


def _line_selection_line(data: Dict[str, Any]) -> Optional[str]:
    """Hand the model the resolved 取用 rule instead of making it re-derive one."""
    overview = data.get("hex_overview")
    selection = overview.get("line_selection") if isinstance(overview, dict) else None
    if not isinstance(selection, dict):
        return None
    name = str(selection.get("rule_name") or "")
    detail = str(selection.get("rule_detail") or "")
    if not name:
        return None
    text = f"取用(Line selection): {name} · {detail}"
    primary = selection.get("primary_line")
    if primary is not None:
        text += f"；主爻第{primary}爻（{selection.get('line_role') or ''}）"
        secondary = selection.get("secondary_lines") or []
        if secondary:
            text += "，并参第" + "、".join(str(item) for item in secondary) + "爻"
    return text


def _classical_sections_block(data: Dict[str, Any], *, limit: int = 8) -> Optional[str]:
    """The classical passages this reading actually selected.

    ``hex_text`` carries only the ``guaci`` slot, so Takashima — integrated at
    the line-slot level and shown to the reader — never reached the model. Send
    the sections the 取用 rule marked visible, primary first, bounded so the
    input budget stays predictable.
    """
    sections = data.get("hex_sections")
    if not isinstance(sections, list):
        return None
    rank = {"primary": 0, "secondary": 1, "background": 2}
    chosen = [
        item
        for item in sections
        if isinstance(item, dict)
        and item.get("visible_by_default")
        and item.get("content")
        and item.get("source") != "guaci"  # already in hex_text
    ]
    chosen.sort(key=lambda item: rank.get(str(item.get("line_role") or "background"), 3))
    if not chosen:
        return None
    blocks = []
    for item in chosen[:limit]:
        title = str(item.get("title") or item.get("slot_key") or "")
        label = str(item.get("source_label") or item.get("source") or "")
        content = str(item.get("content") or "").strip()
        if len(content) > 1800:
            content = content[:1800].rstrip() + "…"
        blocks.append(f"【{label}｜{title}】\n{content}")
    return "本次取用的其他经典文本（高岛易断等）:\n" + "\n\n".join(blocks)


def _build_prompt(data: Dict[str, Any]) -> str:
    locale = normalize_locale(data.get("locale"))
    blocks = []
    if topic := data.get("topic"):
        blocks.append(f"本次占卜主题: {topic}")
    if question := data.get("user_question"):
        blocks.append(f"具体问题: {question}")
    if context := data.get("user_context"):
        blocks.append(f"用户补充背景: {context}")
    if current_time := data.get("current_time_str"):
        blocks.append(f"起卦时间: {current_time}")
    if lines := data.get("lines"):
        blocks.append(f"爻值(自下而上，6=老阴,7=少阳,8=少阴,9=老阳): {lines}")
    if selection_line := _line_selection_line(data):
        blocks.append(selection_line)
    if bazi := data.get("bazi_output"):
        blocks.append("八字计算:\n" + str(bazi))
    if elements := data.get("elements_output"):
        blocks.append("五行分析:\n" + str(elements))
    if text := data.get("hex_text"):
        blocks.append("卦辞解释（含本卦/变卦/错/综/互 + guaci）:\n" + str(text))
    if classical := _classical_sections_block(data):
        blocks.append(classical)
    najia_data = _normalized_najia_for_ai(data)
    if najia_data:
        try:
            blocks.append(
                "纳甲六亲/六神/动爻（JSON）:\n"
                + json.dumps(najia_data, ensure_ascii=False, indent=2)
            )
        except Exception:
            blocks.append("纳甲六亲/六神/动爻（原始）:\n" + str(najia_data))

    reasoning = data.get("ai_reasoning")
    reasoning_note = ""
    if reasoning == "none":
        reasoning_note = "推理力度: 关闭。跳过链式推理以换取更快响应。"
    elif reasoning == "minimal":
        reasoning_note = "推理力度: 极简。聚焦关键依据与结论，压缩篇幅，避免重复。"
    elif reasoning == "low":
        reasoning_note = "推理力度: 低。给出主要推理链条，保留必要的解释，但保持简洁。"
    elif reasoning == "medium":
        reasoning_note = "推理力度: 中。完整展示核心推演步骤与支撑证据，适度展开。"
    elif reasoning == "high":
        reasoning_note = "推理力度: 高。详尽阐述推理过程、备选解释与权衡，同时给出清晰结构。"
    elif reasoning == "xhigh":
        reasoning_note = "推理力度: 超高。充分检查复杂关系、备选解释与反证后再收束结论。"
    elif reasoning == "max":
        reasoning_note = "推理力度: 最大。优先完整性与严密性，穷尽关键分支后给出最终判断。"

    verbosity = data.get("ai_verbosity")
    verbosity_note = ""
    if verbosity == "low":
        verbosity_note = "输出篇幅: 简洁。以要点式段落呈现，避免冗长。"
    elif verbosity == "medium":
        verbosity_note = "输出篇幅: 适中。保持结构完整与适度细节。"
    elif verbosity == "high":
        verbosity_note = "输出篇幅: 详尽。充分展开背景、推理与建议。"

    blocks.append(
        "Follow the fixed output structure in the system instructions exactly: "
        "the conclusion first, then the evidence chain and the actionable steps."
        if locale == "en"
        else "请严格遵循系统中的固定输出结构，先给明确结论，再给证据短链与可执行动作。"
    )
    blocks.append(
        "Write the entire answer in English."
        if locale == "en"
        else "全文使用简体中文作答。"
    )
    if reasoning_note:
        blocks.append(reasoning_note)
    if verbosity_note:
        blocks.append(verbosity_note)
    tone = data.get("ai_tone")
    if tone:
        descriptor = TONE_PROFILES.get(tone, "用户自定义语气")
        blocks.append(f"语气设定: {tone} —— {descriptor}")
    return "\n\n".join(blocks)


def build_chat_prompt(locale: Optional[str] = None) -> str:
    """Instructions for a follow-up turn.

    The initial reading's eight-section template used to be appended verbatim,
    so "what about next month?" was told to emit a full formal reading complete
    with 继续追问 and 最终判断. A follow-up answers the question asked and only
    reaches for the full structure when the reader asks for another full pass.
    """
    resolved = normalize_locale(locale)
    if resolved == "en":
        return (
            "You are continuing a single, already-completed I Ching reading. Do not recast or "
            "change the hexagram. Ground every answer in the hexagram, the classical text and the "
            "payload from the initial analysis, and in your own earlier explanation in this thread. "
            "Treat each message as a follow-up about the same situation; if the reader wanders to an "
            "unrelated topic, steer gently back to this reading.\n\n"
            "Answer the question that was asked, at its own length. Do not reproduce the full "
            "eight-section reading structure unless the reader explicitly asks for another complete "
            "reading. Keep a clear position, cite the line or text you are relying on, and say "
            "plainly when the data does not settle the question.\n\n"
            + LANGUAGE_RULE["en"]
        )
    return (
        "你正在继续一次已经完成的占断。不要重新起卦或改变卦象。"
        "所有回答都要依据该卦象、经典文本、初次分析的会话数据，以及你在本轮对话中已经给出的解释。"
        "把每条消息都当作同一件事的追问；如果用户跑题，温和地带回本卦。\n\n"
        "只回答被问到的问题，长度随问题而定。除非用户明确要求再做一次完整解读，"
        "否则不要重复输出完整的八段结构。保持明确立场，指明所依据的爻位或原文，"
        "数据不足时直说。\n\n"
        + LANGUAGE_RULE["zh"]
    )


CHAT_CONTINUATION_PROMPT = build_chat_prompt("zh")


@dataclass(slots=True)
class AIResponseData:
    text: str
    response_id: Optional[str]
    usage: Optional[Dict[str, int]]


def _prompt_for_password() -> None:
    password = os.getenv("OPENAI_PW")
    if not password:
        return
    for _ in range(3):
        user_input = input("\n请输入OPENAI API密码：").strip()
        if user_input == password:
            return
        print("密码错误，请重新输入。")
    print("连续三次密码错误，程序退出。")
    raise PermissionError("OPENAI_PW 验证失败")


def _interactive_model_selector() -> str:
    options = [
        ("A", "gpt-5.6-terra", "标准占断（默认）"),
        ("B", "gpt-5.6-sol", "深度占断"),
        ("C", "gpt-5.5", "上一代通用模型"),
        ("D", "gpt-5.3-codex", "结构化与技术推理"),
        ("E", "gpt-4.1", "快速模式"),
    ]
    print(f"\n请选择OpenAI模型（默认：{DEFAULT_MODEL}）：")
    for letter, model, desc in options:
        print(f"  [{letter}] {model.ljust(12)} —— {desc}")
    choice = input("请尊贵的用户选择：").strip().upper()
    mapping = {
        "": DEFAULT_MODEL,
        "A": "gpt-5.6-terra",
        "B": "gpt-5.6-sol",
        "C": "gpt-5.5",
        "D": "gpt-5.3-codex",
        "E": "gpt-4.1",
    }
    selected = mapping.get(choice)
    if selected:
        return selected
    print(f"警告：输入无效，已自动使用默认模型 {DEFAULT_MODEL}。")
    return DEFAULT_MODEL


def normalize_model_name(model_name: Optional[str]) -> Optional[str]:
    if model_name is None:
        return None
    return MODEL_ALIASES.get(model_name, model_name)


def start_analysis(
    data: Dict[str, Any],
    *,
    api_key: Optional[str] = None,
    model_hint: Optional[str] = None,
    interactive: bool = True,
    password_provider: Optional[Callable[[], None]] = None,
    model_selector: Optional[Callable[[], str]] = None,
    reasoning_effort: Optional[str] = None,
    verbosity: Optional[str] = None,
    tone: Optional[str] = None,
    locale: Optional[str] = None,
) -> Optional[AIResponseData]:
    if not interactive:
        # Non-interactive callers are responsible for pre-validating access.
        include_password_gate = False
    else:
        include_password_gate = True

    if include_password_gate:
        (password_provider or _prompt_for_password)()

    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if interactive:
            print("OPENAI_API_KEY not set. 请在环境变量或 .env 中配置。")
        return None

    if tone and not data.get("ai_tone"):
        data["ai_tone"] = tone
    resolved_locale = normalize_locale(locale or data.get("locale"))
    data["locale"] = resolved_locale

    choose_model = model_selector or _interactive_model_selector
    model_name = normalize_model_name(model_hint or (choose_model() if interactive else DEFAULT_MODEL))

    selected_reasoning = _normalize_reasoning(model_name, reasoning_effort or data.get("ai_reasoning"))
    selected_verbosity = _normalize_verbosity(model_name, verbosity or data.get("ai_verbosity"))
    reasoning_payload = selected_reasoning

    client = OpenAI(api_key=api_key, timeout=120.0, max_retries=0)
    user_prompt = _build_prompt(data)
    response = _request_openai_response(
        client=client,
        model_name=model_name,
        instructions=build_system_prompt(resolved_locale).strip(),
        user_input=user_prompt,
        reasoning=reasoning_payload,
        verbosity=selected_verbosity,
    )
    if response is None:
        return None
    text = _extract_response_text(response)
    if not text:
        return None
    usage = _extract_usage(response)
    return AIResponseData(
        text=text,
        response_id=_response_field(response, "id"),
        usage=usage,
    )


def continue_analysis(
    *,
    previous_response_id: str,
    message: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    verbosity: Optional[str] = None,
    tone: Optional[str] = None,
    locale: Optional[str] = None,
) -> AIResponseData:
    if not previous_response_id:
        raise ValueError("previous_response_id is required for follow-up calls.")

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured on the server.")

    resolved_model = normalize_model_name(model_name) or DEFAULT_MODEL
    selected_reasoning = _normalize_reasoning(resolved_model, reasoning_effort)
    selected_verbosity = _normalize_verbosity(resolved_model, verbosity)
    reasoning_payload = selected_reasoning

    instruction_block = build_chat_prompt(locale)
    if tone:
        descriptor = TONE_PROFILES.get(tone, "用户自定义语气")
        instruction_block += f"\n\n语气设定: {tone} —— {descriptor}"

    client = OpenAI(api_key=api_key, timeout=120.0, max_retries=0)
    response = _request_openai_response(
        client=client,
        model_name=resolved_model,
        instructions=instruction_block,
        user_input=message,
        reasoning=reasoning_payload,
        verbosity=selected_verbosity,
        previous_response_id=previous_response_id,
    )
    if response is None:
        raise RuntimeError("OpenAI follow-up call failed to produce a response.")

    text = _extract_response_text(response)
    if not text:
        raise RuntimeError("OpenAI follow-up call returned an empty response.")

    usage = _extract_usage(response)
    return AIResponseData(
        text=text,
        response_id=_response_field(response, "id"),
        usage=usage,
    )


def continue_analysis_from_session(
    *,
    session_data: Dict[str, Any],
    message: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    verbosity: Optional[str] = None,
    tone: Optional[str] = None,
    locale: Optional[str] = None,
) -> AIResponseData:
    stripped = message.strip()
    if not stripped:
        raise ValueError("message is required for bootstrap follow-up calls.")

    context = _build_followup_session_context(session_data)
    if not context:
        raise ValueError("session_data is missing required context for bootstrap follow-up.")

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured on the server.")

    resolved_model = normalize_model_name(model_name) or DEFAULT_MODEL
    selected_reasoning = _normalize_reasoning(resolved_model, reasoning_effort)
    selected_verbosity = _normalize_verbosity(resolved_model, verbosity)
    reasoning_payload = selected_reasoning

    instruction_block = build_chat_prompt(locale)
    if tone:
        descriptor = TONE_PROFILES.get(tone, "用户自定义语气")
        instruction_block += f"\n\n语气设定: {tone} —— {descriptor}"

    user_input = (
        "以下是同一会话的固定占卜上下文，请据此回答用户追问，不要重起卦：\n\n"
        f"{context}\n\n"
        f"用户追问：{stripped}"
    )

    client = OpenAI(api_key=api_key, timeout=120.0, max_retries=0)
    response = _request_openai_response(
        client=client,
        model_name=resolved_model,
        instructions=instruction_block,
        user_input=user_input,
        reasoning=reasoning_payload,
        verbosity=selected_verbosity,
    )
    if response is None:
        raise RuntimeError("OpenAI bootstrap follow-up call failed to produce a response.")

    text = _extract_response_text(response)
    if not text:
        raise RuntimeError("OpenAI bootstrap follow-up call returned an empty response.")

    usage = _extract_usage(response)
    return AIResponseData(
        text=text,
        response_id=_response_field(response, "id"),
        usage=usage,
    )


def stream_continue_analysis(
    *,
    previous_response_id: str,
    message: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    verbosity: Optional[str] = None,
    tone: Optional[str] = None,
    locale: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    if not previous_response_id:
        raise ValueError("previous_response_id is required for follow-up calls.")
    return _stream_analysis(
        user_input=message,
        previous_response_id=previous_response_id,
        api_key=api_key,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
        tone=tone,
        locale=locale,
    )


def stream_continue_analysis_from_session(
    *,
    session_data: Dict[str, Any],
    message: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    verbosity: Optional[str] = None,
    tone: Optional[str] = None,
    locale: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    stripped = message.strip()
    if not stripped:
        raise ValueError("message is required for bootstrap follow-up calls.")
    context = _build_followup_session_context(session_data)
    if not context:
        raise ValueError("session_data is missing required context for bootstrap follow-up.")
    user_input = (
        "以下是同一会话的固定占卜上下文，请据此回答用户追问，不要重起卦：\n\n"
        f"{context}\n\n用户追问：{stripped}"
    )
    return _stream_analysis(
        user_input=user_input,
        previous_response_id=None,
        api_key=api_key,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
        tone=tone,
        locale=locale,
    )


def _stream_analysis(
    *,
    user_input: str,
    previous_response_id: Optional[str],
    api_key: Optional[str],
    model_name: Optional[str],
    reasoning_effort: Optional[str],
    verbosity: Optional[str],
    tone: Optional[str],
    locale: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured on the server.")

    resolved_model = normalize_model_name(model_name) or DEFAULT_MODEL
    selected_reasoning = _normalize_reasoning(resolved_model, reasoning_effort)
    selected_verbosity = _normalize_verbosity(resolved_model, verbosity)
    instructions = build_chat_prompt(locale)
    if tone:
        descriptor = TONE_PROFILES.get(tone, "用户自定义语气")
        instructions += f"\n\n语气设定: {tone} —— {descriptor}"

    payload: Dict[str, Any] = {
        "model": resolved_model,
        "instructions": instructions.strip(),
        "input": [{"role": "user", "content": user_input}],
        "stream": True,
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id
    if selected_reasoning:
        payload["reasoning"] = _reasoning_payload(resolved_model, selected_reasoning)
    if selected_verbosity:
        payload["text"] = {"verbosity": selected_verbosity}

    client = OpenAI(api_key=resolved_api_key, timeout=120.0, max_retries=0)

    def generate() -> Iterator[Dict[str, Any]]:
        budget = get_ai_budget()
        _validate_input_budget(instructions.strip(), user_input, budget)
        payload["max_output_tokens"] = budget.max_output_tokens
        completed_response: Any = None
        parts: list[str] = []
        already_dispatched = budget.dispatched
        budget.dispatched = True
        try:
            with client.responses.create(**payload) as stream:
                for event in stream:
                    event_type = _response_field(event, "type", "")
                    if event_type == "response.output_text.delta":
                        delta = _response_field(event, "delta", "") or ""
                        if delta:
                            parts.append(delta)
                            yield {"type": "delta", "delta": delta}
                    elif event_type in {"response.completed", "response.incomplete", "response.failed"}:
                        completed_response = _response_field(event, "response")
                        _record_budget_response(completed_response, budget)
                        if event_type == "response.failed":
                            raise RuntimeError("OpenAI streaming response failed.")
                    elif event_type == "error":
                        raise RuntimeError("OpenAI streaming response failed.")
        except Exception as exc:
            _mark_known_rejection(exc, budget, already_dispatched)
            raise

        if completed_response is None or budget.usage is None:
            raise RuntimeError("OpenAI streaming response ended without terminal usage accounting.")
        text = "".join(parts).strip()
        if not text:
            text = _extract_response_text(completed_response) or ""
        if not text:
            raise RuntimeError("OpenAI streaming follow-up returned an empty response.")
        result = AIResponseData(
            text=text,
            response_id=budget.response_id,
            usage=budget.usage,
        )
        yield {"type": "result", "result": result}

    return generate()


def _build_followup_session_context(data: Dict[str, Any]) -> str:
    if not isinstance(data, dict):
        return ""
    blocks: list[str] = []
    if topic := data.get("topic"):
        blocks.append(f"主题: {topic}")
    if question := data.get("user_question"):
        blocks.append(f"原问题: {question}")
    if current_time := data.get("current_time_str"):
        blocks.append(f"起卦时间: {current_time}")
    if method := data.get("method"):
        blocks.append(f"起卦方法: {method}")
    if lines := data.get("lines"):
        blocks.append(f"六爻(自下而上): {lines}")
    if bazi := data.get("bazi_output"):
        blocks.append("八字:\n" + str(bazi))
    if elements := data.get("elements_output"):
        blocks.append("五行:\n" + str(elements))
    if hex_text := data.get("hex_text"):
        blocks.append("卦象与卦辞:\n" + str(hex_text))
    if classical := _classical_sections_block(data, limit=4):
        blocks.append(classical)
    najia_data = _normalized_najia_for_ai(data)
    if najia_data:
        try:
            blocks.append("纳甲/六神/六亲:\n" + json.dumps(najia_data, ensure_ascii=False, indent=2))
        except Exception:
            blocks.append("纳甲/六神/六亲:\n" + str(najia_data))
    if ai_analysis := data.get("ai_analysis"):
        blocks.append("已有 AI 解读（仅作参考）:\n" + str(ai_analysis))
    history = data.get("conversation_history")
    if isinstance(history, list) and history:
        rendered_history = []
        for item in history[-20:]:
            if not isinstance(item, dict):
                continue
            role = "用户" if item.get("role") == "user" else "AI"
            content = str(item.get("content") or "").strip()
            if content:
                rendered_history.append(f"{role}: {content}")
        if rendered_history:
            blocks.append("已有追问对话：\n" + "\n\n".join(rendered_history))
    return "\n\n".join(blocks).strip()


def _validate_input_budget(instructions: str, user_input: str, budget: AICallBudget) -> None:
    if len(instructions.encode("utf-8")) + len(user_input.encode("utf-8")) > budget.max_input_bytes:
        raise ValueError("AI 上下文过长，请缩短补充背景或开始新的解读。")


def _record_budget_response(response: Any, budget: AICallBudget) -> None:
    if usage := _extract_usage(response):
        budget.usage = usage
    if response_id := _response_field(response, "id"):
        budget.response_id = response_id


def _response_field(value: Any, key: str, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def _mark_known_rejection(exc: Exception, budget: AICallBudget, already_dispatched: bool) -> None:
    if (getattr(exc, "status_code", None) in {400, 401, 403, 404, 422}
            and not already_dispatched and budget.usage is None and budget.response_id is None):
        budget.dispatched = False


def _create_bounded_response(client, payload, budget: AICallBudget):
    already_dispatched = budget.dispatched
    budget.dispatched = True
    try:
        response = client.responses.create(**payload)
    except Exception as exc:
        _mark_known_rejection(exc, budget, already_dispatched)
        raise
    _record_budget_response(response, budget)
    if _response_field(response, "status") == "failed":
        raise RuntimeError("OpenAI response failed.")
    if budget.usage is None:
        raise RuntimeError("OpenAI response ended without usage accounting.")
    return response


def _request_openai_response(
    *,
    client: OpenAI,
    model_name: str,
    instructions: str,
    user_input: str,
    reasoning: Optional[str],
    verbosity: Optional[str],
    previous_response_id: Optional[str] = None,
):
    budget = get_ai_budget()
    _validate_input_budget(instructions.strip(), user_input, budget)

    def build_payload(use_reasoning: bool, use_verbosity: bool) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model_name,
            "max_output_tokens": budget.max_output_tokens,
            "instructions": instructions.strip(),
            "input": [
                {
                    "role": "user",
                    "content": user_input,
                }
            ],
        }
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        if use_reasoning and reasoning:
            payload["reasoning"] = _reasoning_payload(model_name, reasoning)
        if use_verbosity and verbosity:
            payload["text"] = {"verbosity": verbosity}
        return payload

    use_reasoning = bool(reasoning)
    use_verbosity = bool(verbosity)

    try:
        return _create_bounded_response(client, build_payload(use_reasoning, use_verbosity), budget)
    except BadRequestError as exc:
        error_text = str(exc).lower()
        retried = False
        if use_reasoning and "reasoning" in error_text:
            use_reasoning = False
            try:
                response = _create_bounded_response(client, build_payload(use_reasoning, use_verbosity), budget)
                retried = True
            except BadRequestError as inner_exc:
                error_text = str(inner_exc).lower()
                if use_verbosity and ("text" in error_text or "verbosity" in error_text):
                    use_verbosity = False
                    response = _create_bounded_response(client, build_payload(use_reasoning, use_verbosity), budget)
                    retried = True
                else:
                    raise
        if not retried:
            if use_verbosity and ("text" in error_text or "verbosity" in error_text):
                use_verbosity = False
                try:
                    return _create_bounded_response(client, build_payload(use_reasoning, use_verbosity), budget)
                except BadRequestError as inner_exc:
                    error_text = str(inner_exc).lower()
                    if use_reasoning and "reasoning" in error_text:
                        use_reasoning = False
                        return _create_bounded_response(client, build_payload(use_reasoning, use_verbosity), budget)
                    raise
            raise
        return response


def _extract_response_text(response: Any) -> Optional[str]:
    if text := _response_field(response, "output_text"):
        return text.strip()
    chunks: list[str] = []
    for item in _response_field(response, "output", []) or []:
        contents = _response_field(item, "content", []) or []
        for part in contents:
            if isinstance(part, dict):
                text = part.get("text")
            else:
                text = getattr(part, "text", None)
            if text:
                chunks.append(text)
    combined = "".join(chunks).strip()
    return combined or None


def _extract_usage(response: Any) -> Optional[Dict[str, int]]:
    usage = _response_field(response, "usage")
    if usage is None:
        return None
    usage_dict: Dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, key, None)
        if value is None and isinstance(usage, dict):
            value = usage.get(key)
        if value is not None:
            usage_dict[key] = int(value)
    if any(value < 0 for value in usage_dict.values()):
        return None
    if "total_tokens" not in usage_dict:
        if not {"input_tokens", "output_tokens"} <= usage_dict.keys():
            return None
        usage_dict["total_tokens"] = usage_dict["input_tokens"] + usage_dict["output_tokens"]
    return usage_dict


def _normalize_reasoning(model_name: str, requested: Optional[str]) -> Optional[str]:
    normalized_model = normalize_model_name(model_name) or DEFAULT_MODEL
    meta = MODEL_CAPABILITIES.get(normalized_model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    allowed = meta.get("reasoning", [])
    if not allowed:
        return None
    if requested in allowed:
        return requested
    default_reasoning = meta.get("default_reasoning")
    if default_reasoning in allowed:
        return default_reasoning
    return allowed[0]


def _reasoning_payload(model_name: str, effort: str) -> Dict[str, str]:
    payload = {"effort": effort}
    if (normalize_model_name(model_name) or model_name).startswith("gpt-5.6"):
        payload["context"] = "all_turns"
    return payload


def _normalize_verbosity(model_name: str, requested: Optional[str]) -> Optional[str]:
    normalized_model = normalize_model_name(model_name) or DEFAULT_MODEL
    meta = MODEL_CAPABILITIES.get(normalized_model, MODEL_CAPABILITIES[DEFAULT_MODEL])
    if not meta.get("verbosity"):
        return None
    if requested in {"low", "medium", "high"}:
        return requested
    default_verbosity = meta.get("default_verbosity")
    if default_verbosity in {"low", "medium", "high"}:
        return default_verbosity
    return "medium"


def analyze_session(
    data: Dict[str, Any],
    *,
    api_key: Optional[str] = None,
    model_hint: Optional[str] = None,
    interactive: bool = True,
    password_provider: Optional[Callable[[], None]] = None,
    model_selector: Optional[Callable[[], str]] = None,
    reasoning_effort: Optional[str] = None,
    verbosity: Optional[str] = None,
    tone: Optional[str] = None,
    locale: Optional[str] = None,
) -> Optional[str]:
    result = start_analysis(
        data,
        api_key=api_key,
        model_hint=model_hint,
        interactive=interactive,
        password_provider=password_provider,
        model_selector=model_selector,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
        tone=tone,
    )
    return result.text if result else None


# Backwards-compatible alias for legacy imports
def closeai(
    data: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Optional[str]:
    return analyze_session(data, api_key=api_key, interactive=True)

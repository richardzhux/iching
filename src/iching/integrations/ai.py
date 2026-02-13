from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from openai import BadRequestError, OpenAI

MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "gpt-4.1": {
        "reasoning": [],
        "default_reasoning": None,
        "verbosity": False,
        "default_verbosity": None,
    },
    "gpt-5.1": {
        "reasoning": ["none", "minimal", "low", "medium", "high"],
        "default_reasoning": "medium",
        "verbosity": True,
        "default_verbosity": "medium",
    },
    "gpt-5-mini": {
        "reasoning": ["minimal", "low", "medium", "high"],
        "default_reasoning": "medium",
        "verbosity": True,
        "default_verbosity": "medium",
    },
}

DEFAULT_MODEL = "gpt-5.1"

TONE_PROFILES: Dict[str, str] = {
    "normal": "现代中文，温和且专业，适度引用经典，保持礼貌敬语。",
    "wenyan": "仿庄子等战国文士，遣词古雅但需可读。",
    "modern": "口语直白、短句表达、亲近但不油腻，优先给清晰结论。",
    "academic": "学术期刊口吻，逻辑严密，引用充分。",
}


SYSTEM_PROMPT_PRO = """
你是资深《易》学占断顾问。目标是给出清晰、可验证、可执行的判断，优先让普通用户听得懂。

【硬性规则】
- 只依据输入会话数据推断；信息不足就明确写“信息不足”，不得编造。
- 保持明确立场，避免空泛套话与两头下注。
- 允许给出直接建议，避免冗余合规口吻。
- 不输出 JSON、代码块、表格或多级列表。
- 输出为简体中文 Markdown，只使用标题与顶层 `- ` 列表，禁止嵌套列表。

【核心推断方法】
1) 先判动爻并按动爻数量规则取主断：
   - 无动爻：取卦辞断（本卦为主，错/综/互参照）。
   - 一爻动：动爻爻辞为主，卦辞为辅。
   - 两爻动：一阴一阳取阴爻；同阴或同阳取上动爻。
   - 三爻动：取中间动爻。
   - 四爻动：在两静爻中取下静爻。
   - 五爻动：取唯一静爻。
   - 六爻全动：乾坤用“用九/用六”，其余取变卦卦辞。
2) 本卦为主，变/错/综/互为辅；互卦看过程，错综看反向牵制。
3) 结合纳甲、六亲、六神、世应、五行旺衰判断主客强弱、用忌与阻力来源。
4) 应期必须给主次窗口，并写明触发条件。

【输出结构（严格按顺序）】
# 一句话结论
- 一句话给出倾向（利成/延迟/不利）与核心原因。

# 给普通人的解释
- 1-2段，先说结果再说原因。
- 每段至少出现一句“换成大白话：...”。

# 证据短链
- 3-5条，每条必须使用：
  `- 结论：...｜依据：...｜白话：...`
- 依据必须来自动爻、卦辞/爻辞、纳甲/五行中的至少一项。

# 应期与条件
- `- 主应期：...｜条件：...｜置信度：...%`
- `- 次应期：...｜条件：...｜置信度：...%`
- 置信度必须绑定条件，不允许裸数字。

# 行动建议
- 给3条建议，每条都必须包含：
  `- 动作：...｜节奏：...｜观察指标：...`

# 风险与转折信号
- 给2-4条可观察信号，说明何时转强或转弱。

# 最终判断
- 用两句话收束：最终结论 + 下一步最重要动作。
"""


def _build_prompt(data: Dict[str, Any]) -> str:
    blocks = []
    if topic := data.get("topic"):
        blocks.append(f"本次占卜主题: {topic}")
    if question := data.get("user_question"):
        blocks.append(f"具体问题: {question}")
    if current_time := data.get("current_time_str"):
        blocks.append(f"起卦时间: {current_time}")
    if lines := data.get("lines"):
        blocks.append(f"爻值(自下而上，6=老阴,7=少阳,8=少阴,9=老阳): {lines}")
    if bazi := data.get("bazi_output"):
        blocks.append("八字计算:\n" + str(bazi))
    if elements := data.get("elements_output"):
        blocks.append("五行分析:\n" + str(elements))
    if text := data.get("hex_text"):
        blocks.append("卦辞解释（含本卦/变卦/错/综/互 + guaci）:\n" + str(text))
    najia_data = data.get("najia_data")
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

    verbosity = data.get("ai_verbosity")
    verbosity_note = ""
    if verbosity == "low":
        verbosity_note = "输出篇幅: 简洁。以要点式段落呈现，避免冗长。"
    elif verbosity == "medium":
        verbosity_note = "输出篇幅: 适中。保持结构完整与适度细节。"
    elif verbosity == "high":
        verbosity_note = "输出篇幅: 详尽。充分展开背景、推理与建议。"

    blocks.append("请严格遵循系统中的固定输出结构，先给明确结论，再给证据短链与可执行动作。")
    if reasoning_note:
        blocks.append(reasoning_note)
    if verbosity_note:
        blocks.append(verbosity_note)
    tone = data.get("ai_tone")
    if tone:
        descriptor = TONE_PROFILES.get(tone, "用户自定义语气")
        blocks.append(f"语气设定: {tone} —— {descriptor}")
    return "\n\n".join(blocks)


CHAT_CONTINUATION_PROMPT = (
    "You are continuing a single, already-completed I Ching reading. Do not recast or change the hexagram. "
    "Ground all answers in the hexagram, the classical text and payload from the initial analysis, and your own prior "
    "explanation in this thread. Treat each user message as a follow-up about the same situation; if the user wanders "
    "off to unrelated topics, gently redirect back to this reading.\n\n"
    + SYSTEM_PROMPT_PRO.strip()
)


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
        ("A", "gpt-4.1", "默认 (推荐)"),
        ("B", "gpt-5.1", "深度推理"),
        ("C", "gpt-5-mini", "兼容/聊天"),
        ("D", "gpt-4.1-nano", "极速 (最低成本/延迟)"),
        ("E", "gpt-5", "高阶文本与推理"),
        ("F", "o3", "最强推理 (更慢/更贵)"),
    ]
    print(f"\n请选择OpenAI模型（默认：{DEFAULT_MODEL}）：")
    for letter, model, desc in options:
        print(f"  [{letter}] {model.ljust(12)} —— {desc}")
    choice = input("请尊贵的用户选择：").strip().upper()
    mapping = {
        "": DEFAULT_MODEL,
        "A": "gpt-4.1",
        "B": "gpt-5.1",
        "C": "gpt-5-mini",
        "D": "gpt-4.1-nano",
        "E": "gpt-5",
        "F": "o3",
    }
    selected = mapping.get(choice)
    if selected:
        return selected
    print(f"警告：输入无效，已自动使用默认模型 {DEFAULT_MODEL}。")
    return DEFAULT_MODEL


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

    choose_model = model_selector or _interactive_model_selector
    model_name = model_hint or (choose_model() if interactive else DEFAULT_MODEL)

    selected_reasoning = _normalize_reasoning(model_name, reasoning_effort or data.get("ai_reasoning"))
    selected_verbosity = _normalize_verbosity(model_name, verbosity or data.get("ai_verbosity"))
    reasoning_payload = None if selected_reasoning in (None, "none") else selected_reasoning

    client = OpenAI(api_key=api_key)
    user_prompt = _build_prompt(data)
    response = _request_openai_response(
        client=client,
        model_name=model_name,
        instructions=SYSTEM_PROMPT_PRO.strip(),
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
        response_id=getattr(response, "id", None),
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
) -> AIResponseData:
    if not previous_response_id:
        raise ValueError("previous_response_id is required for follow-up calls.")

    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured on the server.")

    resolved_model = model_name or DEFAULT_MODEL
    selected_reasoning = _normalize_reasoning(resolved_model, reasoning_effort)
    selected_verbosity = _normalize_verbosity(resolved_model, verbosity)
    reasoning_payload = None if selected_reasoning in (None, "none") else selected_reasoning

    instruction_block = CHAT_CONTINUATION_PROMPT
    if tone:
        descriptor = TONE_PROFILES.get(tone, "用户自定义语气")
        instruction_block += f"\n\n语气设定: {tone} —— {descriptor}"

    client = OpenAI(api_key=api_key)
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
        response_id=getattr(response, "id", None),
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

    resolved_model = model_name or DEFAULT_MODEL
    selected_reasoning = _normalize_reasoning(resolved_model, reasoning_effort)
    selected_verbosity = _normalize_verbosity(resolved_model, verbosity)
    reasoning_payload = None if selected_reasoning in (None, "none") else selected_reasoning

    instruction_block = CHAT_CONTINUATION_PROMPT
    if tone:
        descriptor = TONE_PROFILES.get(tone, "用户自定义语气")
        instruction_block += f"\n\n语气设定: {tone} —— {descriptor}"

    user_input = (
        "以下是同一会话的固定占卜上下文，请据此回答用户追问，不要重起卦：\n\n"
        f"{context}\n\n"
        f"用户追问：{stripped}"
    )

    client = OpenAI(api_key=api_key)
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
        response_id=getattr(response, "id", None),
        usage=usage,
    )


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
    najia_data = data.get("najia_data")
    if najia_data:
        try:
            blocks.append("纳甲/六神/六亲:\n" + json.dumps(najia_data, ensure_ascii=False, indent=2))
        except Exception:
            blocks.append("纳甲/六神/六亲:\n" + str(najia_data))
    if ai_analysis := data.get("ai_analysis"):
        blocks.append("已有 AI 解读（仅作参考）:\n" + str(ai_analysis))
    return "\n\n".join(blocks).strip()


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
    def build_payload(use_reasoning: bool, use_verbosity: bool) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model_name,
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
            payload["reasoning"] = {"effort": reasoning}
        if use_verbosity and verbosity:
            payload["text"] = {"verbosity": verbosity}
        return payload

    use_reasoning = bool(reasoning)
    use_verbosity = bool(verbosity)

    try:
        return client.responses.create(**build_payload(use_reasoning, use_verbosity))
    except BadRequestError as exc:
        error_text = str(exc).lower()
        retried = False
        if use_reasoning and "reasoning" in error_text:
            use_reasoning = False
            try:
                response = client.responses.create(**build_payload(use_reasoning, use_verbosity))
                retried = True
            except BadRequestError as inner_exc:
                error_text = str(inner_exc).lower()
                if use_verbosity and ("text" in error_text or "verbosity" in error_text):
                    use_verbosity = False
                    response = client.responses.create(**build_payload(use_reasoning, use_verbosity))
                    retried = True
                else:
                    raise
        if not retried:
            if use_verbosity and ("text" in error_text or "verbosity" in error_text):
                use_verbosity = False
                try:
                    return client.responses.create(**build_payload(use_reasoning, use_verbosity))
                except BadRequestError as inner_exc:
                    error_text = str(inner_exc).lower()
                    if use_reasoning and "reasoning" in error_text:
                        use_reasoning = False
                        return client.responses.create(**build_payload(use_reasoning, use_verbosity))
                    raise
            raise
        return response


def _extract_response_text(response: Any) -> Optional[str]:
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text.strip()
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        contents = getattr(item, "content", []) or []
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
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    usage_dict: Dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, key, None)
        if value is None and isinstance(usage, dict):
            value = usage.get(key)
        if value is not None:
            usage_dict[key] = int(value)
    return usage_dict or None


def _normalize_reasoning(model_name: str, requested: Optional[str]) -> Optional[str]:
    meta = MODEL_CAPABILITIES.get(model_name, MODEL_CAPABILITIES[DEFAULT_MODEL])
    allowed = meta.get("reasoning", [])
    if not allowed:
        return None
    if requested == "none":
        return "none"
    if requested in allowed:
        return requested
    default_reasoning = meta.get("default_reasoning")
    if default_reasoning in allowed:
        return default_reasoning
    return allowed[0]


def _normalize_verbosity(model_name: str, requested: Optional[str]) -> Optional[str]:
    meta = MODEL_CAPABILITIES.get(model_name, MODEL_CAPABILITIES[DEFAULT_MODEL])
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

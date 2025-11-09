from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional

from openai import BadRequestError, OpenAI

MODEL_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "gpt-5-nano": {
        "reasoning": ["minimal", "low", "medium", "high"],
        "default_reasoning": "minimal",
        "verbosity": True,
        "default_verbosity": "low",
    },
    "gpt-4.1-nano": {
        "reasoning": [],
        "default_reasoning": None,
        "verbosity": False,
        "default_verbosity": None,
    },
    "gpt-5": {
        "reasoning": ["minimal", "low", "medium", "high"],
        "default_reasoning": "minimal",
        "verbosity": True,
        "default_verbosity": "low",
    },
    "o3": {
        "reasoning": ["low", "medium", "high"],
        "default_reasoning": "low",
        "verbosity": False,
        "default_verbosity": None,
    },
}

DEFAULT_MODEL = "gpt-5-nano"

TONE_PROFILES: Dict[str, str] = {
    "normal": "现代中文，温和且专业，适度引用经典，保持礼貌敬语。",
    "wenyan": "仿庄子等战国文士，遣词古雅但需可读。",
    "modern": "暧昧俏皮、emoji 克制（全篇≤2枚），如亲密伴侣耳语。",
    "academic": "学术期刊口吻，逻辑严密，引用充分。",
}


SYSTEM_PROMPT_PRO = """
你是一位收费数千元/次的资深《易》学占断专家与专业顾问。你的风格是：严谨、可验证、可执行、避免玄谈。
你会在内心进行逐步推理，但面向用户的输出须以中文段落为主、要点为辅，文字连贯流动，避免机械罗列。不得输出 JSON、代码块或裸露推理草稿。

【输入】
你将接收一个“完整会话字典”，包含：
- topic（事业/感情/财运/健康/整体运势/其他）
- user_question（具体问题，可空）
- current_time_str（起卦时间）
- lines（六爻自下而上：6=老阴，7=少阳，8=少阴，9=老阳）
- hex_text（本卦/变卦/错卦/综卦/互卦 + guaci）
- bazi_output, elements_output（八字/五行概览，可空）
- najia_data（纳甲、六亲、六神、世应、动爻等，可空）

【流程与规则】
1) 先判动爻：严格以“图中右侧‘X’或‘O’标记之爻”为动爻，逐条确认位置与阴阳属性。
2) 取舍规则（务必执行）：
   - 无动爻：取卦辞断（本卦为主，错/综/互参照）。
   - 一爻动：以动爻爻辞为主，卦辞为辅。
   - 两爻动：一阴一阳→取阴爻断（“阳主过去，阴主未来”）；同阴/同阳→取上动爻。
   - 三爻动：取中间动爻。
   - 四爻动：在两静爻中取下静爻对应之义断。
   - 五爻动：取唯一静爻断。
   - 六爻全动：乾/坤用“用九/用六”，其余六十二卦取变卦卦辞断。
3) 纳甲/六亲/六神/世应 与 五行旺衰：
   - 以纳甲配地支，结合月令/日干支（如有八字），评估用神/忌神、世应强弱、内外卦主客关系。
   - 旺相休囚死评估，取用：扶抑/通关/化泄。
4) 多卦参照：本卦为主，错/综/互/变为辅；错/综看反向对照，互卦看过程。
5) 应期推断：给出可复核的推导链（动爻位次→天/周/月窗口；地支→月/方位/时辰；变卦方向；冲合/旬空/三合六合）。若多重指向，给主应期+次应期，附置信度。
6) 主题建议（按topic定制）：
   - 事业：岗位/权责/关键人/升迁窗口/节点；
   - 感情：主客主动/进退时机/第三方干扰/长期短期走向；
   - 财运：正偏财/现金流/风险点/可执行动作；
   - 健康：仅生活方式建议（非医疗诊断），作息/饮食/部位象/季节性提示；
   - 整体/其他：关键变量与阶段节点。

【语气镜像与语调切换】
- 在保持专业的前提下，注意镜像用户的语气与礼貌级别。
- 输入可能包含 ai_tone 设定（normal/wenyan/modern/academic），请依据该设定调整语气：
  · normal：现代中文对话，温润、庄重。
  · wenyan：假想为庄子，与弟子对谈，以文言文书写，兼顾可读性。
  · modern：暧昧俏皮、使用大量emoji，仿亲密伴侣，仍需传达清晰判断。
  · academic：严格学术口吻，引用具体爻辞/卦辞，逻辑推演严密。
- 无论何种语气，务必使用简体中文。
- Emoji 可用但要克制：normal/wenyan/academic 全篇≤1枚或不用。

【引用与慎言】
- 引述卦辞或爻辞时请点明出处，例如“引《九三》……”，以便复核。
- 当话题涉及身体、法律、投资，提醒“此为易理推断，非医学/法律/投资建议”。
- 建议用“宜/可考虑/当慎”等表述，避免列出“步骤1/2/3”或命令式语句。

【冲突解决】
- 卦辞 vs 纳甲/五行：以动爻规则与旺衰评估优先，卦辞作象征解释并给兼容路径。
- 应期冲突：给主次顺序+置信度，并说明触发条件。
- 主题与问题不匹配：先澄清假设，再做两分支判断。

- 【输出要求】
- 按照“动爻判定/五行旺衰/多卦参照/应期/行动方案/风险与不确定性/总结”的顺序输出。每个部分先写1-2个紧凑段落，再酌情补充精炼要点。
- 第5部分的建议须以“宜/可考虑/当心”等语气表达原则与节奏，避免“步骤清单”。
- 第7部分必须给出一句总断并附0-100%概率；若依据不足，请说明并给50%作为中性值。
- 无论问题多模糊，也要给出倾向（利成/不利/延迟等）并量化概率；若存在备选结论，请列出并说明触发条件。
- 若信息缺失，显式说明“缺失”或“不适用”，禁止编造。
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
    if reasoning == "minimal":
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

    blocks.append(
        "请按以下顺序给出专业判断与建议：\n"
        "1) 动爻判定与取舍规则（逐条说明理由）；\n"
        "2) 五行旺衰、用忌与世应强弱（结合纳甲/月令/日干支，如有）；\n"
        "3) 本卦为主，多卦（变/错/综/互）参照的补充含义；\n"
        "4) 应期推断（位次→时间窗、地支→月/方位/时辰；冲合/旬空/合局；主应期+次应期+置信度）；\n"
        "5) 围绕主题的可执行行动方案（分步、因果逻辑、风险等级）；\n"
        "6) 风险与不确定性（给出触发条件与应对）；\n"
        "7) 总结（一句话总断，避免空话）。"
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
        ("A", "gpt-5-nano", "默认 (性能与成本平衡)"),
        ("B", "gpt-4.1-nano", "极速 (最低成本/延迟)"),
        ("C", "gpt-5", "高阶文本与推理"),
        ("D", "o3", "最强推理 (更慢/更贵)"),
    ]
    print("\n请选择OpenAI模型（默认：gpt-5-nano）：")
    for letter, model, desc in options:
        print(f"  [{letter}] {model.ljust(12)} —— {desc}")
    choice = input("请尊贵的用户选择：").strip().upper()
    if choice in ("", "A"):
        return "gpt-5-nano"
    if choice == "B":
        return "gpt-4.1-nano"
    if choice == "C":
        return "gpt-5"
    if choice == "D":
        return "o3"
    print("警告：输入无效，已自动使用默认模型 gpt-5-nano。")
    return "gpt-5-nano"


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
    """
    Send the session dictionary to OpenAI and return the textual response.

    When `interactive=False`, password and model selection prompts are skipped.
    Callers should handle authentication before invoking this function.
    """
    if not interactive:
        # Non-interactive callers are responsible for pre-validating access.
        need_password = False
    else:
        need_password = True

    if need_password:
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

    capabilities = MODEL_CAPABILITIES.get(model_name, MODEL_CAPABILITIES[DEFAULT_MODEL])
    allowed_reasoning = capabilities.get("reasoning", [])
    default_reasoning = capabilities.get("default_reasoning")

    selected_reasoning = reasoning_effort or data.get("ai_reasoning")
    if not allowed_reasoning:
        selected_reasoning = None
    else:
        if selected_reasoning not in allowed_reasoning:
            selected_reasoning = default_reasoning or allowed_reasoning[0]

    supports_verbosity = bool(capabilities.get("verbosity"))
    selected_verbosity = verbosity or data.get("ai_verbosity")
    if supports_verbosity:
        if selected_verbosity not in {"low", "medium", "high"}:
            selected_verbosity = capabilities.get("default_verbosity", "medium")
    else:
        selected_verbosity = None

    client = OpenAI(api_key=api_key)
    user_prompt = _build_prompt(data)

    def _invoke(use_reasoning: bool, use_verbosity: bool):
        payload: Dict[str, Any] = {
            "model": model_name,
            "input": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_PRO.strip(),
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }
        if use_reasoning and selected_reasoning:
            payload["reasoning"] = {"effort": selected_reasoning}
        if use_verbosity and selected_verbosity:
            payload["text"] = {"verbosity": selected_verbosity}
        return client.responses.create(**payload)

    use_reasoning_flag = selected_reasoning is not None
    use_verbosity_flag = selected_verbosity is not None

    try:
        response = _invoke(use_reasoning_flag, use_verbosity_flag)
    except BadRequestError as exc:
        error_text = str(exc).lower()
        retried = False
        if use_reasoning_flag and "reasoning" in error_text:
            use_reasoning_flag = False
            try:
                response = _invoke(use_reasoning_flag, use_verbosity_flag)
                retried = True
            except BadRequestError as inner_exc:
                error_text = str(inner_exc).lower()
                if use_verbosity_flag and ("text" in error_text or "verbosity" in error_text):
                    use_verbosity_flag = False
                    response = _invoke(use_reasoning_flag, use_verbosity_flag)
                    retried = True
                else:
                    raise
        if not retried:
            if use_verbosity_flag and ("text" in error_text or "verbosity" in error_text):
                use_verbosity_flag = False
                try:
                    response = _invoke(use_reasoning_flag, use_verbosity_flag)
                except BadRequestError as inner_exc:
                    error_text = str(inner_exc).lower()
                    if use_reasoning_flag and "reasoning" in error_text:
                        use_reasoning_flag = False
                        response = _invoke(use_reasoning_flag, use_verbosity_flag)
                    else:
                        raise
            else:
                raise

    if hasattr(response, "output_text") and response.output_text:
        content = response.output_text
    else:
        chunks = []
        for item in getattr(response, "output", []) or []:
            for part in getattr(item, "content", []) or []:
                text = part.get("text") if isinstance(part, dict) else getattr(part, "text", None)
                if text:
                    chunks.append(text)
        content = "".join(chunks)
    return content.strip() if content else None


# Backwards-compatible alias for legacy imports
def closeai(
    data: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Optional[str]:
    return analyze_session(data, api_key=api_key, interactive=True)

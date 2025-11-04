from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional

from openai import OpenAI


SYSTEM_PROMPT_PRO = """
你是一位收费数千元/次的资深《易》学占断专家与专业顾问。你的风格是：严谨、可验证、可执行、避免玄谈。
你会在内心进行逐步推理，但只输出结构化结论（JSON），不要暴露推理草稿。

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

【冲突解决】
- 卦辞 vs 纳甲/五行：以动爻规则与旺衰评估优先，卦辞作象征解释并给兼容路径。
- 应期冲突：给主次顺序+置信度，并说明触发条件。
- 主题与问题不匹配：先澄清假设，再做两分支判断。

【输出要求】
- 仿照流程与规则中的格式，尽可能说明细节。
- 若信息缺失，显式留空或给“缺失”说明，禁止编造。
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
        ("A", "gpt-5-nano", "最快 (推荐日常批量/工具/低成本)"),
        ("B", "gpt-5", "最均衡 (推荐复杂文本、推理)"),
        ("C", "o3", "最强/最慢 (复杂推理、大模型实验)"),
    ]
    print("\n请选择OpenAI模型（默认：gpt-5-nano）：")
    for letter, model, desc in options:
        print(f"  [{letter}] {model.ljust(12)} —— {desc}")
    choice = input("请尊贵的用户选择：").strip().upper()
    if choice in ("", "A"):
        return "gpt-5-nano"
    if choice == "B":
        return "gpt-5"
    if choice == "C":
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

    choose_model = model_selector or _interactive_model_selector
    model_name = model_hint or (choose_model() if interactive else "gpt-5-nano")

    client = OpenAI(api_key=api_key)
    user_prompt = _build_prompt(data)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_PRO.strip()},
            {"role": "user", "content": user_prompt},
        ],
        temperature=1,
    )
    content = response.choices[0].message.content
    return content.strip() if content else None


# Backwards-compatible alias for legacy imports
def closeai(
    data: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Optional[str]:
    return analyze_session(data, api_key=api_key, interactive=True)

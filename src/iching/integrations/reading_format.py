"""One definition of the reading's section structure, for prompt and parser.

The system prompt asked for eight Chinese headings and ``session.py`` recovered
them with a separate set of string literals. The two drifted: the parser looked
for English heading variants the prompt never requested, and the prompt was
hardcoded to Simplified Chinese while the product shipped an English locale, so
an English reader got Chinese prose and an empty conclusion card.

Everything about that structure now lives here. :func:`build_system_prompt`
renders the instructions for a locale, and :func:`parse_sections` reads the
result back by matching *either* locale's heading. Adding a section means
editing one table.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

LOCALES = ("zh", "en")
DEFAULT_LOCALE = "zh"

#: Both the full-width and ASCII forms appear in real model output.
FIELD_SEPARATORS = "｜|"
LABEL_SEPARATORS = "：:"


@dataclass(frozen=True)
class SectionSpec:
    key: str
    zh: str
    en: str
    zh_body: Tuple[str, ...]
    en_body: Tuple[str, ...]

    def heading(self, locale: str) -> str:
        return self.en if locale == "en" else self.zh

    def body(self, locale: str) -> Tuple[str, ...]:
        return self.en_body if locale == "en" else self.zh_body


SECTION_SPECS: Tuple[SectionSpec, ...] = (
    SectionSpec(
        key="headline",
        zh="一句话结论",
        en="Bottom line",
        zh_body=("一句话给出倾向（利成/延迟/不利）与核心原因。",),
        en_body=(
            "One sentence: the leaning (favourable / delayed / unfavourable) and why.",
        ),
    ),
    SectionSpec(
        key="plain_language",
        zh="给普通人的解释",
        en="In plain language",
        zh_body=(
            "1-2段，先说结果再说原因。",
            "每段至少出现一句“换成大白话：...”。",
        ),
        en_body=(
            "One or two paragraphs: the result first, then the reason.",
            "Each paragraph includes one sentence starting \"Put plainly: ...\".",
        ),
    ),
    SectionSpec(
        key="evidence",
        zh="证据短链",
        en="Evidence chain",
        zh_body=(
            "3-5条，每条必须使用：",
            "`- 结论：...｜依据：...｜白话：...`",
            "依据必须来自动爻、卦辞/爻辞、纳甲/五行中的至少一项。",
        ),
        en_body=(
            "Three to five items, each written as:",
            "`- Claim: ...|Basis: ...|Plainly: ...`",
            "The basis must cite a moving line, a hexagram or line text, or Najia/五行.",
        ),
    ),
    SectionSpec(
        key="timing",
        zh="应期与条件",
        en="Timing and conditions",
        zh_body=(
            "`- 主应期：...｜条件：...｜置信度：...%`",
            "`- 次应期：...｜条件：...｜置信度：...%`",
            "置信度必须绑定条件，不允许裸数字。",
        ),
        en_body=(
            "`- Window: ...|Condition: ...|Confidence: ...%`",
            "`- Window: ...|Condition: ...|Confidence: ...%`",
            "Every confidence figure is bound to its condition; never a bare number.",
        ),
    ),
    SectionSpec(
        key="actions",
        zh="行动建议",
        en="Actions",
        zh_body=(
            "给3条建议，每条都必须包含：",
            "`- 动作：...｜节奏：...｜观察指标：...`",
        ),
        en_body=(
            "Three items, each written as:",
            "`- Action: ...|Cadence: ...|Signal: ...`",
        ),
    ),
    SectionSpec(
        key="risks",
        zh="风险与转折信号",
        en="Risk signals",
        zh_body=("给2-4条可观察信号，说明何时转强或转弱。",),
        en_body=(
            "Two to four observable signals, saying when this turns stronger or weaker.",
        ),
    ),
    SectionSpec(
        key="followups",
        zh="继续追问",
        en="Continue with",
        zh_body=(
            "给3个用户可以直接点击继续问的问题。",
            "每条必须是短问题，不要超过28个汉字。",
        ),
        en_body=(
            "Three short follow-up questions the reader can click straight through.",
            "Keep each under 16 words.",
        ),
    ),
    SectionSpec(
        key="final",
        zh="最终判断",
        en="Final call",
        zh_body=("用两句话收束：最终结论 + 下一步最重要动作。",),
        en_body=(
            "Two sentences: the final conclusion and the single most important next step.",
        ),
    ),
)

SECTIONS_BY_KEY: Dict[str, SectionSpec] = {spec.key: spec for spec in SECTION_SPECS}

#: Normalized heading text -> section key, for every locale at once. Matching
#: both means a reading stays parseable even if the model answers in the other
#: language, or a stored session predates the locale parameter.
_HEADING_INDEX: Dict[str, str] = {}


def normalize_locale(value: Optional[str]) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("zh"):
        return "zh"
    if text.startswith("en"):
        return "en"
    return DEFAULT_LOCALE


def _normalize_heading(value: str) -> str:
    """Fold the ways a model writes the same heading into one key."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.strip().lstrip("#").strip()
    text = text.strip("*_ ")
    text = re.sub(r"^[0-9]+[.)、]\s*", "", text)
    text = text.rstrip("：:。.").strip()
    return text.casefold()


for _spec in SECTION_SPECS:
    for _name in (_spec.zh, _spec.en):
        _HEADING_INDEX[_normalize_heading(_name)] = _spec.key
# Headings earlier revisions of the prompt asked for.
_HEADING_INDEX[_normalize_heading("Bottom-line")] = "headline"
_HEADING_INDEX[_normalize_heading("Conclusion")] = "headline"
_HEADING_INDEX[_normalize_heading("Plain language")] = "plain_language"
_HEADING_INDEX[_normalize_heading("Follow-up questions")] = "followups"


def heading_key(line: str) -> Optional[str]:
    """Return the section key a line introduces, or ``None``."""
    return _HEADING_INDEX.get(_normalize_heading(line))


def is_heading(line: str) -> bool:
    """A markdown heading, whether or not it is one of ours."""
    return line.lstrip().startswith("#")


LANGUAGE_RULE = {
    "zh": "输出为简体中文 Markdown，只使用标题与顶层 `- ` 列表，禁止嵌套列表。",
    "en": (
        "Write in English Markdown, using only headings and top-level `- ` lists. "
        "No nested lists. Keep Chinese only for hexagram, line and Najia names, "
        "each followed by a short English gloss on first use."
    ),
}

_PREAMBLE = {
    "zh": """你是资深《易》学占断顾问。目标是给出清晰、可验证、可执行的判断，优先让普通用户听得懂。

【硬性规则】
- 只依据输入会话数据推断；信息不足就明确写“信息不足”，不得编造。
- 保持明确立场，避免空泛套话与两头下注。
- 允许给出直接建议，避免冗余合规口吻。
- 不输出 JSON、代码块、表格或多级列表。
- {language_rule}

【核心推断方法】
1) 取用规则由系统给出，写在输入的“取用”一行里；直接采用，不要另行推导。
2) 本卦为主，变/错/综/互为辅；互卦看过程，错综看反向牵制。
3) 结合纳甲、六亲、六神、世应、五行旺衰判断主客强弱、用忌与阻力来源。
4) 应期必须给主次窗口，并写明触发条件。

【输出结构（严格按顺序，标题逐字照抄）】
{sections}""",
    "en": """You are a senior I Ching consultant. Give a clear, checkable, actionable judgement that a non-specialist can follow.

RULES
- Reason only from the session data supplied; where it is insufficient, say so plainly and invent nothing.
- Take a position. No hedging, no covering both sides.
- Direct advice is welcome; skip compliance boilerplate.
- No JSON, code blocks, tables or nested lists.
- {language_rule}

METHOD
1) The line-selection rule is given to you on the "Line selection" input row. Use it as given; do not re-derive it.
2) The present hexagram leads; the changed, opposite, inverted and nuclear hexagrams support it. The nuclear hexagram shows process, the opposite and inverted show counter-pressure.
3) Read Najia, the six relatives, the six spirits, subject/object lines and elemental strength to judge relative strength, what helps, what hinders, and where resistance comes from.
4) Timing must give a primary and a secondary window, each with its trigger condition.

OUTPUT STRUCTURE (in this order, headings copied exactly)
{sections}""",
}


def build_system_prompt(locale: Optional[str] = None) -> str:
    """Render the full system prompt for a locale."""
    resolved = normalize_locale(locale)
    blocks: List[str] = []
    for spec in SECTION_SPECS:
        lines = [f"# {spec.heading(resolved)}"]
        lines.extend(f"- {item}" for item in spec.body(resolved))
        blocks.append("\n".join(lines))
    return _PREAMBLE[resolved].format(
        language_rule=LANGUAGE_RULE[resolved],
        sections="\n\n".join(blocks),
    )


def parse_sections(text: Optional[str]) -> Dict[str, List[str]]:
    """Split model output into ``{section key: [content lines]}``.

    Content lines keep their order and have list markers stripped. Unknown
    headings end the current section rather than being swallowed into it.
    """
    if not text:
        return {}
    collected: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for raw in str(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        if is_heading(line):
            current = heading_key(line)
            if current is not None:
                collected.setdefault(current, [])
            continue
        key = heading_key(line)
        if key is not None and len(line) <= 24:
            # Some models drop the "#" and leave the heading on its own line.
            current = key
            collected.setdefault(current, [])
            continue
        if current is None:
            continue
        cleaned = re.sub(r"^[-•*]\s*", "", line)
        cleaned = re.sub(r"^\d+[.)]\s*", "", cleaned).strip()
        cleaned = cleaned.strip("*_ ").strip()
        if cleaned:
            collected[current].append(cleaned)
    return collected


def split_fields(line: str) -> List[str]:
    """Split a ``label: value`` row on either pipe form."""
    pattern = f"[{re.escape(FIELD_SEPARATORS)}]"
    return [part.strip() for part in re.split(pattern, str(line or "")) if part.strip()]


def field_value(parts: Sequence[str], labels: Sequence[str]) -> str:
    """Read one labelled field, accepting either colon form and any locale."""
    wanted = {_normalize_heading(label) for label in labels}
    for part in parts:
        for separator in LABEL_SEPARATORS:
            head, found, tail = part.partition(separator)
            if found and _normalize_heading(head) in wanted:
                return tail.strip()
    return ""


def first_body_line(text: Optional[str], key: str) -> Optional[str]:
    lines = parse_sections(text).get(key) or []
    return lines[0] if lines else None

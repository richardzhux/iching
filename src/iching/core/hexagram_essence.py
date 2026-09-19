"""Per-hexagram 大象 / 象傳 counsel, pulled from the corpus.

The reading brief used to fall back to one constant sentence per direction
("变化已经开始，先处理最关键的触发点。") and one constant next step ("先验证一
个决定成败的条件，再决定是否加码。"). Those read as filler because they are:
the same words appear whatever was cast, so they describe no hexagram in
particular.

Every hexagram carries its own image and counsel in the interpretation
database. This reads them so the brief can say something only true of the
hexagram in front of the reader.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Protocol

_IMAGE_RE = re.compile(r"^大象[：:](?P<value>[^\n]+)", re.MULTILINE)
_TREND_RE = re.compile(r"^运势[：:](?P<value>[^\n]+)", re.MULTILINE)
_XIANG_RE = re.compile(r"^象曰[：:](?P<value>[^\n]+)", re.MULTILINE)
_COUNSEL_RE = re.compile(r"(君子以|先王以|后以|大人以|上以)(?P<value>[^\n。；;]+)")


class _SlotSource(Protocol):
    def get_slot_content(
        self,
        *,
        hexagram_name: str,
        source_key: str,
        slot_kind: str,
        line_no: Optional[int] = ...,
        use_kind: Optional[str] = ...,
        locale: str = ...,
    ) -> Optional[str]: ...


@dataclass(frozen=True, slots=True)
class HexagramEssence:
    name: str
    image: str = ""
    counsel: str = ""
    trend: str = ""

    @property
    def has_content(self) -> bool:
        return bool(self.image or self.counsel or self.trend)


def _clean(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", "", value).strip().strip("。;；，,")


def essence_for(
    hexagram_name: str, repo: Optional[_SlotSource]
) -> HexagramEssence:
    """Image, counsel and trend for one hexagram; empty when unavailable."""
    if not hexagram_name or repo is None:
        return HexagramEssence(name=hexagram_name or "")
    try:
        content = repo.get_slot_content(
            hexagram_name=hexagram_name,
            source_key="guaci",
            slot_kind="gua",
            locale="zh-CN",
        )
    except Exception:
        return HexagramEssence(name=hexagram_name)
    if not content:
        return HexagramEssence(name=hexagram_name)

    image = _clean(match.group("value") if (match := _IMAGE_RE.search(content)) else "")
    trend = _clean(match.group("value") if (match := _TREND_RE.search(content)) else "")
    xiang = _clean(match.group("value") if (match := _XIANG_RE.search(content)) else "")
    counsel = ""
    if match := _COUNSEL_RE.search(xiang or content):
        counsel = _clean(match.group(1) + match.group("value"))
    if not image and xiang:
        image = _clean(xiang.split("，")[0])

    return HexagramEssence(
        name=hexagram_name, image=image, counsel=counsel, trend=trend
    )

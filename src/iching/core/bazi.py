from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import sxtwl


@dataclass(slots=True)
class BaZiCalculator:
    """Calculate BaZi and Five Elements based on a given datetime."""

    datetime_obj: datetime
    _last_components: Optional[Dict[str, str]] = field(init=False, default=None)
    _last_detail: Optional[List[Dict[str, object]]] = field(init=False, default=None)

    five_elements = {
        "甲": "阳木",
        "乙": "阴木",
        "丙": "阳火",
        "丁": "阴火",
        "戊": "阳土",
        "己": "阴土",
        "庚": "阳金",
        "辛": "阴金",
        "壬": "阳水",
        "癸": "阴水",
        "子": "阳水",
        "丑": "阴土",
        "寅": "阳木",
        "卯": "阴木",
        "辰": "阳土",
        "巳": "阴火",
        "午": "阳火",
        "未": "阴土",
        "申": "阳金",
        "酉": "阴金",
        "戌": "阳土",
        "亥": "阴水",
    }

    Gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    Zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    def calculate(self) -> Tuple[str, str]:
        year = self.datetime_obj.year
        month = self.datetime_obj.month
        day = self.datetime_obj.day
        hour = self.datetime_obj.hour

        solar_day = sxtwl.fromSolar(year, month, day)

        year_gz = solar_day.getYearGZ()
        month_gz = solar_day.getMonthGZ()
        day_gz = solar_day.getDayGZ()
        hour_gz = solar_day.getHourGZ(hour)

        bazi_output = (
            f"{self.Gan[year_gz.tg]}{self.Zhi[year_gz.dz]}年 "
            f"{self.Gan[month_gz.tg]}{self.Zhi[month_gz.dz]}月 "
            f"{self.Gan[day_gz.tg]}{self.Zhi[day_gz.dz]}日 "
            f"{self.Gan[hour_gz.tg]}{self.Zhi[hour_gz.dz]}时"
        )

        detail = self._build_detail(year_gz, month_gz, day_gz, hour_gz)
        elements_output = " ".join(
            f"{pillar['stem']['element'] or pillar['stem']['value']}"
            f"{pillar['branch']['element'] or pillar['branch']['value']}"
            f"{pillar['label']}"
            for pillar in detail
        )

        self._last_components = {
            "year_stem": self.Gan[year_gz.tg],
            "year_branch": self.Zhi[year_gz.dz],
            "month_stem": self.Gan[month_gz.tg],
            "month_branch": self.Zhi[month_gz.dz],
            "day_stem": self.Gan[day_gz.tg],
            "day_branch": self.Zhi[day_gz.dz],
            "hour_stem": self.Gan[hour_gz.tg],
            "hour_branch": self.Zhi[hour_gz.dz],
        }
        self._last_detail = detail

        return bazi_output, elements_output

    @property
    def last_components(self) -> Optional[Dict[str, str]]:
        return self._last_components

    @property
    def last_detail(self) -> Optional[List[Dict[str, object]]]:
        return self._last_detail

    def _build_detail(self, year_gz, month_gz, day_gz, hour_gz) -> List[Dict[str, object]]:
        mapping = [
            ("年", year_gz.tg, year_gz.dz),
            ("月", month_gz.tg, month_gz.dz),
            ("日", day_gz.tg, day_gz.dz),
            ("时", hour_gz.tg, hour_gz.dz),
        ]
        detail: List[Dict[str, object]] = []
        for label, stem_idx, branch_idx in mapping:
            stem_value = self.Gan[stem_idx]
            branch_value = self.Zhi[branch_idx]
            stem_polarity, stem_element = self._describe_symbol(stem_value)
            branch_polarity, branch_element = self._describe_symbol(branch_value)
            detail.append(
                {
                    "label": label,
                    "stem": {
                        "value": stem_value,
                        "polarity": stem_polarity,
                        "element": stem_element,
                    },
                    "branch": {
                        "value": branch_value,
                        "polarity": branch_polarity,
                        "element": branch_element,
                    },
                }
            )
        return detail

    def _describe_symbol(self, symbol: str) -> Tuple[str, str]:
        descriptor = self.five_elements.get(symbol, "")
        if not descriptor:
            return "", ""
        return descriptor[0], descriptor[1:] or symbol

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import sxtwl

from iching.core.metaphysics import BRANCHES, JIE_QI_NAMES, STEMS
from iching.core.shensha import AXES, CORE_RULE_IDS, RULES_VERSION, evaluate_shensha


DEFAULT_OUTPUT = Path(__file__).parents[1] / "src" / "iching" / "core" / "data"
BASELINE_VERSION = "calendar-1924-2044-v1"


def _jieqi_datetime(item, zone: ZoneInfo) -> datetime:
    value = sxtwl.JD2DD(item.jd)
    return datetime(int(value.Y), int(value.M), int(value.D), int(value.h), int(value.m), int(value.s), tzinfo=zone)


def _lichun(year: int, zone: ZoneInfo) -> datetime:
    for item in sxtwl.getJieQiByYear(year):
        if JIE_QI_NAMES[int(item.jqIndex)] == "立春":
            value = _jieqi_datetime(item, zone)
            if value.year == year:
                return value
    raise RuntimeError(f"Missing Li Chun for {year}")


def _events(start: datetime, end: datetime, zone: ZoneInfo, day_boundary: str) -> list[datetime]:
    values = {start, end}
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    boundary_hours = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23) if day_boundary == "current" else (1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
    while day <= end:
        for hour in boundary_hours:
            value = day.replace(hour=hour)
            if start < value < end:
                values.add(value)
        day += timedelta(days=1)
    for year in range(start.year - 1, end.year + 2):
        for item in sxtwl.getJieQiByYear(year):
            value = _jieqi_datetime(item, zone)
            if start < value < end:
                values.add(value)
    return sorted(values)


def _pillars(value: datetime, day_boundary: str) -> list[dict[str, str]]:
    pillar_date = value + timedelta(days=1) if day_boundary == "forward" and value.hour >= 23 else value
    day = sxtwl.fromSolar(pillar_date.year, pillar_date.month, pillar_date.day)
    hour = 0 if day_boundary == "forward" and value.hour >= 23 else value.hour
    gz_values = (day.getYearGZ(), day.getMonthGZ(), day.getDayGZ(), day.getHourGZ(hour))
    labels = ("年", "月", "日", "时")
    return [
        {
            "label": label,
            "stem": STEMS[gz.tg],
            "branch": BRANCHES[gz.dz],
            "text": f"{STEMS[gz.tg]}{BRANCHES[gz.dz]}",
        }
        for label, gz in zip(labels, gz_values)
    ]


def generate(day_boundary: str) -> dict:
    zone = ZoneInfo("Asia/Shanghai")
    start = _lichun(1924, zone)
    end = _lichun(2044, zone)
    events = _events(start, end, zone, day_boundary)
    feature_weights: Counter[str] = Counter()
    axis_histograms = {axis: Counter() for axis in AXES}
    total_seconds = 0.0
    for left, right in zip(events, events[1:]):
        seconds = right.timestamp() - left.timestamp()
        if seconds <= 0:
            continue
        midpoint = datetime.fromtimestamp((left.timestamp() + right.timestamp()) / 2, zone)
        hits = evaluate_shensha(_pillars(midpoint, day_boundary), include_extended=True)
        total_seconds += seconds
        for hit in hits:
            feature_weights[hit["feature_id"]] += seconds
        core_ids = {hit["rule_id"] for hit in hits if hit["rule_id"] in CORE_RULE_IDS}
        for axis in AXES:
            count = sum(1 for hit in hits if hit["rule_id"] in core_ids and hit["axis"] == axis)
            axis_histograms[axis][count] += seconds

    sample_weight = round(total_seconds / 60, 6)
    payload = {
        "id": f"bazi-{BASELINE_VERSION}-{day_boundary}",
        "chart_type": "bazi",
        "kind": "calendar_sample_frequency",
        "label": "1924立春—2044立春历法样本",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": "Asia/Shanghai",
        "day_boundary": day_boundary,
        "engine": "sxtwl 2.0.7",
        "rules_version": RULES_VERSION,
        "sample_unit": "minute",
        "sample_weight": sample_weight,
        "method": "按四柱变化边界分段穷举，并按每段实际持续分钟数加权。",
        "features": {
            feature_id: {"hit_weight": round(seconds / 60, 6)}
            for feature_id, seconds in sorted(feature_weights.items())
        },
        "axis_histograms": {
            axis: {str(count): round(seconds / 60, 6) for count, seconds in sorted(histogram.items())}
            for axis, histogram in axis_histograms.items()
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload["hash"] = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for mode in ("forward", "current"):
        payload = generate(mode)
        path = args.output / f"{payload['id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(f"{path}: {payload['sample_weight']:.0f} minute weight, {payload['hash']}")


if __name__ == "__main__":
    main()


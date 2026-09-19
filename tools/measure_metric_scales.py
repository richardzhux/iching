#!/usr/bin/env python3
"""Measure the reference scales the BaZi synthesis ranks against.

`build_consumer_synthesis` leads each theme on whichever metric this chart
deviates furthest from the population on. That needs a population: raw counts
are not comparable across metrics, because 关系 counts average 5.3 while 日干合
averages 0.31. Ranking by raw value made 关系 the lead on 70-90% of charts.

It also prints the tercile cutoffs for the day-master strength score. Both sets
of constants live in `bazi_structure.py`; re-run this after changing the metric
registry or the strength weights, and paste the output back.

    python tools/measure_metric_scales.py --samples 2500
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from iching.core.bazi_structure import (  # noqa: E402
    STEM_ELEMENTS,
    build_structure_profile,
    day_master_strength,
)
from iching.core.calendar_engine import STEMS, calculate_calendar_facts  # noqa: E402
from iching.core.metaphysics import _pillar, _seasonal_status  # noqa: E402
from iching.core.shensha import evaluate_shensha  # noqa: E402

ZONE = "Asia/Shanghai"


def _chart(value: datetime):
    facts = calculate_calendar_facts(
        value, timezone_name=ZONE, day_boundary="forward", crosscheck=False
    )
    day_stem = STEMS[facts.day_gz.tg]
    return [
        _pillar("年", facts.year_gz, day_stem),
        _pillar("月", facts.month_gz, day_stem),
        _pillar("日", facts.day_gz, day_stem),
        _pillar("时", facts.hour_gz, day_stem),
    ]


def _roots(pillars) -> list[str]:
    day_element = STEM_ELEMENTS[str(pillars[2]["stem"])]
    return [
        str(pillar.get("label", ""))
        for pillar in pillars
        if any(
            STEM_ELEMENTS.get(str(hidden.get("stem", ""))) == day_element
            for hidden in pillar.get("hidden_stems", ()) or ()
        )
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=2500)
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--start-year", type=int, default=1950)
    parser.add_argument("--end-year", type=int, default=2012)
    args = parser.parse_args()

    random.seed(args.seed)
    zone = ZoneInfo(ZONE)
    values: dict[tuple[str, str], list[int]] = defaultdict(list)
    scores: list[float] = []
    counted = 0

    for _ in range(args.samples):
        moment = datetime(
            random.randint(args.start_year, args.end_year),
            random.randint(1, 12),
            random.randint(1, 28),
            random.randint(0, 23),
            random.randint(0, 59),
            tzinfo=zone,
        )
        try:
            pillars = _chart(moment)
        except Exception:
            continue
        roots = _roots(pillars)
        seasonal = _seasonal_status(pillars[1]["branch"])
        profile = build_structure_profile(
            pillars,
            gender=random.choice(["male", "female"]),
            shensha_hits=evaluate_shensha(pillars),
            seasonal_status=seasonal,
        )
        counted += 1
        scores.append(
            day_master_strength(pillars, seasonal_status=seasonal, roots=roots)["score"]
        )
        for theme_profile in profile["theme_profiles"]:
            theme = str(theme_profile["theme"])
            for metric in theme_profile["structure_metrics"]:
                if metric.get("metric_type") == "ordinal":
                    values[(theme, str(metric["metric_id"]))].append(int(metric["value"]))

    print(f"# measured over {counted} charts, {args.start_year}-{args.end_year}")
    print("METRIC_SCALES: dict[str, dict[str, tuple[float, float]]] = {")
    by_theme: dict[str, list[tuple[str, float, float]]] = defaultdict(list)
    for (theme, metric_id), samples in values.items():
        by_theme[theme].append(
            (metric_id, round(statistics.mean(samples), 3), round(statistics.pstdev(samples) or 1.0, 3))
        )
    for theme in sorted(by_theme):
        print(f'    "{theme}": {{')
        for metric_id, mean, sd in sorted(by_theme[theme]):
            print(f'        "{metric_id}": ({mean}, {sd}),')
        print("    },")
    print("}")

    scores.sort()
    lower = scores[len(scores) // 3]
    upper = scores[(len(scores) * 2) // 3]
    print()
    print(f"STRENGTH_LOWER_TERCILE = {lower:.2f}")
    print(f"STRENGTH_UPPER_TERCILE = {upper:.2f}")


if __name__ == "__main__":
    main()

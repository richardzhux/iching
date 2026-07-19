from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


_ALIASES = {
    "direct_wealth": {"direct_wealth", "wealth"},
    "indirect_wealth": {"indirect_wealth", "wealth"},
    "direct_resource": {"direct_resource", "resource"},
    "indirect_resource": {"indirect_resource", "resource"},
    "month_prosperity": {"month_prosperity", "prosperity_robbery"},
    "month_robbery": {"month_robbery", "prosperity_robbery"},
}


@lru_cache(maxsize=1)
def load_pattern_product_catalog() -> dict[str, Any]:
    path = files("iching.core").joinpath("data/pattern-product-catalog-v1.json")
    return json.loads(path.read_text(encoding="utf-8"))


def pattern_library(pattern_id: str) -> dict[str, Any]:
    catalog = load_pattern_product_catalog()
    pattern_ids = _ALIASES.get(pattern_id, {pattern_id})
    groups = [
        group
        for group in catalog.get("groups", ())
        if str(group.get("pattern_id", "")) in pattern_ids
    ]
    rules = [rule for group in groups for rule in group.get("rules", ())]
    examples = [example for group in groups for example in group.get("examples", ())]
    return {
        "version": catalog["version"],
        "digest": catalog["digest"],
        "pattern_id": pattern_id,
        "label": " / ".join(
            dict.fromkeys(str(group.get("label", pattern_id)) for group in groups)
        )
        or pattern_id,
        "candidate_count": len(rules),
        "executable_count": sum(bool(rule.get("execution_ready")) for rule in rules),
        "status_counts": {
            status: sum(rule.get("terminal_status") == status for rule in rules)
            for status in ("executable", "contextual", "example_only", "deferred")
        },
        "examples": examples,
    }


__all__ = ["load_pattern_product_catalog", "pattern_library"]

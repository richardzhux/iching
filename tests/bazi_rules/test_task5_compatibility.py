from __future__ import annotations

import hashlib
from importlib import resources
from typing import Any

from iching.core.bazi_rules.adapter import build_source_backed_shadow
from iching.core.bazi_rules.fact_graph import build_bazi_fact_graph
from iching.core.bazi_rules.registry import (
    TASK4_SHADOW_BUNDLE_DIGEST,
    TASK4_SHADOW_BUNDLE_ID,
    TASK4_SHADOW_RESOURCE,
    TASK4_SHADOW_RESOURCE_SHA256,
    load_packaged_shen_registry,
    load_packaged_task4_shadow_registry,
)


TASK4_RULE_IDS = {
    "zzq.rule.officer.form-wealth-support-001",
    "zzq.rule.officer.form-seal-support-001",
    "zzq.rule.officer.form-dual-support-001",
    "zzq.rule.officer.damage-mixed-killing-001",
    "zzq.rule.officer.damage-hurting-officer-001",
    "zzq.rule.officer.damage-wealth-breaks-seal-001",
    "zzq.rule.officer.rescue-hurting-seal-001",
    "zzq.rule.useful.rescue-officer-002",
    "zzq.rule.officer.form-single-support-001",
}


def _chart(*texts: str) -> list[dict[str, Any]]:
    return [
        {"label": label, "stem": text[0], "branch": text[1], "text": text}
        for label, text in zip(("年", "月", "日", "时"), texts)
    ]


def test_task4_shadow_resource_is_an_exact_immutable_package_blob() -> None:
    resource = resources.files("iching.core.bazi_rules").joinpath(
        "bundles", TASK4_SHADOW_RESOURCE
    )
    payload = resource.read_bytes()

    assert len(payload) == 22_613
    assert hashlib.sha256(payload).hexdigest() == TASK4_SHADOW_RESOURCE_SHA256

    registry = load_packaged_task4_shadow_registry()
    assert registry is load_packaged_task4_shadow_registry()
    assert registry.bundle_id == TASK4_SHADOW_BUNDLE_ID
    assert registry.bundle_digest == TASK4_SHADOW_BUNDLE_DIGEST
    assert registry.authority_layer == "shen_core"
    assert set(registry.rules_by_id) == TASK4_RULE_IDS
    assert not any(rule.stage == "candidate" for rule in registry.rules)


def test_shadow_separates_frozen_generic_projection_from_task5_pattern_set() -> None:
    pillars = _chart("庚寅", "乙酉", "甲子", "戊辰")
    canonical = load_packaged_shen_registry()

    shadow = build_source_backed_shadow(
        pillars,
        {"ordinary": []},
        build_bazi_fact_graph(pillars),
    )

    assert shadow["bundle_id"] == TASK4_SHADOW_BUNDLE_ID
    assert shadow["bundle_digest"] == TASK4_SHADOW_BUNDLE_DIGEST
    assert shadow["generic_result"]["bundle_digest"] == TASK4_SHADOW_BUNDLE_DIGEST
    assert shadow["pattern_set"]["bundle_id"] == canonical.bundle_id
    assert shadow["pattern_set"]["bundle_digest"] == canonical.bundle_digest
    canonical_officer = next(
        item
        for item in shadow["pattern_set"]["patterns"]
        if item["pattern_id"] == "direct_officer"
    )
    assert canonical_officer["bundle_digest"] == canonical.bundle_digest
    assert canonical_officer != shadow["generic_result"]
    assert shadow["overlay_results"] == []

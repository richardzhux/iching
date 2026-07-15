"""Source-backed Zi Ping fact and rule primitives."""

from iching.core.bazi_rules.compiler import (
    COMPILER_VERSION,
    canonical_digest,
    compile_rule_bundle,
    compile_rule_records,
    hydrate_propositions,
    index_hydrated_propositions,
    ingest_rule_definitions,
    load_hydrated_propositions,
)
from iching.core.bazi_rules.fact_graph import (
    FACT_GRAPH_VERSION,
    build_bazi_fact_envelope,
    build_bazi_fact_graph,
)
from iching.core.bazi_rules.predicates import (
    FACT_PATH_REGISTRY,
    OPERATORS,
    PREDICATE_VERSION,
    evaluate_predicate,
    parse_predicate,
)
from iching.core.bazi_rules.primitives import PRIMITIVES_VERSION
from iching.core.bazi_rules.schema import (
    BaziFactEnvelope,
    BaziFactGraph,
    CompiledRuleBundle,
    EvaluationResult,
    PredicateNode,
    Proposition,
    RuleDefinition,
    TruthValue,
)

__all__ = [
    "BaziFactEnvelope",
    "BaziFactGraph",
    "COMPILER_VERSION",
    "CompiledRuleBundle",
    "EvaluationResult",
    "FACT_GRAPH_VERSION",
    "FACT_PATH_REGISTRY",
    "OPERATORS",
    "PREDICATE_VERSION",
    "PRIMITIVES_VERSION",
    "PredicateNode",
    "Proposition",
    "RuleDefinition",
    "TruthValue",
    "build_bazi_fact_envelope",
    "build_bazi_fact_graph",
    "canonical_digest",
    "compile_rule_bundle",
    "compile_rule_records",
    "evaluate_predicate",
    "hydrate_propositions",
    "index_hydrated_propositions",
    "ingest_rule_definitions",
    "load_hydrated_propositions",
    "parse_predicate",
]

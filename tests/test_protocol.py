"""Integrity checks for the research protocol artefacts (offline, no LLM calls)."""

import json
import math
from pathlib import Path
from typing import Any

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
PROTOCOL: dict[str, Any] = json.loads((DOCS / "protocol" / "protocol.json").read_text("utf-8"))
EXAMPLES: list[dict[str, Any]] = json.loads(
    (DOCS / "protocol" / "reference_examples.json").read_text("utf-8")
)["examples"]
# Backticks are stripped so markdown tables can be compared with the JSON values.
PROTOCOL_MD = (DOCS / "EXPERIMENT_PROTOCOL.md").read_text("utf-8").replace("`", "")
DECISIONS_MD = (DOCS / "DECISIONS.md").read_text("utf-8")

CLASSES: list[str] = [c["id"] for c in PROTOCOL["classes"]]
COST: dict[str, Any] = PROTOCOL["classification_cost"]
MATRIX: list[list[float]] = COST["values"]
OTHER = "OTHER_OR_UNCLEAR"
POLICY: dict[str, Any] = PROTOCOL["action_policy"]
REASON_IDS: set[str] = {r["id"] for r in PROTOCOL["review_reasons"]}
GATE_RULES: dict[str, str] = {
    r["id"]: r["gate_rule"] for r in PROTOCOL["review_reasons"] if r["mandatory_rule"]
}
PRIORITY: dict[str, int] = {c["id"]: c["priority"] for c in PROTOCOL["classes"]}


def test_taxonomy_has_five_classes_with_unique_priorities() -> None:
    assert len(CLASSES) == 5
    assert COST["order"] == [
        "PAYMENT_PROMISE",
        "PAYMENT_CLAIM",
        "PAYMENT_PLAN_REQUEST",
        "INVOICE_DISPUTE",
        OTHER,
    ]
    assert set(COST["order"]) == set(CLASSES)
    assert sorted(PRIORITY.values()) == [1, 2, 3, 4, 5]
    by_priority = sorted((c for c in CLASSES if c != OTHER), key=PRIORITY.__getitem__)
    assert PROTOCOL["multi_intent_priority"] == by_priority
    assert PRIORITY[OTHER] == 5


def test_cost_matrix_is_valid() -> None:
    assert len(MATRIX) == 5 and all(len(row) == 5 for row in MATRIX)
    top = COST["scale"]["max"]
    for i, row in enumerate(MATRIX):
        assert row[i] == 0
        for j, v in enumerate(row):
            assert math.isfinite(v) and 0 <= v <= top
            if i != j:
                assert v > 0, "off-diagonal errors must have a positive cost"


def test_cost_matrix_is_asymmetric_where_justified() -> None:
    idx = {c: i for i, c in enumerate(COST["order"])}
    dispute, promise = idx["INVOICE_DISPUTE"], idx["PAYMENT_PROMISE"]
    assert MATRIX[dispute][promise] > MATRIX[promise][dispute]


def test_critical_classes_are_derived_from_matrix() -> None:
    threshold = COST["critical_class_rule"]["min_max_row_cost"]
    derived = {c for c, row in zip(COST["order"], MATRIX, strict=True) if max(row) >= threshold}
    assert derived == set(COST["critical_classes"])


def test_markdown_matrix_matches_json() -> None:
    for name, row in zip(COST["order"], MATRIX, strict=True):
        line = f"| {name} | " + " | ".join(str(int(v)) for v in row) + " |"
        assert line in PROTOCOL_MD, f"matrix row not in protocol: {line}"


def test_routing_costs() -> None:
    routing = PROTOCOL["routing_cost"]
    fn = routing["false_negative_by_gold_class"]
    assert set(fn) == set(CLASSES)
    assert routing["true_positive"] == 0 and routing["true_negative"] == 0
    assert 0 < routing["false_positive"] < min(fn.values())
    assert all(math.isfinite(v) for v in fn.values())


def test_action_policy_invariants() -> None:
    assert POLICY["always_true"]["external_communication_requires_human_approval"] is True
    assert POLICY["always_true"]["may_modify_accounting_data"] is False
    assert POLICY["always_true"]["may_confirm_payment_from_client_statement"] is False
    forbidden = set(POLICY["always_forbidden"])
    assert {"confirm_payment", "modify_accounting_data", "send_external_without_approval"} <= (
        forbidden
    )
    for profile in POLICY["profiles"].values():
        assert set(profile["allowed"]) <= set(POLICY["tools"])
        assert not set(profile["allowed"]) & forbidden
    rules = POLICY["mapping_first_match"]
    assert {rule["profile"] for rule in rules} == set(POLICY["profiles"])
    assert rules[-1].get("default") is True
    # Every mandatory rule fires the profile with mandatory review; the gate never reads gold.
    assert set(rules[0]["if_any_gate_rule"]) == set(GATE_RULES.values())
    assert POLICY["profiles"][rules[0]["profile"]]["mandatory_review"] is True
    assert "never from annotations" in POLICY["decided_by"]


def test_review_reasons_drop_rv4_and_keep_mandatory_rules() -> None:
    assert {"RV1", "RV2", "RV3", "RV5", "RV6", "RV7", "RV8"} == REASON_IDS
    assert [r["id"] for r in PROTOCOL["removed_review_reasons"]] == ["RV4"]
    assert GATE_RULES == {"RV5": "MR1", "RV6": "MR2", "RV7": "MR3"}
    assert "broken_promises_for_rv4" not in PROTOCOL["review_thresholds"]
    assert "risk_flags" not in PROTOCOL


def test_experiment_parameters_are_coherent() -> None:
    exp = PROTOCOL["experiment"]
    splits = exp["splits"]
    assert splits["initial_memory_n0"] <= splits["seed_stock"]
    assert 100 <= splits["test"] <= 150
    assert 20 <= splits["initial_memory_n0"] <= 30
    assert splits["test_min_per_class"] * 5 <= splits["test"]
    assert splits["split_unit"] == "customer_id"
    assert exp["annotation_budget"] == 40
    assert exp["eval_points"][0] == 0
    assert exp["eval_points"][-1] == exp["annotation_budget"]
    assert exp["annotation_budget"] % exp["round_size"] == 0
    assert exp["eval_points"] == list(range(0, 41, exp["round_size"]))
    assert set(exp["e2"]["s2_memory_sources"]) <= set(exp["strategies"])
    ablations = exp["risk_aware"]["ablations"]
    assert len({tuple(a) for a in ablations}) == 7
    assert all(set(a) <= {"U", "R", "D"} and a for a in ablations)
    assert exp["llm_calls"]["votes_n"] >= exp["risk_aware"]["min_valid_votes"]
    stats = exp["statistics"]
    assert stats["multiplicity"] == "holm" and stats["ci_multiplicity_adjusted"] is False
    assert "inversão de sinal" in PROTOCOL_MD and "não ajustados" in PROTOCOL_MD
    assert "sem correção +1" in PROTOCOL_MD and "com correção +1" in PROTOCOL_MD


def test_documents_reference_every_protocol_identifier() -> None:
    names = (
        CLASSES
        + sorted(REASON_IDS)
        + list(GATE_RULES.values())
        + list(POLICY["profiles"])
        + list(PROTOCOL["experiment"]["strategies"])
        + ["S0", "S1", "S2"]
    )
    missing = [n for n in names if n not in PROTOCOL_MD]
    assert not missing, f"not documented in EXPERIMENT_PROTOCOL.md: {missing}"
    assert f"Versão:** {PROTOCOL['protocol_version']}" in PROTOCOL_MD
    decisions = [f"D{i:02d}" for i in range(1, 18)]
    assert [d for d in decisions if f"## {d} " not in DECISIONS_MD] == []


def test_reference_examples_cover_the_required_scenarios() -> None:
    assert len(EXAMPLES) >= 10
    assert len({e["id"] for e in EXAMPLES}) == len(EXAMPLES)
    assert {e["message_label"] for e in EXAMPLES} == set(CLASSES)
    assert {r for e in EXAMPLES for r in e["review_reasons"]} == REASON_IDS
    # needs_additional_review must not be a function of the class (E2 would be trivial).
    for label in ("PAYMENT_PROMISE", "PAYMENT_CLAIM", "PAYMENT_PLAN_REQUEST", OTHER):
        assert {e["needs_additional_review"] for e in EXAMPLES if e["message_label"] == label} == {
            True,
            False,
        }


@pytest.mark.parametrize("ex", EXAMPLES, ids=[e["id"] for e in EXAMPLES])
def test_reference_example_follows_the_rules(ex: dict[str, Any]) -> None:
    label: str = ex["message_label"]
    reasons: list[str] = ex["review_reasons"]
    assert set(ex) == {
        "id",
        "title",
        "message",
        "context",
        "message_label",
        "review_reasons",
        "needs_additional_review",
        "rationale",
    }
    assert label in CLASSES
    assert set(reasons) <= REASON_IDS
    assert ex["needs_additional_review"] is bool(reasons)
    if label == "INVOICE_DISPUTE":
        assert "RV1" in reasons
    if "RV8" in reasons:
        assert label == OTHER
    th = PROTOCOL["review_thresholds"]
    if (
        label == "PAYMENT_PLAN_REQUEST"
        and ex["context"]["pending_amount_eur"] >= th["high_value_pending_eur"]
    ):
        assert "RV3" in reasons

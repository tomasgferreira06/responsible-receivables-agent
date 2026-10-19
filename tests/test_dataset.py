"""Checks for the static synthetic dataset (T03). Offline; no LLM calls.

Passing these tests means the files are internally consistent with the T02 rules. It is not
evidence of linguistic quality or of independent human validation (see docs/DATASET_CARD.md).
"""

import copy
from collections import Counter
from datetime import datetime
from typing import Any

import pytest

from responsible_receivables_agent import dataset as ds

CASES = ds.load_cases()
ANNS = ds.load_annotations()
ANN = {a["case_id"]: a for a in ANNS}
SPLITS = ds.load_splits()
MANDATORY = {r["id"] for r in ds.PROTOCOL["review_reasons"] if r["mandatory_rule"]}
GROUP_KEYS = ("customer_id", "scenario_id", "family_id")


# ---------------------------------------------------------------------------- integrity


def test_records_and_annotations_are_valid() -> None:
    assert ds.validate_records(CASES, ANNS) == []


def test_dataset_has_the_protocol_size_and_unique_ids() -> None:
    assert len(CASES) == len(ANNS) == sum(ds.SPLIT_SIZES.values()) == 510
    assert len({c["case_id"] for c in CASES}) == 510
    assert [c["case_id"] for c in CASES] == [a["case_id"] for a in ANNS]


def test_loading_is_deterministic() -> None:
    assert ds.load_cases() == CASES and ds.load_annotations() == ANNS


# ---------------------------------------------------------------------------- annotations


def test_every_class_rule_flag_and_policy_is_covered() -> None:
    assert {a["message_label"] for a in ANNS} == set(ds.CLASSES)
    assert {r for a in ANNS for r in a["review_reasons"]} == set(ds.REASONS)
    assert {f for a in ANNS for f in a["risk_flags"]} == set(ds.FLAGS)
    assert {a["action_policy"] for a in ANNS} == set(ds.PROTOCOL["action_policy"]["profiles"])
    assert sum(bool(a["secondary_intents"]) for a in ANNS) >= 25


def test_review_is_not_a_function_of_the_label() -> None:
    # INVOICE_DISPUTE always triggers RV1 by protocol; every other class must have both outcomes.
    for label in set(ds.CLASSES) - {"INVOICE_DISPUTE"}:
        outcomes = {a["needs_additional_review"] for a in ANNS if a["message_label"] == label}
        assert outcomes == {True, False}, label
    assert any(
        a["message_label"] == ds.OTHER and MANDATORY & set(a["review_reasons"]) for a in ANNS
    )
    # A legitimate intent carrying a malicious instruction keeps its own label.
    assert any(a["message_label"] != ds.OTHER and "RV6" in a["review_reasons"] for a in ANNS)


def test_mandatory_rules_force_mandatory_profiles() -> None:
    for a in ANNS:
        profile = ds.PROTOCOL["action_policy"]["profiles"][a["action_policy"]]
        assert profile["mandatory_review"] == bool(MANDATORY & set(a["review_reasons"]))


def test_claims_are_never_treated_as_confirmed_payments() -> None:
    assert "confirm_payment" in ds.PROTOCOL["action_policy"]["always_forbidden"]
    for a in ANNS:
        allowed = ds.PROTOCOL["action_policy"]["profiles"][a["action_policy"]]["allowed"]
        assert "confirm_payment" not in allowed
        assert not any("confirm" in key for key in a["rv_facts"])


def _first(pred: Any) -> str:
    return next(str(a["case_id"]) for a in ANNS if pred(a))


def _errors_after(case_id: str, **changes: Any) -> list[str]:
    anns = copy.deepcopy(ANNS)
    next(a for a in anns if a["case_id"] == case_id).update(changes)
    return ds.validate_records(CASES, anns)


def test_validator_rejects_rule_violations() -> None:
    dispute = _first(lambda a: a["message_label"] == "INVOICE_DISPUTE" and not a["risk_flags"])
    assert _errors_after(dispute, review_reasons=[], needs_additional_review=False)
    lockdown = _first(lambda a: a["action_policy"] == "AP_SECURITY_LOCKDOWN")
    assert _errors_after(lockdown, action_policy="AP_STANDARD")
    contradiction = _first(lambda a: "contradictory_statements" in a["risk_flags"])
    assert _errors_after(contradiction, message_label="PAYMENT_CLAIM")
    claim = _first(lambda a: a["situation"] == "claim_complete")
    assert _errors_after(claim, rv_facts={**ANN[claim]["rv_facts"], "claim_has_date": False})
    assert _errors_after(claim, needs_adjudication=True)


def test_weekday_mentions_are_checked() -> None:
    received = datetime(2026, 10, 12, 10, 0)
    assert ds.weekday_mismatches("pago na sexta, dia 16", received) == []
    assert ds.weekday_mismatches("pago na segunda, dia 16", received) == ["segunda 16"]


# ---------------------------------------------------------------------------- quality


def test_no_exact_or_near_duplicates() -> None:
    assert ds.exact_duplicates(CASES) == []
    assert ds.near_duplicate_pairs(CASES) == []


def test_formulation_families_are_real_and_small() -> None:
    assert ds.family_audit(CASES) == []
    sizes = Counter(c["family_id"] for c in CASES)
    assert sum(n > 1 for n in sizes.values()) >= 5
    assert max(sizes.values()) <= 6
    assert max(len(c) for c in ds.components(CASES)) <= 20


def test_test_split_meets_protocol_minima() -> None:
    exp = ds.PROTOCOL["experiment"]["splits"]
    labels = Counter(ANN[cid]["message_label"] for cid in SPLITS["test"])
    assert min(labels[c] for c in ds.CLASSES) >= exp["test_min_per_class"]
    critical = ds.PROTOCOL["classification_cost"]["critical_classes"]
    assert sum(labels[c] for c in critical) >= exp["test_min_critical_class_items"]
    discretionary = [
        ANN[cid] for cid in SPLITS["test"] if not MANDATORY & set(ANN[cid]["review_reasons"])
    ]
    reviews = Counter(a["needs_additional_review"] for a in discretionary)
    assert reviews[True] >= 30 and reviews[False] >= 30


# ---------------------------------------------------------------------------- splits / leakage


def test_splits_respect_sizes_groups_and_near_duplicates() -> None:
    assert ds.check_splits(CASES, ANNS, SPLITS) == []


def test_test_cases_and_groups_never_reach_other_splits() -> None:
    test = set(SPLITS["test"])
    for other in ("seed_stock", "pool", "validation"):
        assert not test & set(SPLITS[other])
    test_groups = {(k, c[k]) for c in CASES if c["case_id"] in test for k in GROUP_KEYS}
    for c in CASES:
        if c["case_id"] not in test:
            assert not test_groups & {(k, c[k]) for k in GROUP_KEYS}


# ---------------------------------------------------------------------------- reproducibility


def test_splits_are_reproducible_from_the_fixed_seed() -> None:
    assert ds.assign_splits(CASES, ANNS) == SPLITS


def test_manifest_matches_files_and_hashes_are_stable() -> None:
    assert ds.check_hashes() == []
    assert ds.file_sha256(ds.CASES_PATH) == ds.file_sha256(ds.CASES_PATH)
    assert ds.sha256(ds.canonical_jsonl(CASES)) == ds.sha256(ds.canonical_jsonl(reversed(CASES)))


# ---------------------------------------------------------------------------- isolation


def test_inference_view_hides_gold_and_grouping() -> None:
    hidden = (set(ds.ANNOTATION_FIELDS) - {"case_id"}) | {"scenario_id", "family_id"}
    gold_values = set(ds.CLASSES) | set(ds.PROTOCOL["action_policy"]["profiles"]) | set(ds.REASONS)
    for split in ds.SPLITS:
        for row in ds.inference_split(split):
            assert set(row) == set(ds.INFERENCE_FIELDS)
            assert not hidden & set(row)
            assert not gold_values & {v for v in row.values() if isinstance(v, str)}


def test_gold_access_is_controlled() -> None:
    with pytest.raises(PermissionError):
        ds.load_gold("pool")
    with pytest.raises(PermissionError):
        ds.load_gold("test")
    assert set(ds.load_gold("validation")) == set(SPLITS["validation"])
    assert set(ds.load_gold("test", unlock_test=True)) == set(SPLITS["test"])


def test_oracle_answers_only_queried_pool_cases() -> None:
    oracle = ds.Oracle()
    pool_id = SPLITS["pool"][0]
    answer = oracle.query([pool_id])
    assert set(answer) == {pool_id} and set(answer[pool_id]) == set(ds.GOLD_FIELDS)
    assert oracle.queried == [pool_id]
    for split in ("test", "validation", "seed_stock"):
        with pytest.raises(PermissionError):
            oracle.query([SPLITS[split][0]])
    assert oracle.queried == [pool_id]

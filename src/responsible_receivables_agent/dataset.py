"""Static synthetic dataset (T03): loading, validation, splits, leakage checks and manifests.

No message text is produced here. The messages are fixed, versioned files under
``data/dataset/``; this module only reads, checks, splits and hashes them.

Usage: ``uv run --locked python -m responsible_receivables_agent.dataset <command>``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "dataset"
CASES_PATH = DATA_DIR / "cases.jsonl"
ANNOTATIONS_PATH = DATA_DIR / "annotations.jsonl"
SPLITS_PATH = DATA_DIR / "splits.json"
MANIFEST_PATH = DATA_DIR / "manifest.json"
PROTOCOL: dict[str, Any] = json.loads(
    (ROOT / "docs" / "protocol" / "protocol.json").read_text("utf-8")
)

DATASET_VERSION = "1.0.0-candidate"
SPLIT_SEED = 20261019
SPLITS = ("seed_stock", "pool", "validation", "test")
CLASSES: list[str] = [c["id"] for c in PROTOCOL["classes"]]
PRIORITY: dict[str, int] = {c["id"]: c["priority"] for c in PROTOCOL["classes"]}
OTHER = "OTHER_OR_UNCLEAR"
FLAGS: dict[str, str | None] = PROTOCOL["risk_flags"]
REASONS = [r["id"] for r in PROTOCOL["review_reasons"]]
THRESHOLDS: dict[str, int] = PROTOCOL["review_thresholds"]
SPLIT_SIZES: dict[str, int] = {s: PROTOCOL["experiment"]["splits"][s] for s in SPLITS}
JACCARD_MAX: float = PROTOCOL["experiment"]["leakage"]["near_duplicate_char5gram_jaccard"]
# Dataset rule (DECISIONS D16), stricter than the protocol near-duplicate threshold: messages of
# different customers this similar share a formulation origin and must share a family_id.
FAMILY_AUDIT_JACCARD = 0.35

CASE_FIELDS = (
    "case_id",
    "customer_id",
    "invoice_id",
    "scenario_id",
    "family_id",
    "pending_amount_eur",
    "due_date",
    "snapshot_date",
    "broken_promises_count",
    "received_at",
    "message_subject",
    "message_text",
)
# Grouping ids are internal to the split procedure (protocol 8.2.5): never shown to the selector.
INFERENCE_FIELDS = tuple(f for f in CASE_FIELDS if f not in ("scenario_id", "family_id"))
GOLD_FIELDS = (
    "message_label",
    "secondary_intents",
    "needs_additional_review",
    "review_reasons",
    "risk_flags",
    "action_policy",
)
ANNOTATION_FIELDS = (
    "case_id",
    *GOLD_FIELDS,
    "rv_facts",
    "situation",
    "rationale",
    "needs_adjudication",
    "annotation_status",
    "authoring_batch",
)
RV_FACT_FIELDS = (
    "claimed_amount_eur",
    "claim_has_date",
    "claim_has_means",
    "claim_third_party",
    "plan_total_months",
)
ANNOTATION_STATUS = "ai_proposed_rule_checked_ai_reviewed"
SITUATIONS = frozenset(
    {
        # PAYMENT_PROMISE
        "promise_fixed_date",
        "promise_short_window",
        "promise_conditional",
        "promise_after_broken",
        # PAYMENT_CLAIM
        "claim_complete",
        "claim_partial",
        "claim_proof_mentioned",
        "claim_incomplete",
        "claim_inconsistent",
        "claim_third_party",
        "claim_with_other_intent",
        # PAYMENT_PLAN_REQUEST
        "plan_installments",
        "plan_deferral",
        "plan_renegotiation",
        "plan_high_value",
        "plan_long",
        "plan_after_broken",
        "plan_insolvency",
        # INVOICE_DISPUTE
        "dispute_amount",
        "dispute_service_not_rendered",
        "dispute_quantity",
        "dispute_billing_error",
        "dispute_credit_note",
        "dispute_obligation",
        "dispute_partial",
        "dispute_with_claim",
        "dispute_conditional_promise",
        "dispute_with_plan",
        # OTHER_OR_UNCLEAR
        "document_request",
        "clarification_question",
        "vague_reply",
        "vague_promise",
        "out_of_office",
        "contradiction",
        "iban_change",
        "agent_instruction",
        "legal_threat",
        "insolvency_notice",
        "unrelated",
        # Any class: a legitimate intent combined with a mandatory-rule trigger
        "intent_with_agent_instruction",
        "intent_with_iban_change",
        "intent_with_legal_threat",
    }
)
WEEKDAYS = {"segunda": 0, "terça": 1, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4}
WEEKDAY_DATE = re.compile(
    r"\b(segunda|terça|terca|quarta|quinta|sexta)(?:-feira)?,?\s+(?:dia\s+)?(\d{1,2})\b",
    re.IGNORECASE,
)

Record = dict[str, Any]


# ---------------------------------------------------------------------------- loading


def read_jsonl(path: Path) -> list[Record]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_cases(path: Path = CASES_PATH) -> list[Record]:
    return read_jsonl(path)


def load_annotations(path: Path = ANNOTATIONS_PATH) -> list[Record]:
    return read_jsonl(path)


def load_splits(path: Path = SPLITS_PATH) -> dict[str, list[str]]:
    data: dict[str, Any] = json.loads(path.read_text("utf-8"))
    return {s: list(data["splits"][s]) for s in SPLITS}


def split_of(splits: dict[str, list[str]]) -> dict[str, str]:
    return {cid: s for s, ids in splits.items() for cid in ids}


def inference_view(case: Record) -> Record:
    """Input-only view of a case: no gold labels, no internal grouping ids."""
    return {f: case[f] for f in INFERENCE_FIELDS}


def inference_split(split: str) -> list[Record]:
    """Cases of a split as the classifier/selector may see them."""
    ids = set(load_splits()[split])
    return [inference_view(c) for c in load_cases() if c["case_id"] in ids]


def load_gold(split: str, *, unlock_test: bool = False) -> dict[str, Record]:
    """Gold labels of a split, for evaluation code only. The test split must be unlocked
    explicitly (protocol 8.2.6); the pool is reachable only through ``Oracle``."""
    if split == "pool":
        raise PermissionError("pool labels are only available through Oracle.query")
    if split == "test" and not unlock_test:
        raise PermissionError("test gold is sealed; pass unlock_test=True in final evaluation")
    ids = set(load_splits()[split])
    return {
        a["case_id"]: {f: a[f] for f in GOLD_FIELDS}
        for a in load_annotations()
        if a["case_id"] in ids
    }


class Oracle:
    """Simulated annotator (protocol 8.2.10): returns pool labels only for queried ids."""

    def __init__(self) -> None:
        pool = set(load_splits()["pool"])
        self._gold = {
            a["case_id"]: {f: a[f] for f in GOLD_FIELDS}
            for a in load_annotations()
            if a["case_id"] in pool
        }
        self.queried: list[str] = []

    def query(self, case_ids: Iterable[str]) -> dict[str, Record]:
        ids = list(case_ids)
        outside = [cid for cid in ids if cid not in self._gold]
        if outside:
            raise PermissionError(f"oracle only answers pool cases: {outside}")
        self.queried.extend(ids)
        return {cid: dict(self._gold[cid]) for cid in ids}


# ---------------------------------------------------------------------------- rules


def derive_policy(flags: Iterable[str]) -> str:
    present = set(flags)
    for rule in PROTOCOL["action_policy"]["mapping_first_match"]:
        if rule.get("default") or set(rule["if_any_flag"]) & present:
            return str(rule["profile"])
    raise AssertionError("protocol mapping has no default")


def money(value: Any) -> Decimal | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d+\.\d{2}", value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def expected_reasons(case: Record, ann: Record) -> set[str]:
    """Review reasons implied by the protocol given the annotated intents, flags and facts.

    Interpretations recorded in docs/DECISIONS.md (GAP-01..GAP-04): RV2/RV3/RV4 are not
    applied to intents that are part of a contradiction (REF12); RV3/RV4 apply to
    promise/plan intents, principal or secondary.
    """
    intents = {ann["message_label"], *ann["secondary_intents"]}
    flags = set(ann["risk_flags"])
    facts = ann["rv_facts"]
    contradictory = "contradictory_statements" in flags
    reasons = {r for f, r in FLAGS.items() if r and f in flags}
    if "INVOICE_DISPUTE" in intents:
        reasons.add("RV1")
    pending = money(case["pending_amount_eur"])
    if "PAYMENT_CLAIM" in intents and not contradictory:
        amount = money(facts["claimed_amount_eur"])
        incomplete = amount is None or not facts["claim_has_date"] or not facts["claim_has_means"]
        inconsistent = bool(facts["claim_third_party"]) or (
            amount is not None and pending is not None and amount > pending
        )
        if incomplete or inconsistent:
            reasons.add("RV2")
    if "PAYMENT_PLAN_REQUEST" in intents and not contradictory:
        months = facts["plan_total_months"]
        if (pending is not None and pending >= THRESHOLDS["high_value_pending_eur"]) or (
            isinstance(months, int) and months > THRESHOLDS["long_plan_months"]
        ):
            reasons.add("RV3")
    if (
        intents & {"PAYMENT_PROMISE", "PAYMENT_PLAN_REQUEST"}
        and not contradictory
        and case["broken_promises_count"] >= THRESHOLDS["broken_promises_for_rv4"]
    ):
        reasons.add("RV4")
    return reasons


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def weekday_mismatches(text: str, received: datetime) -> list[str]:
    """Mentions like 'sexta-feira, dia 23' whose weekday does not match the first such day of
    the month from 10 days before the message onwards (recent past or near future)."""
    start = received.date() - timedelta(days=10)
    bad = []
    for name, day in WEEKDAY_DATE.findall(text):
        match = next(
            start + timedelta(i) for i in range(32) if (start + timedelta(i)).day == int(day)
        )
        if match.weekday() != WEEKDAYS[name.lower()]:
            bad.append(f"{name} {day}")
    return bad


def validate_records(cases: list[Record], annotations: list[Record]) -> list[str]:
    errors: list[str] = []
    ids = [c.get("case_id") for c in cases]
    if len(set(ids)) != len(ids):
        errors.append("duplicate case_id")
    ann_by_id = {a.get("case_id"): a for a in annotations}
    if len(ann_by_id) != len(annotations):
        errors.append("duplicate annotation case_id")
    if set(ann_by_id) != set(ids):
        errors.append("cases and annotations do not cover the same case_ids")

    invoice_owner: dict[str, str] = {}
    for case in cases:
        cid = case.get("case_id")
        if tuple(case) != CASE_FIELDS:
            errors.append(f"{cid}: case fields {list(case)} != {list(CASE_FIELDS)}")
            continue
        for f in ("case_id", "customer_id", "invoice_id", "scenario_id", "family_id"):
            if not isinstance(case[f], str) or not case[f].strip():
                errors.append(f"{cid}: empty {f}")
        if not isinstance(case["message_text"], str) or len(case["message_text"].strip()) < 3:
            errors.append(f"{cid}: empty message_text")
        if not isinstance(case["message_subject"], str):
            errors.append(f"{cid}: message_subject must be a string (may be empty)")
        owner = invoice_owner.setdefault(case["invoice_id"], case["customer_id"])
        if owner != case["customer_id"]:
            errors.append(f"{cid}: invoice {case['invoice_id']} belongs to another customer")
        amount = money(case["pending_amount_eur"])
        if amount is None or amount <= 0:
            errors.append(f"{cid}: pending_amount_eur must be a positive 'NNNN.NN' string")
        bp = case["broken_promises_count"]
        if not isinstance(bp, int) or isinstance(bp, bool) or bp < 0:
            errors.append(f"{cid}: broken_promises_count must be a non-negative int")
        due, snap = _parse_date(case["due_date"]), _parse_date(case["snapshot_date"])
        received = _parse_datetime(case["received_at"])
        if due is None or snap is None or received is None:
            errors.append(f"{cid}: invalid dates")
            continue
        if not due < snap <= received.date():
            errors.append(f"{cid}: dates must satisfy due_date < snapshot_date <= received_at")
        for bad in weekday_mismatches(case["message_text"], received):
            errors.append(f"{cid}: weekday/date mismatch '{bad}'")

    cases_by_id = {c["case_id"]: c for c in cases if "case_id" in c}
    for ann in annotations:
        cid = ann.get("case_id")
        if tuple(ann) != ANNOTATION_FIELDS:
            errors.append(f"{cid}: annotation fields {list(ann)} != {list(ANNOTATION_FIELDS)}")
            continue
        if cid not in cases_by_id:
            continue
        errors.extend(f"{cid}: {e}" for e in check_annotation(cases_by_id[cid], ann))
    return errors


def check_annotation(case: Record, ann: Record) -> list[str]:
    errors: list[str] = []
    label, secondary = ann["message_label"], ann["secondary_intents"]
    flags, reasons = ann["risk_flags"], ann["review_reasons"]
    if label not in CLASSES:
        return [f"invalid label {label}"]
    if not set(secondary) <= set(CLASSES) - {OTHER} or label in secondary:
        return [f"invalid secondary_intents {secondary}"]
    if len(set(secondary)) != len(secondary) or secondary != sorted(
        secondary, key=PRIORITY.__getitem__
    ):
        errors.append("secondary_intents must be unique and in priority order")
    if not set(flags) <= set(FLAGS) or len(set(flags)) != len(flags):
        errors.append(f"invalid risk_flags {flags}")
    if not set(reasons) <= set(REASONS) or reasons != sorted(set(reasons), key=REASONS.index):
        errors.append(f"review_reasons must be unique, valid and ordered: {reasons}")

    contradictory = "contradictory_statements" in flags
    if label == OTHER:
        if secondary and not contradictory:
            errors.append("OTHER_OR_UNCLEAR has secondary intents without a contradiction")
    else:
        if contradictory:
            errors.append("contradictory_statements requires OTHER_OR_UNCLEAR (protocol 3.6.3)")
        if any(PRIORITY[s] < PRIORITY[label] for s in secondary):
            errors.append("a secondary intent has higher priority than the label (3.6.5)")
        if "insufficient_information" in flags:
            errors.append("insufficient_information only applies to OTHER_OR_UNCLEAR")
    if contradictory and not secondary:
        errors.append("a contradiction must keep the conflicting intents as secondary")

    facts = ann["rv_facts"]
    if not isinstance(facts, dict) or tuple(facts) != RV_FACT_FIELDS:
        return [*errors, f"rv_facts fields must be {list(RV_FACT_FIELDS)}"]
    intents = {label, *secondary}
    has_claim, has_plan = "PAYMENT_CLAIM" in intents, "PAYMENT_PLAN_REQUEST" in intents
    claim_facts = [facts[f] for f in RV_FACT_FIELDS[:4]]
    if has_claim:
        if facts["claimed_amount_eur"] is not None and money(facts["claimed_amount_eur"]) is None:
            errors.append("claimed_amount_eur must be null or a 'NNNN.NN' string")
        if not all(isinstance(v, bool) for v in claim_facts[1:]):
            errors.append("claim facts must be booleans for claims")
    elif any(v is not None for v in claim_facts):
        errors.append("claim facts must be null when there is no PAYMENT_CLAIM intent")
    months = facts["plan_total_months"]
    if months is not None and (not has_plan or not isinstance(months, int) or months < 1):
        errors.append("plan_total_months must be null or a positive int on plan intents")

    expected = expected_reasons(case, ann)
    if set(reasons) != expected:
        errors.append(f"review_reasons {reasons} != expected {sorted(expected)}")
    if ann["needs_additional_review"] is not bool(reasons):
        errors.append("needs_additional_review must equal bool(review_reasons) (protocol 4.2)")
    if ann["action_policy"] != derive_policy(flags):
        errors.append(f"action_policy {ann['action_policy']} != {derive_policy(flags)}")
    if ann["situation"] not in SITUATIONS:
        errors.append(f"unknown situation {ann['situation']}")
    if not isinstance(ann["rationale"], str) or len(ann["rationale"]) < 20:
        errors.append("rationale missing")
    if ann["needs_adjudication"] is not False:
        errors.append("cases flagged for adjudication must be resolved or excluded (3.7)")
    if ann["annotation_status"] != ANNOTATION_STATUS:
        errors.append("unexpected annotation_status")
    return errors


# ---------------------------------------------------------------------------- duplicates


def normalize_text(text: str) -> str:
    """Protocol 8.2.3: lower case, no accents, no punctuation, numbers normalised."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\d+", "0", text)
    text = re.sub(r"[^\w\s]|_", " ", text)
    return " ".join(text.split())


def char_ngrams(text: str, n: int = 5) -> frozenset[str]:
    norm = normalize_text(text)
    return frozenset(norm[i : i + n] for i in range(max(1, len(norm) - n + 1)))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 1.0


def exact_duplicates(cases: list[Record]) -> list[list[str]]:
    by_hash: dict[str, list[str]] = {}
    for c in cases:
        key = hashlib.sha256(normalize_text(c["message_text"]).encode()).hexdigest()
        by_hash.setdefault(key, []).append(c["case_id"])
    return [ids for ids in by_hash.values() if len(ids) > 1]


def near_duplicate_pairs(
    cases: list[Record], threshold: float = JACCARD_MAX
) -> list[tuple[str, str, float]]:
    grams = [(c["case_id"], char_ngrams(c["message_text"])) for c in cases]
    pairs = []
    for i, (a, ga) in enumerate(grams):
        for b, gb in grams[i + 1 :]:
            # Jaccard is bounded by the size ratio; skip pairs that cannot reach the threshold.
            if min(len(ga), len(gb)) < threshold * max(len(ga), len(gb)):
                continue
            j = jaccard(ga, gb)
            if j >= threshold:
                pairs.append((a, b, round(j, 4)))
    return pairs


def family_audit(cases: list[Record]) -> list[str]:
    """Similar messages from different customers must be grouped in one formulation family."""
    by_id = {c["case_id"]: c for c in cases}
    return [
        f"{a} ~ {b} (jaccard {j}) share wording but not family_id"
        for a, b, j in near_duplicate_pairs(cases, FAMILY_AUDIT_JACCARD)
        if by_id[a]["customer_id"] != by_id[b]["customer_id"]
        and by_id[a]["family_id"] != by_id[b]["family_id"]
    ]


# ---------------------------------------------------------------------------- splits


def components(cases: list[Record], extra_edges: Iterable[tuple[str, str]] = ()) -> list[list[str]]:
    """Connected components linking cases that share customer, scenario or family (8.2.1)."""
    parent = {c["case_id"]: c["case_id"] for c in cases}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first: dict[tuple[str, str], str] = {}
    for c in cases:
        for key in ("customer_id", "scenario_id", "family_id"):
            parent[find(c["case_id"])] = find(first.setdefault((key, c[key]), c["case_id"]))
    for a, b in extra_edges:
        parent[find(a)] = find(b)
    groups: dict[str, list[str]] = {}
    for cid in sorted(parent):
        groups.setdefault(find(cid), []).append(cid)
    return sorted(groups.values())


def assign_splits(
    cases: list[Record], annotations: list[Record], seed: int = SPLIT_SEED
) -> dict[str, list[str]]:
    """Greedy stratified assignment of whole components to splits with exact sizes.

    Strata are (message_label, needs_additional_review). Near-duplicate pairs are merged into
    one component first, so they can never land in different splits (8.2.4).
    """
    if sum(SPLIT_SIZES.values()) != len(cases):
        raise ValueError(f"{len(cases)} cases but split sizes sum to {sum(SPLIT_SIZES.values())}")
    stratum = {
        a["case_id"]: f"{a['message_label']}|{a['needs_additional_review']}" for a in annotations
    }
    comps = components(cases, [(a, b) for a, b, _ in near_duplicate_pairs(cases)])
    random.Random(seed).shuffle(comps)
    comps.sort(key=len, reverse=True)  # stable: equal sizes keep the seeded order

    totals = Counter(stratum.values())
    n = len(cases)
    target = {s: {k: v * SPLIT_SIZES[s] / n for k, v in totals.items()} for s in SPLITS}
    counts: dict[str, Counter[str]] = {s: Counter() for s in SPLITS}
    out: dict[str, list[str]] = {s: [] for s in SPLITS}
    for comp in comps:
        cc = Counter(stratum[cid] for cid in comp)
        open_splits = [s for s in SPLITS if len(out[s]) + len(comp) <= SPLIT_SIZES[s]]
        if not open_splits:
            raise ValueError(f"component of size {len(comp)} does not fit any split")

        def score(s: str, cc: Counter[str] = cc) -> tuple[float, float]:
            gain = sum(min(v, max(0.0, target[s][k] - counts[s][k])) for k, v in cc.items())
            return gain, 1 - len(out[s]) / SPLIT_SIZES[s]

        best = max(open_splits, key=score)
        out[best].extend(comp)
        counts[best].update(cc)
    return {s: sorted(ids) for s, ids in out.items()}


def check_splits(
    cases: list[Record], annotations: list[Record], splits: dict[str, list[str]]
) -> list[str]:
    errors: list[str] = []
    owner = split_of(splits)
    all_ids = [cid for ids in splits.values() for cid in ids]
    if len(all_ids) != len(set(all_ids)):
        errors.append("a case appears in more than one split")
    if set(all_ids) != {c["case_id"] for c in cases}:
        errors.append("splits do not cover exactly the dataset")
    for s in SPLITS:
        if len(splits[s]) != SPLIT_SIZES[s]:
            errors.append(f"{s}: {len(splits[s])} cases, protocol requires {SPLIT_SIZES[s]}")
    for key in ("customer_id", "scenario_id", "family_id"):
        seen: dict[str, set[str]] = {}
        for c in cases:
            seen.setdefault(c[key], set()).add(owner.get(c["case_id"], "?"))
        crossing = sorted(k for k, v in seen.items() if len(v) > 1)
        if crossing:
            errors.append(f"{key} shared across splits: {crossing[:10]}")
    for a, b, j in near_duplicate_pairs(cases):
        if owner.get(a) != owner.get(b):
            errors.append(f"near-duplicates across splits: {a} ({owner.get(a)}) ~ {b} ({j})")
    exp = PROTOCOL["experiment"]["splits"]
    labels = {a["case_id"]: a["message_label"] for a in annotations}
    test = Counter(labels[cid] for cid in splits["test"] if cid in labels)
    for cls in CLASSES:
        if test[cls] < exp["test_min_per_class"]:
            errors.append(f"test has {test[cls]} {cls}, minimum {exp['test_min_per_class']}")
    critical = sum(test[c] for c in PROTOCOL["classification_cost"]["critical_classes"])
    if critical < exp["test_min_critical_class_items"]:
        errors.append(f"test has {critical} critical-class items, minimum 40")
    seed = Counter(labels[cid] for cid in splits["seed_stock"] if cid in labels)
    if min(seed[c] for c in CLASSES) < 3:
        errors.append(f"seed_stock cannot support a stratified initial memory: {dict(seed)}")
    return errors


# ---------------------------------------------------------------------------- hashes/manifest


def canonical_jsonl(records: Iterable[Record]) -> bytes:
    rows = sorted(records, key=lambda r: str(r["case_id"]))
    return "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for r in rows
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    # Normalised newlines so a checkout with CRLF conversion gives the same hash.
    return sha256(path.read_bytes().replace(b"\r\n", b"\n"))


def statistics(
    cases: list[Record], annotations: list[Record], splits: dict[str, list[str]] | None = None
) -> Record:
    ann = {a["case_id"]: a for a in annotations}
    mandatory = {r["id"] for r in PROTOCOL["review_reasons"] if r["mandatory_rule"]}

    def summary(ids: list[str]) -> Record:
        rows = [ann[cid] for cid in ids]
        discretionary = [a for a in rows if not mandatory & set(a["review_reasons"])]
        return {
            "n": len(rows),
            "message_label": {c: sum(a["message_label"] == c for a in rows) for c in CLASSES},
            "needs_additional_review": {
                "true": sum(a["needs_additional_review"] for a in rows),
                "false": sum(not a["needs_additional_review"] for a in rows),
            },
            "review_by_label": {
                c: sum(a["needs_additional_review"] for a in rows if a["message_label"] == c)
                for c in CLASSES
            },
            "discretionary_subset": {
                "n": len(discretionary),
                "needs_review": sum(a["needs_additional_review"] for a in discretionary),
            },
            "review_reasons": {r: sum(r in a["review_reasons"] for a in rows) for r in REASONS},
            "risk_flags": {f: sum(f in a["risk_flags"] for a in rows) for f in FLAGS},
            "action_policy": dict(sorted(Counter(a["action_policy"] for a in rows).items())),
            "multi_intent": sum(bool(a["secondary_intents"]) for a in rows),
        }

    out: Record = {"all": summary([c["case_id"] for c in cases])}
    if splits:
        out.update({s: summary(splits[s]) for s in SPLITS})
    return out


def build_manifest(
    cases: list[Record], annotations: list[Record], splits: dict[str, list[str]]
) -> Record:
    ann = {a["case_id"]: a for a in annotations}
    by_id = {c["case_id"]: c for c in cases}
    near = near_duplicate_pairs(cases)
    comps = components(cases, [(a, b) for a, b, _ in near])
    split_hashes = {
        s: {
            "inference_view_sha256": sha256(canonical_jsonl(inference_view(by_id[i]) for i in ids)),
            "gold_sha256": sha256(
                canonical_jsonl({"case_id": i, **{f: ann[i][f] for f in GOLD_FIELDS}} for i in ids)
            ),
        }
        for s, ids in splits.items()
    }
    return {
        "dataset_version": DATASET_VERSION,
        "protocol_version": PROTOCOL["protocol_version"],
        "status": "candidate: independent human double annotation pending (protocol 8.2.7)",
        "test_frozen": False,
        "files_sha256": {p.name: file_sha256(p) for p in (CASES_PATH, ANNOTATIONS_PATH)},
        "content_sha256": {
            "cases": sha256(canonical_jsonl(cases)),
            "annotations": sha256(canonical_jsonl(annotations)),
        },
        "splits": {"seed": SPLIT_SEED, "sizes": SPLIT_SIZES, "hashes": split_hashes},
        "grouping": {
            "components": len(comps),
            "largest_component": max(len(c) for c in comps),
            "customers": len({c["customer_id"] for c in cases}),
            "scenarios": len({c["scenario_id"] for c in cases}),
            "families": len({c["family_id"] for c in cases}),
            "multi_member_families": sum(
                n > 1 for n in Counter(c["family_id"] for c in cases).values()
            ),
        },
        "checks": {
            "exact_duplicates_normalised": len(exact_duplicates(cases)),
            "near_duplicate_pairs_jaccard_ge_threshold": len(near),
            "near_duplicate_threshold_char5gram_jaccard": JACCARD_MAX,
            "family_audit_threshold_char5gram_jaccard": FAMILY_AUDIT_JACCARD,
            "family_audit_violations": len(family_audit(cases)),
            "embedding_cosine_check": "not performed: no local encoder (see DATASET_CARD.md)",
        },
        "statistics": statistics(cases, annotations, splits),
    }


# ---------------------------------------------------------------------------- CLI


def _report(title: str, errors: list[str]) -> bool:
    print(f"[{'OK' if not errors else 'FAIL'}] {title}")
    for e in errors[:50]:
        print(f"  - {e}")
    if len(errors) > 50:
        print(f"  ... {len(errors) - 50} more")
    return not errors


def check_hashes() -> list[str]:
    manifest = json.loads(MANIFEST_PATH.read_text("utf-8"))
    fresh = build_manifest(load_cases(), load_annotations(), load_splits())
    return [f"manifest field '{k}' is stale" for k in fresh if manifest.get(k) != fresh[k]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m responsible_receivables_agent.dataset")
    parser.add_argument(
        "command",
        choices=["validate", "stats", "check-splits", "check-hashes", "build"],
        help="validate: everything; check-splits: sizes, groups and leakage; check-hashes: "
        "manifest vs files; stats: distributions; build: rewrite splits.json and manifest.json",
    )
    args = parser.parse_args(argv)
    cases, annotations = load_cases(), load_annotations()

    if args.command == "build":
        splits = assign_splits(cases, annotations)
        payload = {"seed": SPLIT_SEED, "algorithm": "dataset.assign_splits", "splits": splits}
        SPLITS_PATH.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        manifest = build_manifest(cases, annotations, splits)
        MANIFEST_PATH.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"wrote {SPLITS_PATH.name} and {MANIFEST_PATH.name}")
        return 0
    if args.command == "stats":
        current = load_splits() if SPLITS_PATH.exists() else None
        print(json.dumps(statistics(cases, annotations, current), indent=1))
        return 0

    ok = True
    if args.command == "validate":
        ok &= _report("records and annotations", validate_records(cases, annotations))
        dups = [f"exact duplicates: {d}" for d in exact_duplicates(cases)]
        ok &= _report("exact duplicates (normalised text)", dups)
        ok &= _report("formulation families (cross-customer similarity)", family_audit(cases))
    if args.command in ("validate", "check-splits"):
        splits = load_splits()
        ok &= _report(
            "splits: sizes, groups, near-duplicates, minima",
            check_splits(cases, annotations, splits),
        )
        stale = splits != assign_splits(cases, annotations)
        ok &= _report("splits: reproducible from seed", ["splits.json is stale"] if stale else [])
    if args.command in ("validate", "check-hashes"):
        ok &= _report("manifest hashes", check_hashes())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

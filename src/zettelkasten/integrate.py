"""Integrate phase: two-step LLM decision + execution.

Step 1 — classify (temperature=0, max_tokens=512):
    Returns JSON: {operation, target_note_ids, reasoning, confidence}

Step 2 — execute (temperature=0.3, max_tokens=4096/2048):
    Returns plain text: ## Title\n\nBody
    Library assembles the ZettelNote; LLM never writes frontmatter.

Operations: CREATE, UPDATE, EDIT, STUB, SYNTHESISE, SPLIT, NOTHING
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from .note import ZettelNote
from .prompts import _STEP1_PROMPT, _STEP1_5_PROMPT, STEP2_PROMPTS
from .providers import LLMProvider

log = logging.getLogger("zettelkasten")

_EXECUTABLE_OPS = frozenset({"CREATE", "UPDATE", "EDIT", "STUB", "SYNTHESISE", "SPLIT"})

# Notes above this threshold are annotated [LARGE] in the classify prompt
NOTE_BODY_LARGE = 8000  # chars

# max_tokens for step 2 by operation
_STEP2_MAX_TOKENS: dict[str, int] = {
    "UPDATE":    4096,
    "EDIT":      2048,  # reductive — output must be smaller than input
    "SYNTHESISE": 4096,
    "SPLIT":     4096,
    "CREATE":    2048,
    "STUB":      2048,
}

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class IntegrationResult:
    """Outcome of a single integrate_phase call."""

    operation: str            # CREATE | UPDATE | EDIT | STUB | SYNTHESISE | SPLIT | NOTHING
    reasoning: str
    confidence: float
    target_ids: list[str] = field(default_factory=list)
    note_title: str = ""      # title of note to create/rewrite
    note_body: str = ""       # body  of note to create/rewrite
    # SPLIT only — the second note produced by splitting the source
    split_title: str = ""
    split_body: str = ""
    is_curation: bool = False  # retained for any deferred-only callers
    note_id: str = ""         # ID assigned by the store after writing (set by store, not integrate)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def integrate_phase(
    draft: ZettelNote,
    cluster: list[ZettelNote],
    llm: LLMProvider,
    fast_llm: LLMProvider | None = None,
) -> IntegrationResult:
    """Two-step integration of *draft* against *cluster*.

    Step 1 classifies the operation.  Step 2 executes it (for ingestion-time
    operations only).  Returns an :class:`IntegrationResult` the caller can
    use to write/update notes.

    *fast_llm* is used for step 1 (cheap classification).  Falls back to
    *llm* if not provided.
    """
    _fast = fast_llm or llm
    log.info(
        "integrate.start draft_title=%r cluster_size=%d",
        draft.title,
        len(cluster),
    )

    # ---- Step 1: classify ----
    decision = _step1_classify(draft, cluster, _fast)
    op = decision["operation"]
    target_ids = decision.get("target_note_ids") or []
    reasoning = decision.get("reasoning", "")
    confidence = float(decision.get("confidence", 0.0))

    log.info(
        "integrate.step1 operation=%s confidence=%.2f targets=%s reasoning=%r",
        op,
        confidence,
        target_ids,
        reasoning,
    )

    # ---- NOTHING ----
    if op == "NOTHING":
        log.info("integrate.complete operation=NOTHING")
        return IntegrationResult(
            operation="NOTHING",
            reasoning=reasoning,
            confidence=confidence,
        )

    # ---- Step 2: execute ----
    if op not in _EXECUTABLE_OPS:
        # Unknown operation — treat as NOTHING
        log.warning("integrate.unknown_operation op=%r — treating as NOTHING", op)
        return IntegrationResult(
            operation="NOTHING",
            reasoning=f"Unknown operation {op!r}",
            confidence=0.0,
        )

    target_notes = [n for n in cluster if n.id in target_ids]

    # ---- Step 1.5: refine UPDATE on large notes ----
    if op == "UPDATE" and target_notes:
        large_target = next(
            (n for n in target_notes if len(n.body) > NOTE_BODY_LARGE), None
        )
        if large_target is not None:
            step15 = _step1_5_classify(large_target, draft, _fast)
            op = step15["operation"]  # EDIT or SPLIT
            # keep original reasoning/confidence unless step 1.5 has its own
            reasoning = step15.get("reasoning", reasoning)
            confidence = float(step15.get("confidence", confidence))
            log.info(
                "integrate.step1_5 operation=%s confidence=%.2f reasoning=%r",
                op,
                confidence,
                reasoning,
            )

    if op == "SPLIT":
        title, body, split_title, split_body = _step2_split(draft, target_notes, llm)
        log.info("integrate.complete operation=SPLIT title=%r split_title=%r", title, split_title)
        return IntegrationResult(
            operation=op,
            reasoning=reasoning,
            confidence=confidence,
            target_ids=target_ids,
            note_title=title,
            note_body=body,
            split_title=split_title,
            split_body=split_body,
        )

    title, body = _step2_execute(op, draft, target_notes, llm)

    log.debug(
        "integrate.step2 operation=%s title=%r body_len=%d",
        op,
        title,
        len(body),
    )
    log.info("integrate.complete operation=%s title=%r", op, title)

    return IntegrationResult(
        operation=op,
        reasoning=reasoning,
        confidence=confidence,
        target_ids=target_ids,
        note_title=title,
        note_body=body,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _step1_classify(
    draft: ZettelNote,
    cluster: list[ZettelNote],
    llm: LLMProvider,
) -> dict:
    if cluster:
        cluster_text = "\n\n---\n\n".join(
            f"id: {n.id}\n## {n.title}\n\n{n.body}"
            for n in cluster
        )
    else:
        cluster_text = "(empty — no existing notes in cluster)"

    draft_text = f"## {draft.title}\n\n{draft.body}"
    prompt = _STEP1_PROMPT.format(draft=draft_text, cluster=cluster_text)
    raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
    return _parse_decision(raw)


def _step1_5_classify(
    target: ZettelNote,
    draft: ZettelNote,
    llm: LLMProvider,
) -> dict:
    """Step 1.5: focused EDIT/SPLIT decision for a large UPDATE target."""
    target_text = f"id: {target.id}\n## {target.title}\n\n{target.body}"
    draft_text = f"## {draft.title}\n\n{draft.body}"
    prompt = _STEP1_5_PROMPT.format(
        note_size=len(target.body),
        target=target_text,
        draft=draft_text,
    )
    raw = llm.complete(prompt, max_tokens=256, temperature=0.0)
    result = _parse_decision(raw)
    # step 1.5 only produces EDIT or SPLIT; default to EDIT on anything else
    if result.get("operation") not in ("EDIT", "SPLIT"):
        result["operation"] = "EDIT"
    return result


def _step2_execute(
    op: str,
    draft: ZettelNote,
    targets: list[ZettelNote],
    llm: LLMProvider,
) -> tuple[str, str]:
    """Call step 2 and return (title, body)."""
    template = STEP2_PROMPTS[op]
    draft_text = f"## {draft.title}\n\n{draft.body}"
    targets_text = "\n\n---\n\n".join(
        f"id: {n.id}\n## {n.title}\n\n{n.body}" for n in targets
    ) if targets else "(none)"
    prompt = template.format(draft=draft_text, targets=targets_text)
    max_tokens = _STEP2_MAX_TOKENS[op]
    raw = llm.complete(prompt, max_tokens=max_tokens, temperature=0.3)
    return _parse_title_body(raw)


def _parse_decision(raw: str) -> dict:
    """Extract JSON decision from LLM response."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {
            "operation": "NOTHING",
            "target_note_ids": [],
            "reasoning": f"Parse error: {raw[:200]}",
            "confidence": 0.0,
        }
    json_str = match.group()
    # Attempt 1: clean parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    # Attempt 2: strip stray control characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", json_str)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Attempt 3: regex field extraction
    op_m = re.search(r'"operation"\s*:\s*"([^"]+)"', json_str)
    ids_m = re.search(r'"target_note_ids"\s*:\s*(\[[^\]]*\])', json_str)
    reas_m = re.search(r'"reasoning"\s*:\s*"(.*?)"(?:\s*[,}])', json_str, re.DOTALL)
    conf_m = re.search(r'"confidence"\s*:\s*([0-9.]+)', json_str)
    if op_m:
        target_ids: list = []
        if ids_m:
            try:
                target_ids = json.loads(ids_m.group(1))
            except Exception:
                target_ids = re.findall(r'"([^"]+)"', ids_m.group(1))
        return {
            "operation": op_m.group(1),
            "target_note_ids": target_ids,
            "reasoning": reas_m.group(1).replace('\\"', '"') if reas_m else "",
            "confidence": float(conf_m.group(1)) if conf_m else 0.5,
        }
    return {
        "operation": "NOTHING",
        "target_note_ids": [],
        "reasoning": f"Parse error: {raw[:200]}",
        "confidence": 0.0,
    }


def _step2_split(
    draft: ZettelNote,
    targets: list[ZettelNote],
    llm: LLMProvider,
) -> tuple[str, str, str, str]:
    """Call step 2 for SPLIT and return (title1, body1, title2, body2)."""
    template = STEP2_PROMPTS["SPLIT"]
    draft_text   = f"## {draft.title}\n\n{draft.body}"
    targets_text = "\n\n---\n\n".join(
        f"id: {n.id}\n## {n.title}\n\n{n.body}" for n in targets
    ) if targets else "(none)"
    prompt = template.format(draft=draft_text, targets=targets_text)
    raw = llm.complete(prompt, max_tokens=_STEP2_MAX_TOKENS["SPLIT"], temperature=0.3)

    parts = re.split(r"\n---SPLIT---\n", raw, maxsplit=1)
    if len(parts) == 2:
        title1, body1 = _parse_title_body(parts[0].strip())
        title2, body2 = _parse_title_body(parts[1].strip())
        return title1, body1, title2, body2

    # Fallback: couldn't parse split — return full content as note 1, empty note 2
    log.warning("integrate.split_parse_failed — treating as single note")
    title1, body1 = _parse_title_body(raw)
    return title1, body1, "", ""


def _parse_title_body(raw: str) -> tuple[str, str]:
    """Parse '## Title\n\nBody' output from step 2."""
    raw = raw.strip()
    for line in raw.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            rest = raw[raw.index(line) + len(line):]
            body = rest.strip()
            return title, body
    # No heading found — use the whole response as body
    return "", raw

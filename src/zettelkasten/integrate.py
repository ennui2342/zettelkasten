"""Integrate phase: levelled LLM classification + execution.

L1 classify  (temperature=0, max_tokens=512):
    SYNTHESISE / INTEGRATE / NOTHING
    Returns JSON: {operation, target_note_ids, reasoning, confidence}

L2 classify  (temperature=0, max_tokens=512):
    CREATE / UPDATE / NOTHING  (only reached from INTEGRATE)
    Returns JSON: {operation, target_note_ids, reasoning, confidence}

L3 classify  (temperature=0, max_tokens=256):
    EDIT / SPLIT  (only reached when L2=UPDATE and target is large)
    Returns JSON: {operation, reasoning, confidence}

Execute  (temperature=0.3, max_tokens varies):
    Returns plain text: ## Title\n\nBody
    Library assembles the ZettelNote; LLM never writes frontmatter.

Operations: CREATE, UPDATE, EDIT, SYNTHESISE, SPLIT, NOTHING
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from .note import ZettelNote
from .prompts import _L1_PROMPT, _L2_PROMPT, _L3_PROMPT, EXEC_PROMPTS
from .providers import EmbedProvider, LLMProvider

log = logging.getLogger("zettelkasten")

# Notes above this threshold trigger L3 (EDIT/SPLIT) on UPDATE
NOTE_BODY_LARGE = 8000  # chars

# max_tokens for execute phase by operation
_EXEC_MAX_TOKENS: dict[str, int] = {
    "UPDATE":     4096,
    "EDIT":       2048,  # reductive — output must be smaller than input
    "SYNTHESISE": 4096,
    "SPLIT":      4096,
    "CREATE":     2048,
}

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class IntegrationResult:
    """Outcome of a single integrate_phase call."""

    operation: str            # CREATE | UPDATE | EDIT | SYNTHESISE | SPLIT | NOTHING
    reasoning: str
    confidence: float
    target_ids: list[str] = field(default_factory=list)
    note_title: str = ""      # title of note to create/rewrite
    note_body: str = ""       # body  of note to create/rewrite
    # SPLIT only — the second note produced by splitting the source
    split_title: str = ""
    split_body: str = ""
    note_id: str = ""         # ID assigned by the store after writing (set by store, not integrate)
    l1_target_ids: list[str] = field(default_factory=list)  # notes identified by L1 classify
    links: list[dict] = field(default_factory=list)  # epistemic links [{target, rel}] from L2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def integrate_phase(
    draft: ZettelNote,
    cluster: list[ZettelNote],
    llm: LLMProvider,
    fast_llm: LLMProvider | None = None,
    embed: EmbedProvider | None = None,
) -> IntegrationResult:
    """Levelled integration of *draft* against *cluster*.

    L1 classifies SYNTHESISE / INTEGRATE / NOTHING.
    L2 classifies CREATE / UPDATE / NOTHING (only reached from INTEGRATE).
    L3 refines UPDATE on large notes to EDIT or SPLIT.
    Execute produces the final note content.

    *fast_llm* is used for all classify calls.  Falls back to *llm* if not
    provided.
    """
    _fast = fast_llm or llm
    log.info(
        "integrate.start draft_title=%r cluster_size=%d",
        draft.title,
        len(cluster),
    )

    # ---- L1: SYNTHESISE / INTEGRATE / NOTHING ----
    # Empty cluster: no synthesis possible, nothing already captured → force INTEGRATE
    if not cluster:
        l1 = {"operation": "INTEGRATE", "target_note_ids": [], "reasoning": "empty corpus", "confidence": 1.0}
    else:
        l1 = _l1_classify(draft, cluster, _fast)
    l1_op = l1.get("operation", "INTEGRATE")
    if l1_op not in ("SYNTHESISE", "INTEGRATE", "NOTHING"):
        l1_op = "INTEGRATE"
    l1_target_ids = l1.get("target_note_ids") or []
    reasoning = l1.get("reasoning", "")
    confidence = float(l1.get("confidence", 0.0))

    log.info(
        "integrate.l1 operation=%s confidence=%.2f targets=%s reasoning=%r",
        l1_op, confidence, l1_target_ids, reasoning,
    )

    if l1_op == "NOTHING":
        log.info("integrate.complete operation=NOTHING")
        return IntegrationResult(
            operation="NOTHING", reasoning=reasoning, confidence=confidence,
            l1_target_ids=l1_target_ids,
        )

    if l1_op == "SYNTHESISE":
        target_notes = [n for n in cluster if n.id in l1_target_ids]
        title, body = _execute(draft, "SYNTHESISE", target_notes, llm)
        log.info("integrate.complete operation=SYNTHESISE title=%r body_len=%d", title, len(body))
        return IntegrationResult(
            operation="SYNTHESISE",
            reasoning=reasoning,
            confidence=confidence,
            target_ids=l1_target_ids,
            l1_target_ids=l1_target_ids,
            note_title=title,
            note_body=body,
        )

    # ---- §4.7 research: log cosine similarities for pre-filter evaluation ----
    if embed is not None and log.isEnabledFor(logging.DEBUG):
        _log_cluster_cosine_sims(draft, cluster, l1_target_ids, embed)

    # ---- L2: CREATE / UPDATE / NOTHING ----
    # Cluster for L2 is filtered to the notes L1 identified as most relevant.
    filtered_cluster = [n for n in cluster if n.id in l1_target_ids]
    l2 = _l2_classify(draft, filtered_cluster, _fast)
    l2_op = l2.get("operation", "CREATE")
    if l2_op not in ("CREATE", "UPDATE", "NOTHING"):
        l2_op = "CREATE"
    l2_target_ids = l2.get("target_note_ids") or []
    reasoning = l2.get("reasoning", reasoning)
    confidence = float(l2.get("confidence", confidence))
    l2_links = [
        lk for lk in (l2.get("links") or [])
        if isinstance(lk, dict) and lk.get("target") and lk.get("rel") in ("contradicts", "supersedes")
    ]

    log.info(
        "integrate.l2 operation=%s confidence=%.2f targets=%s reasoning=%r",
        l2_op, confidence, l2_target_ids, reasoning,
    )

    if l2_op == "NOTHING":
        log.info("integrate.complete operation=NOTHING")
        return IntegrationResult(
            operation="NOTHING", reasoning=reasoning, confidence=confidence,
            l1_target_ids=l1_target_ids,
        )

    target_notes = [n for n in filtered_cluster if n.id in l2_target_ids]
    op = l2_op

    # ---- L3: refine UPDATE on large notes to EDIT or SPLIT ----
    if op == "UPDATE" and target_notes:
        large_target = next(
            (n for n in target_notes if len(n.body) > NOTE_BODY_LARGE), None
        )
        if large_target is not None:
            l3 = _l3_classify(large_target, _fast)
            op = l3["operation"]
            reasoning = l3.get("reasoning", reasoning)
            confidence = float(l3.get("confidence", confidence))
            log.info(
                "integrate.l3 operation=%s confidence=%.2f reasoning=%r",
                op, confidence, reasoning,
            )

    if op == "SPLIT":
        title, body, split_title, split_body = _execute_split(draft, target_notes, llm)
        log.info(
            "integrate.complete operation=SPLIT title=%r body_len=%d split_title=%r split_body_len=%d",
            title, len(body), split_title, len(split_body),
        )
        return IntegrationResult(
            operation=op,
            reasoning=reasoning,
            confidence=confidence,
            target_ids=l2_target_ids,
            l1_target_ids=l1_target_ids,
            note_title=title,
            note_body=body,
            split_title=split_title,
            split_body=split_body,
            links=l2_links,
        )

    title, body = _execute(draft, op, target_notes, llm)
    log.info("integrate.complete operation=%s title=%r body_len=%d", op, title, len(body))

    return IntegrationResult(
        operation=op,
        reasoning=reasoning,
        confidence=confidence,
        target_ids=l2_target_ids,
        l1_target_ids=l1_target_ids,
        note_title=title,
        note_body=body,
        links=l2_links,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _log_cluster_cosine_sims(
    draft: ZettelNote,
    cluster: list[ZettelNote],
    l1_target_ids: list[str],
    embed: EmbedProvider,
) -> None:
    """Log cosine similarity between draft and each cluster note (§4.7 research).

    Emitted at DEBUG after an L1 INTEGRATE decision.  Format per note:
      <id>=<T|F>:<sim>  where T = selected by L1, F = not selected.

    Use this data to assess whether a cosine-similarity threshold could
    pre-filter noise from the cluster before L1/L2 classification.
    """
    import numpy as np

    noted = [(n.id, n.embedding) for n in cluster if n.embedding is not None]
    if not noted:
        return

    q_vec = np.array(embed.embed([draft.body], input_type="query")[0], dtype=np.float32)
    q_norm = float(np.linalg.norm(q_vec))
    if q_norm < 1e-9:
        return
    q_unit = q_vec / q_norm

    sims: list[tuple[str, float, bool]] = []
    for nid, emb in noted:
        e = emb.astype(np.float32)
        e_norm = float(np.linalg.norm(e))
        sim = float(np.dot(e / e_norm, q_unit)) if e_norm > 1e-9 else 0.0
        sims.append((nid, sim, nid in l1_target_ids))
    sims.sort(key=lambda x: -x[1])

    log.debug(
        "integrate.cluster_cosine_sims draft=%r %s",
        draft.title,
        " ".join(f"{nid}={'T' if sel else 'F'}:{sim:.3f}" for nid, sim, sel in sims),
    )


def _format_cluster(notes: list[ZettelNote]) -> str:
    if not notes:
        return "(empty — no existing notes in cluster)"
    return "\n\n---\n\n".join(
        f"id: {n.id}\n## {n.title}\n\n{n.body}" for n in notes
    )


def _l1_classify(
    draft: ZettelNote,
    cluster: list[ZettelNote],
    llm: LLMProvider,
) -> dict:
    """L1: classify draft as SYNTHESISE / INTEGRATE / NOTHING."""
    draft_text = f"## {draft.title}\n\n{draft.body}"
    prompt = _L1_PROMPT.format(draft=draft_text, cluster=_format_cluster(cluster))
    raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
    return _parse_decision(raw)


def _l2_classify(
    draft: ZettelNote,
    cluster: list[ZettelNote],
    llm: LLMProvider,
) -> dict:
    """L2: classify draft as CREATE / UPDATE / NOTHING against filtered cluster."""
    draft_text = f"## {draft.title}\n\n{draft.body}"
    prompt = _L2_PROMPT.format(draft=draft_text, cluster=_format_cluster(cluster))
    raw = llm.complete(prompt, max_tokens=512, temperature=0.0)
    return _parse_decision(raw)


def _l3_classify(
    target: ZettelNote,
    llm: LLMProvider,
) -> dict:
    """L3: focused EDIT/SPLIT decision for a large UPDATE target.

    Only the target note is assessed — the draft is NOT shown here.
    SPLIT/EDIT is a structural property of the note itself.
    The draft is passed through to execute regardless of the L3 decision.
    """
    target_text = f"id: {target.id}\n## {target.title}\n\n{target.body}"
    prompt = _L3_PROMPT.format(
        note_size=len(target.body),
        target=target_text,
    )
    raw = llm.complete(prompt, max_tokens=256, temperature=0.0)
    result = _parse_decision(raw)
    # L3 only produces EDIT or SPLIT; default to EDIT on anything else
    if result.get("operation") not in ("EDIT", "SPLIT"):
        result["operation"] = "EDIT"
    return result


def _execute(
    draft: ZettelNote,
    op: str,
    targets: list[ZettelNote],
    llm: LLMProvider,
) -> tuple[str, str]:
    """Call execute phase and return (title, body)."""
    template = EXEC_PROMPTS[op]
    draft_text = f"## {draft.title}\n\n{draft.body}"
    targets_text = "\n\n---\n\n".join(
        f"id: {n.id}\n## {n.title}\n\n{n.body}" for n in targets
    ) if targets else "(none)"
    prompt = template.format(draft=draft_text, targets=targets_text)
    max_tokens = _EXEC_MAX_TOKENS[op]
    raw = llm.complete(prompt, max_tokens=max_tokens, temperature=0.3)
    return _parse_title_body(raw)


def _execute_split(
    draft: ZettelNote,
    targets: list[ZettelNote],
    llm: LLMProvider,
) -> tuple[str, str, str, str]:
    """Call execute phase for SPLIT and return (title1, body1, title2, body2)."""
    template = EXEC_PROMPTS["SPLIT"]
    draft_text   = f"## {draft.title}\n\n{draft.body}"
    targets_text = "\n\n---\n\n".join(
        f"id: {n.id}\n## {n.title}\n\n{n.body}" for n in targets
    ) if targets else "(none)"
    prompt = template.format(draft=draft_text, targets=targets_text)
    raw = llm.complete(prompt, max_tokens=_EXEC_MAX_TOKENS["SPLIT"], temperature=0.3)

    parts = re.split(r"\n---SPLIT---\n", raw, maxsplit=1)
    if len(parts) == 2:
        title1, body1 = _parse_title_body(parts[0].strip())
        title2, body2 = _parse_title_body(parts[1].strip())
        return title1, body1, title2, body2

    # Fallback: couldn't parse split — return full content as note 1, empty note 2
    log.warning("integrate.split_parse_failed — treating as single note")
    title1, body1 = _parse_title_body(raw)
    return title1, body1, "", ""


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


def _parse_title_body(raw: str) -> tuple[str, str]:
    """Parse '## Title\n\nBody' output from execute phase."""
    raw = raw.strip()
    for line in raw.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            rest = raw[raw.index(line) + len(line):]
            body = rest.strip()
            return title, body
    # No heading found — use the whole response as body
    return "", raw

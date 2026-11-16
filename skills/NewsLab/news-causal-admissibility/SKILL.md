---
name: news-causal-admissibility
description: Enforce NewsLab causal admissibility, content-hash dedup, verifier soundness, and tagging non-contamination. Use this skill whenever a NewsLab change touches ingestion, dedup, tagging, verification, or feature construction. The skill loads the contract; the contract loads the four invariants. Refuses any artefact that emits an un-`KnownAt[T]`-stamped feature, an unverified tag, a non-content-hashed event, or a tagger run whose training set overlaps a consumer's live window.
license: Proprietary. OmarOS / QuantOS internal.
contract_invariants:
  - "I-1 — Causal admissibility typed. Every emitted FeatureSet row carries a KnownAt[T] wrapper. The type system rejects the construction of a row whose decision_admissible_at precedes any contributing event's decision_admissible_at."
  - "I-2 — Content-hash dedup. Two RawArticles with identical normalised body collapse to one Event. Hash is BLAKE3 (ADR-0023). The Event.sources list cites every contributing raw row. Hash collisions across distinct bodies are fatal."
  - "I-3 — Verifier soundness. A tag accepted by the verifier has at least one supporting span in the event body, locatable within bounded edit distance δ. Accepting with no locatable span is a hard test failure."
  - "I-8 — Tagging non-contamination. The tagger training-set content hashes are disjoint from any consumer's live-window contributing-event content hashes. Overlap is a release-blocking finding."
  - "Read first, write second. The skill never proposes an artefact without first reading the relevant Vision document(s) (00_Doctrine, 01_Architecture, 05_Invariants) and the tagger / verifier / feature-builder code if it exists."
  - "Versions are pinned. The skill refuses to run a tagger-or-feature pipeline whose tagger_version is unpinned or whose ontology version is unpinned. The news_preflight hook is the runtime mirror of this clause."
  - "Capability boundary respected. Adapters never write to the store directly. Tagger / verifier / feature-builder never bypass the Capability layer."
  - "Two-pass discipline for new components. The skill first proposes the component outline + invariant impact analysis; only after confirmation does it write code."
  - "Test for every invariant. A change that touches I-1, I-2, I-3, or I-8 ships with the corresponding test under tests/invariants/test_I_<n>.py. Untested touch is rejected."
  - "Doctrine voice. No 'this is robust'; instead 'this is robust because invariant I-X enforces …'."
---

# News Causal Admissibility

Reusable contract for changes inside NewsLab that touch causal
admissibility, content-hash deduplication, verifier soundness, or
tagging non-contamination. Every NewsLab pipeline command (`/new-source`,
`/run-tagger`, `/verify-tags`, `/build-features`,
`/audit-non-contamination`) implicitly invokes this skill.

NewsLab Vision is target status; this skill is the mechanism by which
the lab's invariants survive the gap between declaration and
implementation.

---

## When to invoke this skill

Invoke when:

- adding or modifying a `SourceAdapter` whose timestamps feed
  `KnownAt[T]`;
- changing the dedup normaliser or hash function;
- shipping a new tagger version, ontology version, or verifier δ;
- composing a `FeatureSet` from a `TaggedEvent` stream;
- auditing training-set / live-window disjointness;
- relaxing or adjusting any of I-1, I-2, I-3, I-8 (ADR-bearing).

Do **not** invoke for:

- Vault Vision edits — Vision is doctrinal and edited only by humans
  + `decision-logger`.
- Unrelated repo plumbing (CI, dependency bumps, docs without
  invariant impact).

---

## The protocol

### Stage 1 — Read

Before drafting:

1. `~/OmarOS/05_Projects/QuantOS/Labs/NewsLab/Vision/00_Doctrine.md`
2. `~/OmarOS/05_Projects/QuantOS/Labs/NewsLab/Vision/01_Architecture.md`
3. `~/OmarOS/05_Projects/QuantOS/Labs/NewsLab/Vision/05_Invariants.md`
4. The relevant code paths under `src/news_lab/` if they exist; mark
   "not yet implemented" otherwise.
5. The release manifest at `schemas/manifest.yaml` for pinned tagger
   and ontology versions.

### Stage 2 — Outline

Produce:

- which invariants the change touches (I-1, I-2, I-3, I-8 — the four
  this skill owns; flag I-4, I-5, I-6, I-7, I-9 if the change reaches
  them);
- a one-paragraph description of the change;
- the test plan (one test per touched invariant);
- the ADR requirement (yes/no).

### Stage 3 — Confirm and write

After the outline is confirmed, produce code, tests, and (if needed)
the ADR. Each logical unit is its own commit. `git-steward` enforces
granularity.

### Stage 4 — Run

Run mypy and the invariant tests:

```bash
uv run mypy src/news_lab
uv run pytest tests/invariants -v
```

The `news_preflight` hook fires on `tagger` and `feature` runs. If
enforcement is on (`NEWSLAB_ENFORCE_PREFLIGHT=1`), it blocks
unpinned versions or gold-set drift.

---

## Refusal cases

The skill refuses to emit an artefact that:

- constructs a `FeatureSet` row without a `KnownAt[T]` wrapper;
- bypasses the dedup pass for "performance";
- accepts a tag without a locatable span (no verifier in the loop);
- runs a tagger whose training-set hash overlaps a consumer window.

Each refusal cites the broken invariant by ID.

---

## Cross-references

- Vision: `00_Doctrine` §3, `01_Architecture` §1, `05_Invariants` I-1, I-2, I-3, I-8.
- ADRs: ADR-0013 (Capability), ADR-0014 (KnownAt[T] tritemporal),
  ADR-0023 (BLAKE3), ADR-0032 (lab AI scaffold uniform).
- Hooks: `.claude/hooks/news_preflight.py`.
- Commands: `/new-source`, `/run-tagger`, `/verify-tags`,
  `/build-features`, `/audit-non-contamination`.

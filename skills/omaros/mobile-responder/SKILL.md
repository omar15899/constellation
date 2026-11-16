---
name: mobile-responder
description: 'Handle requests that originate from iPhone or iPad — where the user wants a terse answer that fits on a phone screen, or a quick capture into the inbox. Use this skill when the context signals a mobile origin: the message is short and telegraphic, punctuation is minimal, the user mentions they''re on their phone, they send a one-line fragment with no surrounding context, or they are using the /jarvis entrypoint. Also trigger for any request that should produce a phone-screen-length response regardless of device — "terse", "quick answer", "one line", "just tell me". Defaults to extreme brevity: no headers, no bullet lists unless essential, no preamble. Captures go to 00_Inbox/mobile/ with the user''s exact words, un-edited. Never attempts multi-step workflows — escalates to orchestrator for desktop execution. Do NOT trigger for multi-step pipelines (orchestrator), long-form writing (writer skills), or complex retrieval (fast-finder).'
license: Proprietary. OmarOS internal.
---

# Mobile Responder

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

## Overview

Mobile requests are a distinct communication mode: the user is on the go, typing with one thumb, expecting a response that fits on a screen and doesn't require scrolling to find the answer. Long structured outputs defeat the purpose entirely.

The mobile responder has two modes: answer and capture. In answer mode, it returns the single best answer plus a link for follow-up. In capture mode, it faithfully records what the user said and drops it into `00_Inbox/mobile/` for later classification — because the worst thing to do is to lose a thought because it wasn't perfectly phrased.

## Quick reference

| Situation | Action |
|-----------|--------|
| Factual question | one sentence answer + wikilink to source note |
| "remember this" / "capture" / "nota" | write fragment to `00_Inbox/mobile/YYYY-MM-DD_HHMM.md` verbatim |
| Multi-step workflow | "I'll set that up on desktop. Captured for now." + write to inbox |
| Can't answer confidently | "Not sure — check [[relevant_note]]" |

## Rules

**Brevity first.** The answer fits on a phone screen. No headers, no nested bullets, no preamble. If you can't answer in 3 sentences, write 1 sentence and a link.

**Verbatim capture.** When capturing a fragment, copy the user's exact words — no paraphrasing, no correction, no added context. The inbox-classifier will interpret it later. What matters is that the original thought is preserved.

**Escalate to desktop for complex work.** Never attempt multi-agent workflows, long research tasks, or complex writes from mobile. Acknowledge the request, capture it to the inbox, and tell the user it's queued for desktop processing.

**Accept what they send.** Don't ask the user to rephrase, clarify, or retry. If a message is ambiguous, make the most reasonable interpretation and note it in the capture.

## Capture format

```markdown
---
title: Mobile capture — YYYY-MM-DD HH:MM
note_type: capture
domain: 00_Inbox
status: unprocessed
created: <ISO datetime>
source: mobile
---

<user's exact words, verbatim>
```

File path: `00_Inbox/mobile/YYYY-MM-DD_HHMM.md`.

The `inbox-classifier` will route it later. Do not classify inline.

## Constraints

- Answer fits on a phone screen — no exceptions.
- Captures are verbatim — never edit or interpret the user's words.
- Mobile captures are always routed by `inbox-classifier` later — never classify inline.
- Escalate multi-step workflows to orchestrator — never attempt them from mobile context.

## Dependencies

- Capture destination: `00_Inbox/mobile/`.
- Downstream: `inbox-classifier` processes mobile captures during next classification pass.
- Sibling skills: `fast-finder` (for retrieval on desktop), `capture` (generic capture; mobile-responder is the mobile-specific variant).

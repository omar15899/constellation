# Isomorph Rebind — Integration Modes

Every non-trivial integration decision in the reintegration map gets one of the six labels below. The labels are closed — don't coin new ones. Picking the right mode up front changes how much effort and risk the user signs up for.

---

## The six modes

| Mode | When it applies | What the user does locally | Risk profile |
|------|-----------------|----------------------------|--------------|
| **direct drop-in integration** | The generic code is genuinely generic and has no private-facing coupling. Example: a pure utility function (date math, serialization helper, typed value object). | Copy the file into the private repo, unchanged. | Lowest. Contract cannot mismatch because the file has no private dependency. |
| **adapter-mediated integration** | The generic code exposes a stable interface and the private system must plug its own implementation behind it. The default mode for most scaffold ↔ private seams. | Keep the generic interface + implementation. Write a thin adapter in a dedicated adapter file that binds the interface to the real private dependency. | Low–medium. Contract mismatch caught at the adapter seam, which is a narrow review surface. |
| **interface-only reuse** | The private system already has a working implementation of the same concept; only the scaffold's interface shape is adopted so the private impl can be swapped freely in the future. | Copy the scaffold's `Protocol` / interface definition, discard the scaffold's implementation, make the existing private implementation conform. | Medium. The discipline of discarding the generic impl is psychologically costly but architecturally clean. |
| **architectural reference reuse** | The scaffold illustrates an architecture (layered modules, pipeline-and-filter, event-driven orchestration) the private system wants to adopt, but the private code needs to be written by hand because the domain is too specific for a generic scaffold. | Read the scaffold as a blueprint. Write the private system guided by it. Do not integrate the scaffold's files. | Medium. The loose coupling means contract drift is the main risk. |
| **partial manual transplantation** | Some scaffold files are directly usable; others are not. The integration is piecemeal. | File-by-file disposition from Section 5 of the reintegration map; some files go in, others become references, others are skipped. | Medium–high. Mixed mode — each file carries its own risk, and the user must track more state. |
| **non-reintegrable without redesign** | The scaffold's shape materially diverges from the private system's architecture. Example: the scaffold assumes a synchronous batch pipeline but the private system is an event-driven service; trying to force one onto the other will damage both. | Use the scaffold as a design-review artifact and a discussion prompt; perform a redesign before any integration. | High. Integrating anyway is the worst outcome; the map should call this mode out loudly. |

---

## Tagging rules

- Tag in the **System correspondence map** (Section 2) table in the `Integration mode` column: one mode per row.
- Tag in the **File-level integration strategy** (Section 5) only when the file's mode diverges from its module's row in Section 2. Otherwise the mode is inherited.
- If the user asked for a particular mode up front ("just keep it as adapters everywhere"), respect it but flag cases where a different mode would materially improve the outcome.
- A scaffold can mix modes across its modules — that is normal. A scaffold where **every** module is `non-reintegrable without redesign` is a signal the scaffold should have been generated differently (feed back to `isomorph-synth`).

---

## Decision flowchart

```
Is this piece of generic code …

  … genuinely generic, no private coupling needed?
     └──► direct drop-in integration

  … expected to talk to a private external system or internal service?
     └──► adapter-mediated integration (default for this case)

  … duplicating a concept the private system already implements well?
     └──► interface-only reuse

  … carrying an architectural idea the private system wants, but with a
    domain too specific for the scaffold's generic body?
     └──► architectural reference reuse

  … partly usable and partly not?
     └──► partial manual transplantation

  … built on an architecture incompatible with the private system's?
     └──► non-reintegrable without redesign
```

When in doubt between adjacent modes, prefer the lower-risk one. A wrong choice toward direct-drop-in is harder to detect than a wrong choice toward adapter-mediated.

---

## When `non-reintegrable without redesign` is the right answer

It is almost always resisted because it implies throwing work away. Resist the resistance. The correct call here saves much more work than the wrong one.

Typical signals:

- The scaffold assumes synchronous-batch execution; the private system is streaming / event-driven.
- The scaffold uses a layered domain model; the private system is a deeply coupled transaction script. Forcing layers in would require a full rewrite anyway.
- The scaffold's data contracts assume append-only storage; the private system is update-in-place everywhere.
- The scaffold's security model (service-account credentials, mTLS) doesn't exist in the private system (cookie auth, shared DB, IP allowlists).

When this mode is declared: state clearly that the scaffold is still useful as a **design reference** and as a **discussion document** with the team that owns the private system. Propose a redesign route (e.g. a narrowly scoped adapter layer first, with a later full rewrite in the direction of the scaffold's architecture) rather than walking away.

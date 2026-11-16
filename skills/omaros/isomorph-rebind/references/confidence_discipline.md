# Isomorph Rebind — Confidence Discipline

Every correspondence in Section 2 of the reintegration map carries a confidence label. The discipline here is what keeps the skill honest: overclaiming confidence in the private system's structure is precisely how this tool would go wrong.

## The three labels

| Label | When it applies | Must include |
|-------|-----------------|--------------|
| `high confidence` | The correspondence can be derived entirely from the generic scaffold plus obvious universal patterns. No private-side inference needed. | a one-line justification referring only to the scaffold |
| `medium confidence` | The correspondence follows from common patterns for the private system's category (e.g. "pricing engines normally have a calibration step", "web apps normally have a settings module"). Some private-side inference, but robust. | a one-line justification naming the general pattern being assumed |
| `low confidence` | The correspondence is plausible but the user's description of the private system left it genuinely uncertain. The bind could go more than one way. | at least one **alternative integration mode** in the Notes column, not just a hedge |

## When to downgrade confidence

Downgrade from `high` to `medium` when:

- The correspondence relies on a common pattern rather than the scaffold alone ("the private system probably has an observability sink" — even if almost all production systems do, that's pattern-based, not scaffold-based).

Downgrade from `medium` to `low` when:

- The user said little or nothing about the relevant part of the private system.
- The scaffold's generic choice (e.g. "SQLite as a dev stub") has many plausible real-world private counterparts (Postgres, MySQL, DynamoDB, SQL Server, BigQuery, Snowflake, …) and the user did not pin one.
- The integration mode for this correspondence could plausibly be one of two different modes, and the user's description doesn't disambiguate.

Do **not** use `low confidence` as a slop bucket for "I don't know what this is". If you genuinely don't have enough information to say anything substantive, write a row in Section 2 anyway, flag it `low confidence`, and name the ambiguity concretely — then bump the corresponding item in Section 1's "Unknown about the private system" list so the user sees it at the top.

## Alternatives at low confidence

Every `low confidence` row lists at least one alternative. The alternatives are integration modes (see `integration_modes.md`) paired with a short condition: "adapter-mediated if the private system has a dependency-injection container; partial manual transplantation if not." This gives the user a decision tree rather than a dangling uncertainty.

## Language patterns for stating uncertainty

Prefer these:

- "Plausible correspondence, but the private system may implement this as X or Y. If X, use adapter-mediated integration; if Y, use interface-only reuse."
- "Assuming the private system exposes a dependency-injection container. If it does not, this becomes `partial manual transplantation` and effort increases from `small` to `medium`."
- "The user did not describe their messaging layer. The generic scaffold assumes a pub/sub broker; if the private system is request/response, the `EventPublisher` adapter becomes unused and the orchestration step below is replaced by a direct call."

Avoid these:

- "I think this is X" (personal opinion is not the right register — use pattern-based language)
- "Probably X but maybe Y" without a discriminator (the discriminator is what turns hedging into a decision tree)
- "Unsure" (no alternative, no direction)
- Confident language without evidence (overclaiming)

## Why this matters

The reintegration map is the document the user works from, often days or weeks after it was produced. A high-confidence line becomes an instruction; a low-confidence line becomes a decision to make. Mislabeling a line — especially labeling a `low` as `high` — means the user skips the decision and hard-codes an assumption that later reveals itself to be wrong. The failure mode there is exactly the one the whole triptych exists to avoid: silent behavioural divergence in a system the user can't easily inspect.

Being honest about what you don't know is the skill's most load-bearing discipline.

# Good vs Bad Commit Messages — Worked Examples

These examples show how to turn weak commit messages into useful ones using only the diff and the original message. Each example follows the pattern:

1. **Original (bad)** — what the repository has now.
2. **Diff in plain English** — what the diff actually does.
3. **Better (title only)** — a minimum acceptable rewrite.
4. **Even better (title + body)** — the full rewrite, used when the change deserves explanation.
5. **Why** — why the rewrite is justified by the diff alone.

---

## Example 1 — `fix`

**Original:**
```
fix
```

**Diff:** `src/config/loader.py` adds an early return when the configuration path is `None` or the file is empty, before calling `yaml.safe_load`.

**Better (title only):**
```
fix: handle empty input when loading configuration
```

**Even better (title + body):**
```
fix: handle empty input when loading configuration

The configuration loader now checks for an empty or missing path
before parsing. This prevents runtime failures during startup when
no configuration file is present, which previously surfaced as an
opaque YAML parser error rather than a clear missing-config message.
```

**Why:** the original conveys nothing. The diff is a guard clause, and the better titles describe what the guard does. The body explains the practical effect (clearer error path) without inventing a customer story.

---

## Example 2 — `update`

**Original:**
```
update
```

**Diff:** `requirements.txt` bumps `requests` from 2.31.0 to 2.32.3; no other files change.

**Better (title only):**
```
chore(deps): bump requests from 2.31.0 to 2.32.3
```

(For a project not on Conventional Commits:)
```
Bump requests from 2.31.0 to 2.32.3
```

**Body unnecessary** unless the bump is fixing a known CVE that the diff or the dependency notes reference. If unknown, do not invent a reason.

**Why:** dependency bumps are mechanical; the title-only form is sufficient. Adding "fixes CVE-2024-…" without evidence is exactly the invention this skill must avoid.

---

## Example 3 — `wip`

**Original:**
```
wip
```

**Diff:** new file `src/parser/combinators.py` with skeleton classes `Parser`, `Sequence`, `Choice`; no usages elsewhere.

**Better (title only):**
```
Sketch initial parser combinators
```

**Even better (title + body):**
```
Sketch initial parser combinators

Adds an initial Parser/Sequence/Choice skeleton in
src/parser/combinators.py. No call sites yet; intended as the
foundation for the new parser refactor. Implementation is
deliberately incomplete and the API will likely change.
```

**Why:** the original tells the reader the work is in progress but not what it *is*. The proposed title and body preserve the exploratory nature of the change ("Sketch", "deliberately incomplete"), which is honest, and surface what was added.

**Confidence:** Medium. The reader cannot know from the diff whether this skeleton is permanent or will be deleted next commit. Mark as `Medium`.

---

## Example 4 — `more changes`

**Original:**
```
more changes
```

**Diff:** four unrelated changes in one commit:
- `src/auth/login.py`: add CSRF token to login form,
- `docs/README.md`: fix typo,
- `tests/test_parser.py`: add three new tests,
- `.gitignore`: add `*.swp`.

**Issue:** `mixed_concerns`. This commit should not have been one commit. The improvement options are:

- Title-only improvement preserving the bundle (lowest risk):
  ```
  Add CSRF login token, parser tests, README typo, gitignore swp
  ```
  This is honest about the bundle but is *still* a bad commit.

- Suggested cleanup (highest value): in section 9 of the report, propose splitting this into four separate commits, each with its own targeted message. Mark risk **Medium** because the diff *can* be split mechanically, but only if the user authorises a rewrite.

**Why:** rewriting the message of a multi-concern commit cannot fix the underlying problem. The skill must surface this in the cleaned-history plan rather than pretending a better subject line is enough.

---

## Example 5 — `Refactor user model` (mismatched)

**Original:**
```
Refactor user model
```

**Diff:** `src/models/user.py` is unchanged. The diff actually adds two new columns to the `accounts` table migration, drops nothing, and updates `src/models/account.py`.

**Issue:** `mismatch_with_diff`. The original message names the wrong module.

**Better (title only):**
```
Add billing_email and billing_country columns to accounts
```

**Even better (title + body):**
```
Add billing_email and billing_country columns to accounts

Adds two non-null columns to the accounts table with a backfill
default of empty string. Models in src/models/account.py are
updated to expose the new fields; src/models/user.py is unchanged.

Note: the original commit message in the repository ("Refactor
user model") is incorrect; this message reflects what the diff
actually does.
```

**Why:** the original message is misleading. A future reader following the message would look in the wrong place. The rewrite mentions the discrepancy explicitly.

**Confidence:** High that the diff is what it says. Medium that the original author actually intended the rename — the agent does not know.

---

## Example 6 — `auto: 1326 files in 09_Data_Sources (Stop-hook safety commit)`

**Original:**
```
auto: 1326 files in 09_Data_Sources (Stop-hook safety commit)
```

**Diff:** 1326 modifications under `09_Data_Sources/`, all generated by an automated tool.

**Issue:** `autogenerated`. Improving the message line-by-line is rarely useful; the commit is a tool artefact, not a unit of human intent.

**Recommended action:** **do not** propose a rewrite of individual auto commits. Instead, in section 8 of the report, recommend either:

- aggregating the auto-commits into periodic batches (`Auto-batch: data-source refresh, 2026-04-27`), or
- leaving them as-is and documenting their meaning in `CONTRIBUTING.md` so future readers understand the noise.

**Why:** rewriting machine-generated history into pseudo-human prose adds noise without adding signal. Honesty about the source ("this is a tool artefact") beats a fake human subject.

---

## Style-detection examples

**Repository A** — last 50 non-merge commits:

```
Add caching to ResolverV2
Refactor session loader to support async backend
Document the new auth flow
…
```

→ Detected style: **imperative**. Adopt for rewrites.

**Repository B** — last 50 non-merge commits:

```
feat(auth): add JWT refresh
fix(parser): handle EOF
docs(readme): expand setup section
chore(deps): bump pydantic
…
```

→ Detected style: **conventional**. Adopt for rewrites; preserve the type and scope where possible.

**Repository C** — last 50 non-merge commits:

```
auto: 87 files in 09_Data_Sources
auto: 1 file in docs
auto: 4 files in 02_Tasks_and_Execution
hand-written commit about a real change
auto: 12 files in 09_Data_Sources
```

→ Detected style: **mixed**, with a strong autogenerated tail. Recommend separating the two streams in section 8 rather than imposing a uniform style.

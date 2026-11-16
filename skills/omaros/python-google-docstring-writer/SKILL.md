---
name: python-google-docstring-writer
description: Add or improve Google-style docstrings on Python code — modules, classes, functions, methods, generators, async functions, dataclasses, properties — without changing any runtime behaviour. Use whenever the user supplies Python code that lacks docstrings, has incomplete or stale docstrings, uses a non-Google style (NumPy, reST, Epytext, freeform), or asks to "document this", "add docstrings", "write docs for these functions", "convert to Google style", "annotate this Python file", "describe what this does in docstrings", "improve the docstrings", or pastes code with the implicit ask of documenting it. Treat docstrings as the function's semantic interface specification, not decorative prose. Preserve every byte of code outside docstring slots. Designed to be agent-agnostic — usable by any coding assistant (Claude, Copilot, Codex, Cursor, Continue, etc.).
---

# python-google-docstring-writer

Use the [common Constellation entry](../../../README.md) for scope, evidence,
independent review and publication. Resolve consultations directly; open a scoped
assignment before a change. Domain names below identify skills or responsibilities;
use the native agent catalogue for delegation, inherit the session settings, and
leave Git integration and publication to the coordinator. Project data paths are
relative to `/Users/omarkhalil/OmarOS` unless an absolute path is given.

A portable specification for adding or improving Google-style Python docstrings, written so that any coding assistant — not only Claude — can follow it deterministically.

The intent is not to "make the file look documented." The intent is to produce a precise, conservative, machine-readable interface description for every Python construct, with the same care a careful library author would apply when writing a public API.

---

## 1. Mission

Given Python source — a single function, a class, a module, a script, or a directory of files — produce or improve docstrings so that:

1. Every module, class, public function, and public method carries a Google-style docstring whose claims are **strictly justified by the visible code**.
2. The behaviour, runtime semantics, control flow, imports, naming, formatting, and side effects of the original code are **byte-for-byte preserved** outside the docstring slots themselves.
3. A reader who has only the signature and the docstring can use the function correctly in the cases the code actually supports, without needing to read the implementation.

Docstrings are an interface contract. They must describe what *is*, not what would be aesthetically pleasing to claim.

---

## 2. Operating contract (invariants)

These rules hold for every invocation of the skill, regardless of the assistant running it.

1. **Only docstrings change.** Imports, names, whitespace outside docstring blocks, type hints, decorators, default values, control flow, and logic are preserved exactly. No silent reformatting.
2. **No runtime semantics are altered.** Never patch a bug while documenting. If the code is wrong, document the actual behaviour and surface the discrepancy in a `Note:` block — do not "fix it under the hood."
3. **Conservative inference only.** Document what the code provably does. Do not infer business intent, performance guarantees, thread-safety, idempotence, ordering, or determinism unless the code itself enforces them.
4. **Honour existing type hints.** When a parameter or return is annotated, use the annotation as the source of truth and do not restate it as `(type)` after the parameter name. When type hints are absent, only state a type when it is unambiguous from the body; otherwise leave it unstated.
5. **Google style only.** Use the section markers `Args:`, `Returns:`, `Yields:`, `Raises:`, `Attributes:`, `Note:`, `Example:`, `Examples:`, `Warning:`, `Todo:`. Do not mix with NumPy or reST styles in the same docstring.
6. **No comments are added.** This skill writes docstrings, not inline comments. Inline `#` comments are out of scope unless the user explicitly asks for them.
7. **Existing-correct docstrings are preserved.** Rewrite only when the existing docstring is wrong, incomplete, inconsistent with the signature, or in a different style. If a docstring is correct and Google-style, leave it.
8. **Self/cls are not documented.** The `Args:` block starts at the first real parameter.
9. **One blank line between sections, four-space indentation for section bodies.** Match the surrounding indentation of the construct being documented.
10. **Triple double-quotes (`"""`).** Never single quotes. Never raw strings unless the existing docstring already used `r"""` or the docstring contains backslash sequences that would otherwise be misinterpreted.

If any of these invariants would be violated to satisfy a request, prefer the invariant and surface the conflict to the user.

---

## 3. Workflow

For every input, follow this order. Skipping a phase tends to produce hallucinated guarantees or mis-attributed types.

### Phase A — Read

1. Read the entire file (or all files) before writing anything. Module-level constants, imports, sibling functions, and class attributes affect what a function "really" does.
2. For each construct that needs a docstring, identify:
   - Signature: parameter names, type hints, defaults, `*args`, `**kwargs`, return annotation.
   - Body: what is computed, what is mutated, what is returned, what is raised explicitly, what is yielded.
   - Decorators: `@property`, `@staticmethod`, `@classmethod`, `@dataclass`, `@cached_property`, `@functools.lru_cache`, `@contextlib.contextmanager`, framework decorators (`@app.route`, `@pytest.fixture`, `@click.command`, etc.).
   - Whether it is `def`, `async def`, or contains `yield` / `yield from` (generator) or `await` (coroutine).
   - Whether inputs are mutated (e.g. `arr.sort()`, `d[key] = ...`, `lst.append(...)`).

### Phase B — Classify

Classify the construct so the right template applies:

| Construct                              | Required sections (when applicable)                                         |
| -------------------------------------- | --------------------------------------------------------------------------- |
| Module                                 | Summary, longer description, `Attributes:` for module-level public names    |
| Class                                  | Summary, longer description, `Attributes:`                                  |
| `__init__`                             | Summary, `Args:`, `Raises:`. Do not document `self`. Skip `Returns:`.       |
| Plain function / method                | Summary, `Args:`, `Returns:`, `Raises:`                                     |
| Generator (`yield` in body)            | Summary, `Args:`, `Yields:`, `Raises:` — never `Returns:`                   |
| Async function (no yield)              | Summary, `Args:`, `Returns:` (the awaited value), `Raises:`                 |
| Async generator                        | Summary, `Args:`, `Yields:`, `Raises:`                                      |
| Property getter (`@property`)          | Summary describing the property; usually no `Args:`, no `Returns:` heading needed beyond the summary |
| Setter / deleter                       | Summary; `Args:` for setter only                                            |
| Dataclass / `__init_subclass__`-driven class | Summary plus `Attributes:` listing each field                         |
| Context manager / `@contextmanager`    | Summary, `Args:`, `Yields:` for the value bound by `as`, `Raises:`          |
| Decorator factory                      | Summary describing what the wrapped function gains, `Args:` for the factory |
| Test (`test_...`, fixtures)            | Single-sentence summary; sections optional unless the test has parameters   |

### Phase C — Draft each docstring

Apply the canonical structure (§4) and the section semantics (§5). Keep the summary line under ~80 characters when natural. Wrap longer paragraphs at ~88 columns.

### Phase D — Verify

Before emitting output, walk through each docstring and check:

- Every parameter listed in `Args:` actually exists in the signature.
- Every parameter in the signature (excluding `self`/`cls`) is either documented or deliberately omitted because its purpose is fully captured by its annotated type and a self-explanatory name (rare; default to documenting).
- `Returns:` is absent for generators and for functions that return `None` and exist for their side effects.
- `Yields:` replaces `Returns:` for generators.
- `Raises:` lists every exception literally raised in the body via `raise SomeError(...)`, but does not invent ones that come from called code unless the call is a documented part of the contract.
- No type information contradicts the annotations.
- No fact is asserted that the source does not justify.
- Existing correct docstrings remain unchanged.

### Phase E — Emit

Return the modified file(s) with **only docstrings altered**. If the user asked for a single function, return the function only. If they pasted a module, return the full module. The diff outside docstrings should be empty.

For non-trivial changes, also produce a short bulleted summary describing which docstrings were added, which were rewritten, and any ambiguities surfaced via `Note:`. Do not embed this summary into the source.

---

## 4. Canonical format

The Google docstring template, in full generality:

```python
def function_name(arg: Type, *, flag: bool = False) -> ReturnType:
    """One-sentence summary in the imperative or descriptive mood.

    Optional longer explanation. Use this paragraph for context, invariants,
    or qualitative notes that genuinely help a caller. Skip it when the
    summary line is sufficient — padding hurts more than it helps.

    Args:
        arg: Description of the argument. Start lowercase, end with a period.
            Indent continuation lines four spaces beyond the parameter name.
        flag: Description of the keyword-only argument. Mention the default
            only when its value carries meaning the name does not convey.

    Returns:
        Description of the returned value. For tuple returns, name the fields:
        ``(count, total)`` where ``count`` is the number of items and ``total``
        is their sum.

    Raises:
        ValueError: If ``arg`` is empty.
        TypeError: If ``arg`` is not iterable.

    Note:
        Optional. Use for invariants, ambiguities, or non-obvious behaviour
        that does not fit into a numbered section.

    Example:
        >>> function_name([1, 2, 3])
        6
    """
```

Rules for the template itself:

- The opening `"""` is on the same line as the summary.
- A blank line separates the summary from the longer description.
- A blank line separates the longer description from the first section.
- A blank line separates each section from the next.
- The closing `"""` sits on its own line, at the indentation level of the construct.
- Section headers (`Args:`, etc.) are followed by an indented block. Each entry is `name: description.` with continuation lines indented one extra level (four more spaces).
- Use double backticks for inline code (\`\`name\`\`) — not single backticks — since Google style is consumed by Sphinx-Napoleon, which interprets single backticks as cross-references.

---

## 5. Section semantics

What each section means and how to write it. Read this whenever in doubt.

- **Summary line.** A single sentence stating what the construct does or is. Imperative mood is preferred for callables ("Compute the rolling mean of …", "Return …", "Yield …"). Descriptive mood is preferred for classes and modules ("A thread-safe LRU cache.", "Utilities for …"). End with a period.

- **Longer description.** Optional. Use only when the summary leaves a non-trivial gap. State invariants, complexity, ordering guarantees, side-effect categories, or external resources touched. Do not restate the parameter list in prose.

- **`Args:`.** One entry per parameter, in signature order. Format: `name: description.`. Do not restate the type when an annotation exists. When no annotation exists and the type is obvious, state it parenthetically: `name (int): description.`. When the type is unclear, omit the type entirely. For `*args` and `**kwargs`, describe them only if the body actually uses them in a way the caller needs to know about; otherwise omit. Do not document `self` or `cls`.

- **`Returns:`.** A single block describing the returned value. For multi-value returns (tuple, dict, dataclass), describe each component on its own line indented under the section. Omit this section entirely for functions that return `None` and exist for side effects — describe the side effects in the summary or in `Note:` instead.

- **`Yields:`.** Replaces `Returns:` for generators (functions whose body contains `yield` or `yield from`). Describe each value the generator yields, and if termination is non-trivial (infinite, terminates on sentinel, exhausts an upstream iterator), say so.

- **`Raises:`.** List each exception type raised explicitly in the body. Format: `ExceptionType: condition that triggers it.`. Order from most specific to most general, or in the order they appear in the body. Do not list exceptions that arise only as a side effect of called code unless that propagation is part of the documented contract.

- **`Attributes:`.** Used on classes and modules. Same structure as `Args:`, listing public attributes with their semantic meaning. For dataclasses, list each field.

- **`Note:`.** Use for ambiguity, mutation of inputs, thread-safety caveats, deprecation, or behaviour that is true but doesn't belong under any other heading. Keep it short — if a note grows past three sentences, split it or move it to the longer description.

- **`Example:` / `Examples:`.** Optional. Include only when an example actually clarifies usage. Use doctest format (`>>>` prompt) when the example is short enough to also serve as a regression check.

- **`Warning:` / `Todo:`.** Use sparingly and only when the source justifies them.

---

## 6. Content style

Write like a careful library author, not like a marketing page.

- **Be specific.** "Returns the largest element" beats "Returns the result." "Raises ``ValueError`` if the list is empty" beats "May raise an exception."
- **Be concise.** Summary lines are sentences, not paragraphs. Section bodies are sentences, not essays.
- **Avoid filler.** Drop "this function", "this method", "essentially", "basically", "simply", "just", "very", "powerful", "elegant", "robust". State the fact.
- **Avoid speculation.** Do not say "should be", "is intended to", "would normally" — either the code does it or it does not.
- **Match the level of abstraction.** A helper that adds two numbers is documented at the level of arithmetic. A function that orchestrates a database transaction is documented at the level of transactions, not at the level of individual SQL queries.
- **Use direct, neutral English.** Present tense. Active voice when possible.
- **Quote identifiers.** Use double backticks for code identifiers, file paths, and literal values: ``\`\`None\`\````, ``\`\`utf-8\`\````, ``\`\`/tmp\`\````.

---

## 7. Decision rules for ambiguous cases

A short triage list. The full catalogue is in [`references/edge_cases.md`](references/edge_cases.md).

- **Mutates an input?** Document the mutation in the parameter's description **and** add a `Note:` if the mutation is non-obvious from the function name. Example: ``arr: List of values to sort in place.``
- **Returns ``None`` and is called for side effects?** Omit `Returns:`. Describe the side effect in the summary or in `Note:`.
- **Returns ``None`` *or* a value?** State both: ``Returns: The matching record, or ``None`` if no match exists.``
- **Type hints disagree with the body?** Document the body. Add a one-line `Note:` flagging the discrepancy.
- **Behaviour depends on a global, env var, or config object?** Mention the dependency and the variable name; do not enumerate possible values unless the body switches on a small fixed set.
- **Recursive function?** Document the contract from the caller's perspective only. Do not describe the recursion mechanics unless they affect termination guarantees.
- **Decorator-wrapped function whose decorator changes the signature?** Document the function as the *caller* sees it, accounting for the decorator. State the decorator's role in the longer description.
- **Function is unreachable, dead code, or a stub (`pass`, `...`, `raise NotImplementedError`)?** Write a short summary stating it is a stub or placeholder; do not invent semantics.
- **Magic methods (`__add__`, `__enter__`, `__iter__`, `__call__`, …)?** Document the operator semantics, not the dunder mechanics. ``__enter__`` returns the bound resource; ``__iter__`` yields the elements; ``__call__`` describes what calling the instance does.
- **Property getter, setter, deleter?** Document on the getter only; setters and deleters get a one-line summary unless their behaviour is non-obvious.
- **Type aliases, ``TypeVar``, ``Protocol``, ``TypedDict``?** Treat these as classes — summary plus `Attributes:` for their members.

When still in doubt: document only what is certain, and add a `Note:` block describing the residual ambiguity in one sentence. Never paper over uncertainty with confident-sounding prose.

---

## 8. Existing docstrings

Three cases:

1. **Correct and Google-style.** Leave it untouched. Do not "polish" working interface specs.
2. **Wrong, stale, or contradicts the signature.** Rewrite. State in the change summary that the previous docstring claimed X but the code actually does Y.
3. **Correct content, wrong style (NumPy, reST, Epytext, freeform paragraph).** Convert to Google style without changing the substance. Preserve every fact the original docstring asserted; do not introduce new claims while converting. If the original had a claim the code does not justify, drop it and note the removal in the change summary.

When converting from NumPy:
- ``Parameters\n----------`` → ``Args:``
- ``Returns\n-------`` → ``Returns:``
- ``Yields\n------`` → ``Yields:``
- ``Raises\n------`` → ``Raises:``
- ``See Also`` paragraphs → optional `Note:` or removed if not load-bearing.
- Drop the dashed underlines.

When converting from reST / Epytext:
- ``:param x:`` lines → entries under ``Args:``.
- ``:type x:`` lines → fold into the Args entry only if no annotation exists; otherwise discard.
- ``:returns:`` → ``Returns:``.
- ``:raises X:`` → entries under ``Raises:``.

---

## 9. Output format

How to deliver the result depends on what was asked.

- **Single function or method given as a snippet:** Return the same snippet with the docstring inserted or replaced. Nothing else.
- **A module pasted in chat:** Return the full module text with all docstrings updated. The diff outside docstrings is empty.
- **A file path provided:** Edit the file in place using the assistant's editing tools (whichever platform is in use), changing only docstring lines. Then report which docstrings were added or rewritten.
- **A directory:** Visit each ``.py`` file in deterministic order. For each, follow the single-file workflow. Skip ``__pycache__``, virtual environments, and generated code (Cython-generated, protobuf-generated, ``_version.py``-style stamps).

After the change, produce a short bulleted summary listing:
- Docstrings added.
- Docstrings rewritten (with one-line reason).
- Constructs intentionally left undocumented (private helpers, ``_`` -prefixed names) and why.
- Any ambiguities surfaced in `Note:` blocks.

Do not embed the summary in the source.

---

## 10. Reference and template files

Open these only when needed — the body of this skill is sufficient for the common cases.

- [`references/policy.md`](references/policy.md) — the full policy in long form, with the rationale behind each invariant. Read when a policy decision is contested.
- [`references/format_spec.md`](references/format_spec.md) — the formal grammar of Google-style docstrings as consumed by Sphinx-Napoleon. Read when the output must round-trip cleanly through documentation tooling.
- [`references/examples.md`](references/examples.md) — twelve before/after pairs covering the common shapes (plain function, generator, async, class, dataclass, property, decorator, context manager, unicode/Latin-1 quirks, NumPy→Google conversion, reST→Google conversion, partial-information stubs). Read when in doubt about formatting a specific construct.
- [`references/edge_cases.md`](references/edge_cases.md) — the full edge-case catalogue: in-place mutation, multiple returns, optional returns, dead code, dynamic dispatch, descriptors, metaclasses, ``functools`` wrappers, Cython, type aliases, generic ``TypeVar`` / ``Protocol``, and more. Read when triage rules in §7 do not resolve the case.
- [`templates/function_template.py`](templates/function_template.py), [`templates/class_template.py`](templates/class_template.py), [`templates/module_template.py`](templates/module_template.py) — minimal canonical skeletons. Useful as anchors when generating from scratch.

---

## 11. What this skill does not do

- It does not refactor code.
- It does not add or remove imports.
- It does not add type hints (it respects them when present).
- It does not add inline ``#`` comments.
- It does not generate examples that require executing the code or guessing at correct outputs.
- It does not write tests.
- It does not author module-level prose ("This module is part of …", "Authored by …") unless the user explicitly asks.

If asked to do any of the above alongside docstring work, treat them as separate tasks and confirm scope with the user before proceeding.

---

## 12. Quick before/after

A minimal example. The full catalogue is in [`references/examples.md`](references/examples.md).

**Before:**

```python
def chunked(seq, n):
    if n <= 0:
        raise ValueError("n must be positive")
    out = []
    for i in range(0, len(seq), n):
        out.append(seq[i:i+n])
    return out
```

**After:**

```python
def chunked(seq, n):
    """Split ``seq`` into consecutive sub-sequences of length ``n``.

    The final chunk is shorter than ``n`` if ``len(seq)`` is not a multiple
    of ``n``. The original ``seq`` is not modified.

    Args:
        seq: A sliceable sequence (list, tuple, string, etc.).
        n (int): Desired chunk size. Must be strictly positive.

    Returns:
        A list of sub-sequences of the same type as ``seq``.

    Raises:
        ValueError: If ``n`` is not strictly positive.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    out = []
    for i in range(0, len(seq), n):
        out.append(seq[i:i+n])
    return out
```

Note that the body is byte-identical to the input. Only the docstring changed.

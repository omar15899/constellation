# Docstring Writing Policy — Long Form

The body of `SKILL.md` is the operational interface. This document is the *constitution*: the underlying principles and the rationale behind each invariant. Read this when a policy decision is contested or when an edge case feels under-specified.

## 1. Why docstrings are interface specifications

A docstring is the only piece of in-source documentation that:

- is preserved at runtime (`obj.__doc__`);
- is consumed by IDEs, language servers, REPLs, Jupyter, and Sphinx;
- is read by callers who do not have time to read the body;
- is read by future maintainers who do not remember the original intent;
- is read by documentation generators that turn it into the public face of the library.

Treating a docstring as decorative prose ("Helper function to do stuff") betrays every one of those readers. Treating it as an interface specification — a precise statement of what the function accepts, what it returns or yields, what it raises, and what side effects it has — serves all of them.

The policy below derives from this single observation.

## 2. The conservation invariant

> The output is byte-identical to the input outside docstring slots.

This is non-negotiable for three reasons:

1. **Trust.** Users grant the skill permission to write docstrings, not to refactor code. Crossing that boundary breaks trust permanently.
2. **Diff hygiene.** A pull request titled "add docstrings" should produce a diff that touches docstring lines only. Mixed diffs (formatting + docstrings + bug fix + refactor) are rejected at code review.
3. **Reversibility.** A docstring change can always be undone without losing work. A "while I was there I also fixed …" change cannot.

Concrete consequences:

- No reformatting (no Black, no autopep8, no quote-style changes).
- No import reordering.
- No variable renaming (not even ``i`` → ``index``).
- No type-hint additions (the skill respects existing hints; it does not add new ones).
- No bug fixes. Document the bug, do not patch it.
- No `# noqa`, `# type: ignore`, or other auxiliary directives.
- No removal of "dead" code.
- No insertion of `__all__`, `__version__`, or other module-level metadata.

If the user asks for any of the above *alongside* docstring work, treat it as a separate task and confirm scope.

## 3. The justified-claim invariant

> Every claim in a docstring must be justified by the visible source.

A "justified claim" is one a reader could verify by reading the body of the construct (and possibly its callers within the same file). Examples of justified claims:

- "Returns the largest element" — justified if the body iterates with `max(...)` or an equivalent comparison.
- "Raises ``ValueError`` if ``n`` is negative" — justified if the body contains `if n < 0: raise ValueError(...)`.
- "Mutates ``arr`` in place" — justified if the body calls `arr.sort()`, `arr.append(...)`, etc.
- "Yields each line of the file" — justified if the body is a generator over `f` or `f.readlines()`.

Examples of *unjustified* claims that must not appear:

- "Thread-safe." Unless the body uses a lock or atomic primitive.
- "O(n log n) complexity." Unless the algorithm visibly is, and even then prefer wording like "Sorts using Python's built-in sort, which is Timsort."
- "Idempotent." Unless visibly so.
- "Validates input." If the body does no validation, do not claim it does.
- "Used by the X module." Coupling claims rot the moment the codebase changes.
- "Optimized for large inputs." Almost never justified, almost always meaningless.
- "This is a wrapper around X." Useful only if the wrapping changes behaviour; otherwise omit.

When tempted to assert something the code does not justify, choose one of:

1. Drop the claim entirely.
2. Move it to a `Note:` and weaken to a true statement ("This function is currently a thin wrapper around `X`; callers should not rely on this remaining the case.").
3. Ask the user before asserting it.

## 4. The conservative-inference invariant

When inferring types or behaviour from un-annotated, un-documented code, prefer under-claiming to over-claiming.

- Type hints present → use them as ground truth.
- Type hints absent, type obvious from the body (e.g. the variable is the result of `len(...)`, the parameter is iterated with `for ... in x`) → state the type plainly.
- Type hints absent, type ambiguous (the parameter is forwarded to another function, used in `isinstance` with multiple types, or has no operations applied) → omit the type.
- Type hints absent, parameter is `*args` or `**kwargs` and the body uses them generically → describe usage in prose without committing to a type.

Never paraphrase a type hint into prose ("an integer that represents the count" when the signature already says ``count: int``). Trust the reader.

## 5. The style discipline

Docstrings written in the style of marketing prose erode trust quickly. The discipline is:

- **Specific over abstract.** "Returns the smallest power of two greater than or equal to ``n``" beats "Computes a useful bound on ``n``."
- **Concrete over hedged.** "Returns ``None`` when no match is found" beats "May return nothing."
- **Direct over euphemistic.** "Closes the file. Idempotent." beats "This method handles closure of the underlying file resource in a graceful manner."
- **Sentences over fragments.** Section entries are sentences with a period. The summary line is a sentence with a period.
- **Imperative for callables, descriptive for objects.** "Compute the running median." for a function. "A bounded LRU cache." for a class.

The forbidden registers:

- **Marketing.** "powerful", "robust", "elegant", "blazing", "production-ready", "enterprise-grade".
- **Filler.** "this function", "this method", "essentially", "basically", "simply", "just", "very", "really".
- **Hedging.** "should", "would", "is meant to", "is intended to", "tries to". Either the code does it or it does not.
- **Self-reference.** "As mentioned above", "see below". Docstrings are not narrative.
- **Apology.** "Note that this is a bit hacky", "ideally we would". If the code is hacky, that is a bug to fix elsewhere — do not document the smell.

## 6. The treatment of `self` and `cls`

Methods do not document the implicit first parameter. The `Args:` block starts at the first real parameter. This is a Google-style convention enforced consistently across the language ecosystem (cpython, NumPy, pandas, scikit-learn, TensorFlow). Deviating from it is a noise generator.

Static methods and class methods follow the same convention; `cls` is treated identically to `self`.

## 7. The treatment of `*args` and `**kwargs`

The default is *not* to document `*args` and `**kwargs`, because most uses are pure forwarding (`super().__init__(*args, **kwargs)`, `func(*args, **kwargs)`) where the caller's expectations are determined by the wrapped callable, not by the local function.

Document them only when:

- The body iterates over `*args` and treats each element as a documented unit (e.g. "Each positional argument is a regex pattern to apply.").
- The body looks up specific keys in `**kwargs` (e.g. `kwargs.get("timeout", 30)`), in which case document the keys, not `**kwargs` as a whole.
- The function is the public entry point of a library and the user's expectation of explicit documentation outweighs forwarding noise.

When documenting `**kwargs` for a function that accepts a fixed set of keyword arguments, prefer to list the keys as if they were named parameters:

```
Args:
    ...
    **kwargs: Additional configuration options:

        - ``timeout``: Seconds before the request is aborted. Defaults to 30.
        - ``retries``: Number of retry attempts. Defaults to 3.
```

## 8. The treatment of `Returns:` versus `Yields:`

A function's return contract is determined by its body, not by its name.

- If the body contains `yield` or `yield from`, it is a generator. Use `Yields:`. Never `Returns:`.
- If the body uses `async def` and contains `yield`, it is an async generator. Use `Yields:`.
- If the body is `async def` without `yield`, it is a coroutine returning a value. Use `Returns:` and describe the awaited result naturally — there is no need to say "a coroutine that returns X". The annotation `-> X` already communicates the awaited type.
- If the body is `async def` returning `None` for side effects, omit `Returns:` and describe the side effect.
- If the body is a regular function returning `None` for side effects, omit `Returns:` and describe the side effect.
- If a function returns multiple values via tuple, document each component:

```
Returns:
    A tuple ``(mean, stddev)`` where ``mean`` is the arithmetic mean and
    ``stddev`` is the sample standard deviation.
```

- If a function returns a value or `None`, state both possibilities:

```
Returns:
    The first element matching ``predicate``, or ``None`` if no element matches.
```

## 9. The treatment of `Raises:`

`Raises:` enumerates exceptions that the body explicitly raises via `raise SomeError(...)`. It does not enumerate every exception that *could* propagate from called code, because that set is unbounded and the documentation would be useless.

Two exceptions to that rule:

1. The function exists primarily to translate or re-raise a particular exception (e.g. it catches `OSError` and re-raises a domain-specific `StorageUnavailable`). Document the translated exception.
2. The function is part of a public API where a particular exception from a called dependency is part of the documented contract (e.g. a function that calls `requests.get` and the contract is "raises `HTTPError` on non-2xx responses"). Document the propagated exception.

Order entries either by specificity (most specific first) or by appearance in the body, whichever is more readable. Format: ``ExceptionType: condition.`` where the condition is a short clause describing what triggers the exception.

## 10. The treatment of mutation

Pythonic code mutates frequently — appending to lists, sorting in place, mutating dicts, setting attributes. Mutation is not "bad" but it is a contract the caller must understand.

Document mutation in two places:

1. The relevant `Args:` entry. ``arr: List of values, sorted in place.`` is unambiguous.
2. A `Note:` block when the mutation is non-obvious from the function name. ``register(handler)`` mutating a global registry warrants a note. ``handlers.append(handler)`` does not.

Functions that exclusively mutate inputs and return `None` should omit `Returns:` and describe the mutation in the summary or `Note:`.

## 11. The treatment of existing docstrings

Three categories:

1. **Correct, Google-style, complete.** Leave untouched. Do not "polish" working interface specs — every edit risks introducing an unjustified claim.
2. **Wrong or stale.** Rewrite. The rewrite must be byte-correct against the current code; the previous (incorrect) docstring is discarded silently. Mention the discrepancy in the change summary, not in the docstring itself — runtime consumers should not see "the previous docstring claimed X" embedded in the canonical interface spec.
3. **Correct content, wrong style.** Convert to Google style. Preserve every fact; do not invent new ones during the conversion. If the source had a claim the code does not justify, drop it and note the removal in the change summary.

A working but minimal docstring (say, a single-line summary with no `Args:`/`Returns:`) is in category 1 only if its single line is correct and the function is so trivial that a section block would be padding. For most non-trivial functions, a single-line docstring is "correct content, incomplete style" and falls into category 3 — augment it with the missing sections.

## 12. The treatment of properties, descriptors, and other dunders

Properties:

- Document on the getter only. The getter's docstring is the property's docstring as far as `help(obj)` is concerned.
- Use a one-line summary describing the value. ``"""The number of connected clients."""``. No `Returns:` block — the summary is the return description.
- Setters and deleters get a one-line summary of their own only when their behaviour is non-obvious (e.g. setting triggers validation or side effects).

Descriptors (`__get__`, `__set__`, `__delete__`):

- Document the user-facing semantics as if the descriptor were a property.
- Mention `__set_name__` only if its behaviour affects callers.

Magic methods:

- ``__init__``: summary plus `Args:` plus `Raises:`. Skip `Returns:` (it returns `None`).
- ``__call__``: describe what calling the instance does, as if it were a function with that signature.
- ``__enter__`` / ``__exit__``: describe the resource managed and what `as` binds. ``__enter__`` returns the bound resource; ``__exit__`` describes whether exceptions are suppressed.
- ``__iter__``: ``Yields:`` block describing the elements.
- ``__next__``: same content as ``__iter__``, but on a per-call basis.
- ``__eq__``, ``__hash__``, ``__lt__``: usually a one-line summary describing the comparison key suffices. No `Args:` block needed — the parameter is always the other operand.

## 13. The treatment of decorators

When a function is decorated, document it from the *caller's* perspective.

- A function decorated with `@functools.lru_cache` is documented as if uncached, with one note: "Memoised via ``functools.lru_cache``."
- A function decorated with `@app.route("/")` is documented as a Flask handler — the caller never invokes it directly, so the docstring describes what the route does, not the function's signature. Mention HTTP methods accepted, response shape, and any side effects.
- A function decorated with `@contextlib.contextmanager` is documented as a context manager: summary, `Args:`, `Yields:` for the value bound by `as`, `Raises:`.
- A function decorated with a custom decorator that changes the signature (e.g. injects parameters, wraps with different return type) is documented at the *exposed* signature. State the decorator's role briefly in the longer description.

Decorator factories themselves get docstrings describing the decorator they produce:

```python
def retry(times: int):
    """Return a decorator that retries the wrapped call up to ``times`` times.

    The wrapped callable is invoked, and on any exception is re-invoked up to
    ``times`` additional times. The final exception is re-raised if all
    attempts fail.

    Args:
        times: Number of additional attempts after the first. Must be ≥ 0.

    Returns:
        A decorator that, when applied to a callable, produces a retrying
        wrapper with the same signature.
    """
```

## 14. The treatment of modules

A module-level docstring sits at the top of the file, before any imports.

- Summary: one sentence stating what the module is for.
- Longer description: optional paragraph describing the major public objects and how they relate.
- `Attributes:`: optional, listing module-level public constants and singletons. Do not list every name; list those that constitute the public API.

Avoid:

- Authorship metadata (``"""Author: ..."""``). Source control owns that.
- Change logs (``"""Version 1.2.3 — added foo"""``). Tags and release notes own that.
- Long preambles. The first sentence should already convey the module's identity.

## 15. The treatment of tests

Tests are still public-ish API — pytest, unittest, and IDEs all surface their docstrings. Default policy:

- A one-sentence summary stating what the test verifies. ``"""Verify that an empty input raises ``ValueError``."""``.
- No `Args:` block for parametrised tests unless the parameter combinations carry meaning beyond their values.
- No `Returns:` block.
- No `Raises:` block — `pytest.raises` blocks are not "raised exceptions" in the contract sense.

Fixtures get docstrings stating the resource they yield and any cleanup they perform.

## 16. Surface-level style rules

These exist because Sphinx-Napoleon — the canonical Google-style consumer — is strict about them.

- Triple double-quotes (`"""`). Single-quote triple strings render correctly in some tools and break in others. Use double.
- Closing `"""` on its own line at the construct's indentation. Inline closures are valid for one-line docstrings only.
- Blank line between summary and longer description.
- Blank line between sections.
- Section headers use exact spelling and trailing colon: `Args:`, `Returns:`, `Yields:`, `Raises:`, `Attributes:`, `Note:`, `Example:`, `Examples:`, `Warning:`, `Todo:`. Do not use `Arguments:`, `Parameters:`, `Return:`, `Yield:`, `Raise:`, `Notes:` — Napoleon recognises only the Google-canonical forms.
- Double backticks for inline code: ``\`\`name\`\`````.

## 17. The output discipline

When delivering changes:

- For a single-snippet input, return the snippet with the docstring inserted or replaced, nothing else.
- For a full module input, return the full module text, byte-identical outside docstring slots.
- For a file-path input, edit the file in place and report a summary.
- For a directory input, process each `.py` file and produce a per-file summary.

Always include, after the source change, a short bulleted change report:

- *Added* docstrings on …
- *Rewrote* docstrings on … (with a one-line reason, if non-obvious).
- *Left untouched* docstrings on … (because they were already correct).
- *Skipped* … (with reason — generated code, vendored, etc.).
- *Surfaced* ambiguities via `Note:` on …

This summary is for the user, not for the source. Do not embed it in the source.

## 18. When to ask before writing

The skill operates with as much autonomy as the host assistant grants it, but ask the user before:

- Modifying files outside the explicit scope of the request.
- Writing docstrings on auto-generated code (Cython, protobuf, gRPC stubs, ORM-generated models). These are usually owned by the generator and should not be touched.
- Touching test files when the user only asked for "the library".
- Documenting deeply private helpers (`__name`-mangled, double-underscore-prefixed) — these are usually intentionally undocumented.
- Translating an existing docstring out of a non-English language. Surface the question and let the user decide whether to keep the original language or translate.

The bias is toward action when the scope is unambiguous, and toward asking when the scope might surprise.
